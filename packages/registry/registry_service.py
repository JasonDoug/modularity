"""
Modularity Registry Service
Central service for discovering and managing modules in the ecosystem
"""

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import time
import threading
import requests
from datetime import datetime
import json
from pathlib import Path
from urllib.parse import urlparse
import ipaddress
import os
from queue import Queue, Full, Empty


app = Flask(__name__)

# Configure CORS with specific allowed origins (security fix)
# In production, set ALLOWED_ORIGINS environment variable to comma-separated list
allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000').split(',')
CORS(app, origins=allowed_origins, supports_credentials=True)

# Invocation tracking authentication
# Set REGISTRY_TRACK_TOKEN to require authentication for /api/track/invocation
# Use REGISTRY_ALLOW_INSECURE=true or FLASK_ENV=development to disable in dev
REGISTRY_TRACK_TOKEN = os.getenv('REGISTRY_TRACK_TOKEN')
REGISTRY_ALLOW_INSECURE = os.getenv('REGISTRY_ALLOW_INSECURE', '').lower() in ('true', '1', 'yes')
FLASK_ENV = os.getenv('FLASK_ENV', 'production')

# In-memory registry (can be replaced with Redis or database)
registry: Dict[str, Dict[str, Any]] = {}
capability_index: Dict[str, List[str]] = {}  # capability -> [service_ids]
registry_lock = threading.Lock()

# Server-Sent Events (SSE) for real-time updates
sse_clients: List[Queue] = []
sse_lock = threading.Lock()

# Connection tracking data structures
@dataclass
class ConnectionInfo:
    """Tracks connection between a consumer and provider service"""
    consumer_id: str
    provider_id: str
    capability: str
    first_seen: str  # ISO datetime
    last_seen: str   # ISO datetime
    request_count: int = 0
    success_count: int = 0
    total_latency_ms: float = 0.0

# Track connections: consumer_id -> List[ConnectionInfo]
connections: Dict[str, List[ConnectionInfo]] = {}
connections_lock = threading.Lock()

# Health check configuration
HEALTH_CHECK_INTERVAL = 30  # seconds
HEALTH_CHECK_TIMEOUT = 5    # seconds
MAX_FAILED_CHECKS = 3


class RegistryStore:
    """Persistent storage for registry data"""

    def __init__(self, storage_path: str = "~/.ecosystem/registry.json"):
        self.storage_path = Path(storage_path).expanduser()
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, data: Dict):
        """Save registry to disk"""
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)

    def load(self) -> Dict:
        """Load registry from disk"""
        if not self.storage_path.exists():
            return {}

        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError, IOError) as e:
            print(f"Error loading registry: {e}")
            return {}


store = RegistryStore()


def broadcast_event(event_type: str, data: dict):
    """Broadcast event to all connected SSE clients"""
    event = {
        'event': event_type,
        'timestamp': datetime.now().isoformat(),
        'data': data
    }

    with sse_lock:
        for client_queue in sse_clients[:]:  # Iterate over a copy
            try:
                client_queue.put_nowait(event)
            except Full:
                # Slow client: drop it to prevent unbounded growth
                sse_clients.remove(client_queue)


def is_safe_url(url: str) -> bool:
    """
    Validate URL to prevent SSRF attacks.
    Only allows localhost and private network addresses for health checks.
    """
    try:
        parsed = urlparse(url)

        # Must have http or https scheme
        if parsed.scheme not in ('http', 'https'):
            return False

        # Extract hostname
        hostname = parsed.hostname
        if not hostname:
            return False

        # Allow localhost
        if hostname in ('localhost', '127.0.0.1', '::1'):
            return True

        # Allow private network ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
        try:
            ip = ipaddress.ip_address(hostname)
            return ip.is_private or ip.is_loopback
        except ValueError:
            # Hostname is not an IP address - for now, reject non-IP hostnames
            # In production, you might want to resolve DNS and check the IP
            return False

    except Exception:
        return False


def rebuild_capability_index():
    """Rebuild the capability index from current registry"""
    global capability_index

    # Acquire lock to prevent race conditions when modifying shared state
    with registry_lock:
        capability_index.clear()

        for service_id, service_info in registry.items():
            for capability in service_info.get('capabilities', []):
                if capability not in capability_index:
                    capability_index[capability] = []
                capability_index[capability].append(service_id)


def health_check_worker():
    """Background worker to check health of registered services"""
    while True:
        time.sleep(HEALTH_CHECK_INTERVAL)

        services_to_check = list(registry.keys())
        for service_id in services_to_check:
            with registry_lock:
                service = registry.get(service_id)
                if not service:
                    continue

                # Only check HTTP services
                if service['mode'] != 'http':
                    continue

                location = service['location']

            # Validate URL to prevent SSRF attacks
            health_url = f"{location}/_module/health"
            if not is_safe_url(health_url):
                print(f"Skipping health check for {service_id}: URL not allowed (SSRF protection)")
                continue

            # Perform health check
            old_status = None
            try:
                response = requests.get(
                    health_url,
                    timeout=HEALTH_CHECK_TIMEOUT
                )

                with registry_lock:
                    if service_id in registry:
                        old_status = registry[service_id].get('status')
                        if response.status_code == 200:
                            registry[service_id]['status'] = 'active'
                            registry[service_id]['failed_checks'] = 0
                            registry[service_id]['last_seen'] = datetime.now().isoformat()
                        else:
                            registry[service_id]['failed_checks'] += 1

            except requests.RequestException:
                with registry_lock:
                    if service_id in registry:
                        registry[service_id]['failed_checks'] += 1

            # Mark as inactive if too many failed checks
            with registry_lock:
                if service_id in registry:
                    failed = registry[service_id].get('failed_checks', 0)
                    if failed >= MAX_FAILED_CHECKS:
                        old_status = registry[service_id].get('status')
                        registry[service_id]['status'] = 'inactive'
                        print(f"Service {service_id} marked as inactive after {failed} failed checks")

                        # Broadcast status change event
                        if old_status != 'inactive':
                            broadcast_event('service.status_changed', {
                                'id': service_id,
                                'old_status': old_status,
                                'new_status': 'inactive'
                            })


@app.route('/api/register', methods=['POST'])
def register_service():
    """Register a new service in the ecosystem"""
    # Validate JSON payload exists
    if not request.json:
        return jsonify({'error': 'Invalid JSON payload'}), 400

    data = request.json

    # Validate required fields exist
    required_fields = ['id', 'name', 'capabilities', 'location', 'mode']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    # Validate field types and formats
    if not isinstance(data['id'], str) or not data['id'].strip():
        return jsonify({'error': 'id must be a non-empty string'}), 400

    if not isinstance(data['name'], str) or not data['name'].strip():
        return jsonify({'error': 'name must be a non-empty string'}), 400

    if not isinstance(data['capabilities'], list):
        return jsonify({'error': 'capabilities must be a list'}), 400

    if not all(isinstance(cap, str) for cap in data['capabilities']):
        return jsonify({'error': 'All capabilities must be strings'}), 400

    if not isinstance(data['location'], str) or not data['location'].strip():
        return jsonify({'error': 'location must be a non-empty string'}), 400

    # Validate location URL format
    if not is_safe_url(data['location']):
        return jsonify({'error': 'location must be a valid localhost or private network URL'}), 400

    if not isinstance(data['mode'], str) or data['mode'] not in ('http', 'embedded', 'standalone'):
        return jsonify({'error': 'mode must be one of: http, embedded, standalone'}), 400

    service_info = {
        'id': data['id'],
        'name': data['name'],
        'version': data.get('version', '1.0.0'),
        'capabilities': data['capabilities'],
        'location': data['location'],
        'mode': data['mode'],
        'status': 'active',
        'registered_at': datetime.now().isoformat(),
        'last_seen': datetime.now().isoformat(),
        'failed_checks': 0,
        'metadata': data.get('metadata', {})
    }

    with registry_lock:
        registry[data['id']] = service_info

        # Update capability index
        for capability in data['capabilities']:
            if capability not in capability_index:
                capability_index[capability] = []
            if data['id'] not in capability_index[capability]:
                capability_index[capability].append(data['id'])

        # Save to disk
        store.save(registry)

    # Broadcast service registration event
    broadcast_event('service.registered', service_info)

    return jsonify({
        'message': 'Service registered successfully',
        'service_id': data['id']
    }), 201


@app.route('/api/unregister/<service_id>', methods=['DELETE'])
def unregister_service(service_id: str):
    """Unregister a service from the ecosystem"""
    with registry_lock:
        if service_id not in registry:
            return jsonify({'error': 'Service not found'}), 404

        service_info = registry[service_id].copy()

        # Remove from capability index
        service_caps = registry[service_id]['capabilities']
        for capability in service_caps:
            if capability in capability_index:
                capability_index[capability] = [
                    sid for sid in capability_index[capability]
                    if sid != service_id
                ]
                if not capability_index[capability]:
                    del capability_index[capability]

        # Remove service
        del registry[service_id]

        # Save to disk
        store.save(registry)

    # Broadcast service unregistration event
    broadcast_event('service.unregistered', {
        'id': service_id,
        'name': service_info.get('name', 'Unknown')
    })

    return jsonify({'message': 'Service unregistered successfully'}), 200


@app.route('/api/services', methods=['GET'])
def list_services():
    """List all registered services"""
    status_filter = request.args.get('status')

    with registry_lock:
        services = list(registry.values())

        if status_filter:
            services = [s for s in services if s['status'] == status_filter]

        return jsonify({
            'services': services,
            'count': len(services)
        })


@app.route('/api/services/<service_id>', methods=['GET'])
def get_service(service_id: str):
    """Get details of a specific service"""
    with registry_lock:
        if service_id not in registry:
            return jsonify({'error': 'Service not found'}), 404

        return jsonify(registry[service_id])


@app.route('/api/capabilities', methods=['GET'])
def list_capabilities():
    """List all available capabilities"""
    with registry_lock:
        capabilities = []
        for capability, service_ids in capability_index.items():
            # Only include active services
            active_services = [
                sid for sid in service_ids
                if registry.get(sid, {}).get('status') == 'active'
            ]

            if active_services:
                capabilities.append({
                    'capability': capability,
                    'providers': active_services,
                    'count': len(active_services)
                })

        return jsonify({
            'capabilities': capabilities,
            'count': len(capabilities)
        })


@app.route('/api/capabilities/<capability_name>', methods=['GET'])
def get_capability(capability_name: str):
    """Find a service providing a specific capability"""
    with registry_lock:
        if capability_name not in capability_index:
            return jsonify({'error': 'Capability not found'}), 404

        service_ids = capability_index[capability_name]

        # Find first active service
        for service_id in service_ids:
            service = registry.get(service_id)
            if service and service['status'] == 'active':
                return jsonify(service)

        # No active services found
        return jsonify({'error': 'No active services provide this capability'}), 503


@app.route('/api/heartbeat/<service_id>', methods=['POST'])
def heartbeat(service_id: str):
    """Update the last seen time for a service"""
    with registry_lock:
        if service_id not in registry:
            return jsonify({'error': 'Service not found'}), 404

        old_status = registry[service_id].get('status')
        registry[service_id]['last_seen'] = datetime.now().isoformat()
        registry[service_id]['status'] = 'active'
        registry[service_id]['failed_checks'] = 0

    # Broadcast heartbeat event (only if status changed)
    if old_status != 'active':
        broadcast_event('service.heartbeat', {
            'id': service_id,
            'status': 'active'
        })

    return jsonify({'message': 'Heartbeat received'})


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get registry statistics"""
    with registry_lock:
        total_services = len(registry)
        active_services = sum(1 for s in registry.values() if s['status'] == 'active')
        inactive_services = total_services - active_services
        total_capabilities = len(capability_index)

        # Group by runtime
        by_runtime = {}
        for service in registry.values():
            runtime = service.get('metadata', {}).get('runtime', 'unknown')
            by_runtime[runtime] = by_runtime.get(runtime, 0) + 1

        return jsonify({
            'total_services': total_services,
            'active_services': active_services,
            'inactive_services': inactive_services,
            'total_capabilities': total_capabilities,
            'services_by_runtime': by_runtime
        })


@app.route('/api/discover', methods=['POST'])
def discover_services():
    """Discover services based on requirements"""
    # Validate JSON payload exists
    if not request.json:
        return jsonify({'error': 'Invalid JSON payload'}), 400

    data = request.json
    required_capabilities = data.get('capabilities', [])
    optional_capabilities = data.get('optional', [])

    # Validate that capabilities are lists of strings
    if not isinstance(required_capabilities, list):
        return jsonify({'error': 'capabilities must be a list'}), 400

    if not isinstance(optional_capabilities, list):
        return jsonify({'error': 'optional must be a list'}), 400

    if not all(isinstance(cap, str) for cap in required_capabilities):
        return jsonify({'error': 'All required capabilities must be strings'}), 400

    if not all(isinstance(cap, str) for cap in optional_capabilities):
        return jsonify({'error': 'All optional capabilities must be strings'}), 400

    with registry_lock:
        matching_services = []

        for service_id, service in registry.items():
            if service['status'] != 'active':
                continue

            service_caps = set(service['capabilities'])
            required_caps = set(required_capabilities)
            optional_caps = set(optional_capabilities)

            # Check if service provides all required capabilities
            if required_caps.issubset(service_caps):
                # Calculate match score
                optional_matches = len(optional_caps.intersection(service_caps))
                match_score = len(required_caps) + optional_matches

                matching_services.append({
                    'service': service,
                    'match_score': match_score,
                    'provides_required': list(required_caps),
                    'provides_optional': list(optional_caps.intersection(service_caps))
                })

        # Sort by match score
        matching_services.sort(key=lambda x: x['match_score'], reverse=True)

        return jsonify({
            'matches': matching_services,
            'count': len(matching_services)
        })


@app.route('/health', methods=['GET'])
def registry_health():
    """Health check for the registry itself"""
    return jsonify({
        'status': 'healthy',
        'service': 'modularity-registry',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/events')
def stream_events():
    """Server-Sent Events endpoint for real-time registry updates"""
    def generate():
        q = Queue(maxsize=1000)

        # Register this client
        with sse_lock:
            sse_clients.append(q)

        try:
            # Send initial connection event
            initial_event = {
                'event': 'connected',
                'timestamp': datetime.now().isoformat(),
                'data': {'message': 'Connected to Modularity Registry event stream'}
            }
            yield f"data: {json.dumps(initial_event)}\n\n"

            # Stream events as they arrive (with keep-alive)
            while True:
                try:
                    event = q.get(timeout=15)
                    yield f"data: {json.dumps(event)}\n\n"
                except Empty:
                    # SSE comment to keep intermediaries from closing idle connection
                    yield ": keep-alive\n\n"
        finally:
            # Unregister this client on disconnect
            with sse_lock:
                if q in sse_clients:
                    sse_clients.remove(q)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


@app.route('/api/track/invocation', methods=['POST'])
def track_invocation():
    """Track a capability invocation between services"""
    # Authenticate request if token is configured (unless in dev mode or insecure mode)
    if REGISTRY_TRACK_TOKEN and not REGISTRY_ALLOW_INSECURE and FLASK_ENV != 'development':
        token = request.headers.get('X-Registry-Token')
        if not token or token != REGISTRY_TRACK_TOKEN:
            return jsonify({'error': 'Unauthorized: Invalid or missing X-Registry-Token header'}), 401

    if not request.json:
        return jsonify({'error': 'Invalid JSON payload'}), 400

    data = request.json
    required = ['consumer_id', 'provider_id', 'capability', 'success']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing required fields'}), 400

    consumer_id = data['consumer_id']
    provider_id = data['provider_id']
    capability = data['capability']
    success = data['success']
    latency_ms = data.get('latency_ms', 0.0)

    now = datetime.now().isoformat()

    with connections_lock:
        # Find or create connection record
        if consumer_id not in connections:
            connections[consumer_id] = []

        conn_list = connections[consumer_id]
        conn = next(
            (c for c in conn_list
             if c.provider_id == provider_id and c.capability == capability),
            None
        )

        if conn is None:
            # New connection
            conn = ConnectionInfo(
                consumer_id=consumer_id,
                provider_id=provider_id,
                capability=capability,
                first_seen=now,
                last_seen=now,
                request_count=1,
                success_count=1 if success else 0,
                total_latency_ms=latency_ms
            )
            conn_list.append(conn)
        else:
            # Update existing connection
            conn.last_seen = now
            conn.request_count += 1
            if success:
                conn.success_count += 1
            conn.total_latency_ms += latency_ms

    # Broadcast invocation event
    broadcast_event('capability.invoked', {
        'consumer_id': consumer_id,
        'provider_id': provider_id,
        'capability': capability,
        'success': success,
        'latency_ms': latency_ms
    })

    return jsonify({'message': 'Invocation tracked'}), 200


@app.route('/api/connections/<service_id>')
def get_connections(service_id: str):
    """Get connections for a service (both as consumer and provider)"""
    with registry_lock:
        if service_id not in registry:
            return jsonify({'error': 'Service not found'}), 404

    with connections_lock:
        # Find where this service is a consumer
        as_consumer = []
        if service_id in connections:
            for conn in connections[service_id]:
                provider_name = registry.get(conn.provider_id, {}).get('name', 'Unknown')
                avg_latency = conn.total_latency_ms / conn.request_count if conn.request_count > 0 else 0
                success_rate = conn.success_count / conn.request_count if conn.request_count > 0 else 0

                as_consumer.append({
                    'provider_id': conn.provider_id,
                    'provider_name': provider_name,
                    'capability': conn.capability,
                    'request_count': conn.request_count,
                    'success_rate': success_rate,
                    'avg_latency_ms': avg_latency,
                    'first_seen': conn.first_seen,
                    'last_seen': conn.last_seen
                })

        # Find where this service is a provider
        as_provider = []
        for consumer_id, conn_list in connections.items():
            for conn in conn_list:
                if conn.provider_id == service_id:
                    consumer_name = registry.get(consumer_id, {}).get('name', 'Unknown')
                    avg_latency = conn.total_latency_ms / conn.request_count if conn.request_count > 0 else 0
                    success_rate = conn.success_count / conn.request_count if conn.request_count > 0 else 0

                    as_provider.append({
                        'consumer_id': consumer_id,
                        'consumer_name': consumer_name,
                        'capability': conn.capability,
                        'request_count': conn.request_count,
                        'success_rate': success_rate,
                        'avg_latency_ms': avg_latency,
                        'first_seen': conn.first_seen,
                        'last_seen': conn.last_seen
                    })

    return jsonify({
        'service_id': service_id,
        'service_name': registry.get(service_id, {}).get('name', 'Unknown'),
        'consuming': as_consumer,
        'providing': as_provider
    })


@app.route('/api/graph')
def get_service_graph():
    """Get the service dependency graph"""
    with registry_lock:
        # Build nodes (all services)
        nodes = [
            {
                'id': service_id,
                'name': service['name'],
                'status': service['status'],
                'capabilities': service['capabilities']
            }
            for service_id, service in registry.items()
        ]

    with connections_lock:
        # Build edges (connections)
        edges = []
        for consumer_id, conn_list in connections.items():
            for conn in conn_list:
                avg_latency = conn.total_latency_ms / conn.request_count if conn.request_count > 0 else 0
                success_rate = conn.success_count / conn.request_count if conn.request_count > 0 else 0

                edges.append({
                    'from': consumer_id,
                    'to': conn.provider_id,
                    'capability': conn.capability,
                    'weight': conn.request_count,
                    'avg_latency_ms': avg_latency,
                    'success_rate': success_rate
                })

    return jsonify({
        'nodes': nodes,
        'edges': edges
    })


def init_registry():
    """Initialize the registry on startup"""
    global registry

    # Load from disk
    stored_data = store.load()
    if stored_data:
        registry.update(stored_data)
        rebuild_capability_index()
        print(f"Loaded {len(registry)} services from storage")

    # Start health check worker
    health_thread = threading.Thread(target=health_check_worker, daemon=True)
    health_thread.start()
    print("Health check worker started")


if __name__ == '__main__':
    init_registry()

    print("=" * 50)
    print("Modularity Registry Service")
    print("=" * 50)
    print("Starting on http://localhost:5000")
    print("API Documentation:")
    print("  POST   /api/register          - Register a service")
    print("  DELETE /api/unregister/<id>   - Unregister a service")
    print("  GET    /api/services          - List all services")
    print("  GET    /api/services/<id>     - Get service details")
    print("  GET    /api/capabilities      - List all capabilities")
    print("  GET    /api/capabilities/<name> - Find service by capability")
    print("  POST   /api/heartbeat/<id>    - Send heartbeat")
    print("  POST   /api/discover          - Discover services by requirements")
    print("  GET    /api/stats             - Get registry statistics")
    print("  GET    /health                - Registry health check")
    print("\nReal-Time & Observability:")
    print("  GET    /api/events            - Server-Sent Events stream")
    print("  POST   /api/track/invocation  - Track capability invocation")
    print("  GET    /api/connections/<id>  - Get service connections")
    print("  GET    /api/graph             - Get service dependency graph")
    print("=" * 50)

    # Use 127.0.0.1 by default for security (localhost only)
    # Set REGISTRY_HOST=0.0.0.0 in environment to bind to all interfaces
    host = os.getenv('REGISTRY_HOST', '127.0.0.1')
    port = int(os.getenv('REGISTRY_PORT', '5000'))
    app.run(host=host, port=port, debug=False)
