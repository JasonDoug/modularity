# Real-Time Infrastructure and Registry TUI Design

**Status**: 🚧 **TBD - Pending Real-Time Infrastructure Implementation**

**Created**: 2025-10-17
**Last Updated**: 2025-10-17

---

## Executive Summary

This document outlines the design for two interconnected features:

1. **Real-Time Infrastructure**: Add WebSocket/SSE support to Registry and SDK for live updates
2. **Registry Terminal UI (TUI)**: An htop-like monitoring dashboard for the Modularity ecosystem

**Decision**: These features are being deferred until the real-time infrastructure is properly architected and implemented across the entire Modularity project. Building real-time capabilities as a foundational enhancement will benefit many features beyond just the TUI.

---

## Background

### Current Architecture Limitations

During exploration for the TUI feature, we discovered critical architectural gaps:

#### ❌ No Real-Time Updates
- Registry uses **polling-only** architecture
- No WebSocket, Server-Sent Events (SSE), or push notifications
- Clients must repeatedly poll `/api/services` for changes
- SDK caches service locations for 60 seconds

#### ❌ No Connection Tracking
- Registry doesn't track which services invoke which other services
- No service-to-service relationship graph
- No visibility into capability usage patterns
- No request frequency or connection metrics

#### ❌ Limited Observability
- Health checks are background-only (every 30s)
- No real-time service lifecycle events
- No connection telemetry or tracing

### Why Real-Time Infrastructure First?

Building real-time capabilities into the Registry and SDK provides benefits far beyond the TUI:

1. **Service Discovery**: Instant notification when services register/unregister
2. **Health Monitoring**: Real-time status updates without polling
3. **Event-Driven Architecture**: Foundation for distributed event bus
4. **Observability**: Live metrics and connection tracking
5. **Developer Experience**: Faster feedback loops in development
6. **Future Features**: Enables many observability and debugging tools

---

## Part 1: Real-Time Infrastructure Requirements

### 1.1 Registry Real-Time API

#### WebSocket Endpoint
```
WS /api/stream
```

**Event Types to Broadcast**:
```json
{
  "event": "service.registered",
  "timestamp": "2025-10-17T10:30:00Z",
  "data": {
    "id": "hello-service",
    "name": "Hello Service",
    "capabilities": ["greet"],
    "status": "active"
  }
}

{
  "event": "service.status_changed",
  "timestamp": "2025-10-17T10:30:15Z",
  "data": {
    "id": "hello-service",
    "old_status": "active",
    "new_status": "inactive"
  }
}

{
  "event": "capability.invoked",
  "timestamp": "2025-10-17T10:30:20Z",
  "data": {
    "capability": "greet",
    "provider_id": "hello-service",
    "consumer_id": "web-frontend",
    "success": true
  }
}
```

**Complete Event Catalog**:
- `service.registered` - New service joins registry
- `service.unregistered` - Service leaves registry
- `service.status_changed` - Health status changes (active ↔ inactive)
- `service.heartbeat` - Service sends heartbeat
- `capability.invoked` - Service invokes capability from another service
- `registry.stats_updated` - Periodic statistics update

#### Alternative: Server-Sent Events (SSE)
```
GET /api/events
```
- Simpler than WebSocket (one-way from server)
- Sufficient if clients only need to receive updates
- Better for simple monitoring tools

**Recommendation**: Start with SSE (simpler), add WebSocket later if bidirectional needed.

### 1.2 Connection Tracking System

#### New Registry Data Structures

```python
# Track active connections between services
connections: Dict[str, List[Connection]] = {}

class Connection:
    consumer_id: str      # Service making the request
    provider_id: str      # Service providing the capability
    capability: str       # Capability being used
    first_seen: datetime  # When connection first established
    last_seen: datetime   # Most recent invocation
    request_count: int    # Total invocations
```

#### New Registry Endpoints

**POST /api/track/invocation**
```json
{
  "consumer_id": "web-frontend",
  "provider_id": "hello-service",
  "capability": "greet",
  "timestamp": "2025-10-17T10:30:00Z",
  "success": true,
  "latency_ms": 45
}
```

**GET /api/connections/{service_id}**
```json
{
  "service_id": "hello-service",
  "consumers": [
    {
      "id": "web-frontend",
      "name": "Web Frontend",
      "capabilities_used": ["greet"],
      "request_count": 1234,
      "last_seen": "2025-10-17T10:30:00Z"
    }
  ],
  "providers": [
    {
      "id": "auth-service",
      "name": "Auth Service",
      "capabilities_used": ["authenticate"],
      "request_count": 567,
      "last_seen": "2025-10-17T10:29:00Z"
    }
  ]
}
```

**GET /api/graph**
```json
{
  "nodes": [
    {"id": "hello-service", "name": "Hello Service", "status": "active"},
    {"id": "web-frontend", "name": "Web Frontend", "status": "active"}
  ],
  "edges": [
    {
      "from": "web-frontend",
      "to": "hello-service",
      "capability": "greet",
      "weight": 1234
    }
  ]
}
```

### 1.3 SDK Modifications

#### Automatic Invocation Tracking

```python
# In ServiceProxy.invoke()
def invoke(self, capability, params):
    start_time = time.time()
    try:
        result = self._invoke_http(capability, params)
        success = True
        return result
    except Exception as e:
        success = False
        raise
    finally:
        # Report invocation to registry
        self._track_invocation(
            consumer_id=self.sdk.manifest['id'],
            provider_id=self.service_info['id'],
            capability=capability,
            success=success,
            latency_ms=(time.time() - start_time) * 1000
        )
```

#### Real-Time Service Discovery

```python
# Subscribe to service updates
sdk = ModularitySDK("app.manifest.json")
sdk.subscribe_to_registry_events(on_event=handle_registry_event)

def handle_registry_event(event):
    if event['event'] == 'service.registered':
        # Invalidate cache, new service available
        sdk.locator.clear_cache()
    elif event['event'] == 'service.status_changed':
        # Update cached service status
        sdk.locator.update_service_status(event['data'])
```

### 1.4 Technology Choices

#### For Registry (Flask-based)

**Option A: Flask-SocketIO**
- Pros: Seamless Flask integration, mature, widely used
- Cons: Adds dependency on Socket.IO client library
- **Use Case**: If we want bidirectional communication

**Option B: SSE with Flask**
- Pros: Simple HTTP-based, no extra libraries, works everywhere
- Cons: One-way only (server → client)
- **Use Case**: For monitoring/observability tools
- **Recommendation**: ✅ Start here (simplest)

**Option C: Hybrid Approach**
- SSE for broadcasts (`/api/events`)
- REST POST for tracking (`/api/track/invocation`)
- **Recommendation**: ✅ Best balance

#### Example SSE Implementation

```python
from flask import Response
import queue

# Event queue for all connected clients
event_queues = []

@app.route('/api/events')
def stream_events():
    """Server-Sent Events endpoint"""
    q = queue.Queue()
    event_queues.append(q)

    def generate():
        try:
            while True:
                event = q.get()  # Blocks until event available
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            event_queues.remove(q)

    return Response(generate(), mimetype='text/event-stream')

def broadcast_event(event_type, data):
    """Broadcast event to all SSE clients"""
    event = {
        'event': event_type,
        'timestamp': datetime.now().isoformat(),
        'data': data
    }
    for q in event_queues:
        q.put(event)

# Example: broadcast when service registers
@app.route('/api/register', methods=['POST'])
def register_service():
    # ... existing registration logic ...

    broadcast_event('service.registered', service_info)
    return jsonify({'message': 'Service registered'})
```

---

## Part 2: Registry TUI Design (Post Real-Time)

### 2.1 Feature Overview

**Goal**: An htop-like terminal UI for monitoring the Modularity ecosystem in real-time.

**Key Capabilities**:
- ✅ Real-time service list with live status updates
- ✅ Interactive selection to view service details
- ✅ Display service capabilities
- ✅ Show which services are connecting to selected service
- ✅ Connection statistics (request count, frequency, last seen)
- ✅ Filter by status (active/inactive)
- ✅ Search/filter by service name
- ✅ Health check history visualization

### 2.2 Technology Stack

**Recommended**: [Textual](https://textual.textualize.io/)

**Why Textual?**
- Modern, actively maintained (2024+)
- Rich integration (already used in CLI)
- CSS-like styling system
- Mouse and keyboard support
- Reactive/live updates built-in
- Excellent documentation
- Production-ready (used by AWS CLI, etc.)

**Alternative Considered**: Rich Live Display
- Simpler but less interactive
- No mouse support
- Better for simple dashboards only

### 2.3 UI Layout (Split View)

```
┌─────────────────────────────────────────────────────────────────┐
│ Modularity Registry Monitor               [Filters: All ▼]     │
├─────────────────────────────┬───────────────────────────────────┤
│ Services (5 active, 1 inac) │ Service Details                   │
│                              │                                   │
│ ● hello-service              │ Name: Hello World Service         │
│   greet                      │ Status: ● Active                  │
│                              │ Version: 1.0.0                    │
│ ● auth-service               │ Location: http://localhost:3100   │
│   authenticate, authorize    │ Uptime: 2h 34m                    │
│                              │                                   │
│ ● web-frontend               │ Capabilities Provided:            │
│   (none)                     │   • greet                         │
│                              │                                   │
│ ○ weather-service            │ Connected Consumers (2):          │
│   get_forecast               │   • web-frontend                  │
│                              │     - 1,234 requests              │
│ ● database-service           │     - Last: 2s ago                │
│   query, insert              │   • mobile-app                    │
│                              │     - 567 requests                │
│                              │     - Last: 15s ago               │
├─────────────────────────────┴───────────────────────────────────┤
│ [F1] Help  [F2] Filter  [F3] Search  [/] Search  [q] Quit      │
└─────────────────────────────────────────────────────────────────┘
```

### 2.4 Package Structure

**New Package**: `packages/registry-tui`

```
packages/registry-tui/
├── pyproject.toml
├── README.md
├── modularity_tui/
│   ├── __init__.py
│   ├── app.py              # Main Textual app
│   ├── widgets/
│   │   ├── service_list.py    # Left panel: scrollable service list
│   │   ├── service_detail.py  # Right panel: service details
│   │   └── header.py          # Top bar with stats
│   ├── api_client.py       # Registry API + SSE client
│   └── models.py           # Data models
└── tests/
    └── test_tui.py
```

**Dependencies** (pyproject.toml):
```toml
[project]
name = "modularity-tui"
version = "0.1.0"
description = "Terminal UI for Modularity Registry monitoring"
requires-python = ">=3.9"
dependencies = [
    "textual>=0.40.0",
    "rich>=13.7.0",
    "requests>=2.31.0",
    "httpx>=0.25.0",  # For async HTTP and SSE
]

[project.scripts]
modularity-tui = "modularity_tui.app:main"
```

### 2.5 Key Features Detail

#### Real-Time Updates
- Connect to Registry SSE endpoint (`/api/events`)
- Update service list live as services register/unregister
- Flash/highlight when service status changes
- Auto-scroll to newly registered services (optional)

#### Service Selection
- Arrow keys or mouse to select service
- Right panel updates immediately
- Show loading state while fetching details

#### Connection Visualization
```
Connected Consumers (2):
┌─────────────────────────────────────────┐
│ ● web-frontend                          │
│   Capabilities Used: greet              │
│   Requests: 1,234 (avg 12/min)          │
│   Last seen: 2s ago                     │
│   Latency: avg 45ms, p95 78ms           │
├─────────────────────────────────────────┤
│ ● mobile-app                            │
│   Capabilities Used: greet              │
│   Requests: 567 (avg 5/min)             │
│   Last seen: 15s ago                    │
│   Latency: avg 120ms, p95 200ms         │
└─────────────────────────────────────────┘

Dependencies (1):
┌─────────────────────────────────────────┐
│ ● auth-service                          │
│   Capabilities Used: authenticate       │
│   Requests: 892                         │
│   Last seen: 5s ago                     │
└─────────────────────────────────────────┘
```

#### Filtering and Search
- Filter dropdown: All / Active / Inactive
- Live search: Type `/` then search term
- Results update as you type
- Clear with Esc

#### Status Indicators
- 🟢 Green dot: Active service
- 🔴 Red dot: Inactive service
- 🟡 Yellow dot: Degraded (high latency)
- ⚪ Gray dot: Unknown status

#### Keyboard Shortcuts
- `↑/↓` or `j/k` - Navigate service list
- `Enter` - Select service
- `/` - Start search
- `f` - Toggle filter
- `r` - Refresh all data
- `q` - Quit
- `?` - Help overlay

### 2.6 Update Frequency

**Recommendation**: Configurable with default of **2 seconds**

```toml
# ~/.modularity/tui-config.toml
[display]
refresh_interval = 2  # seconds
auto_scroll = true
theme = "dark"

[filters]
default_status = "all"  # all, active, inactive
```

**Real-Time Updates**:
- SSE events: Instant (no polling needed)
- Connection stats: Poll every 2s from `/api/connections/{id}`
- Health history: Poll every 5s

### 2.7 Entry Point

**Option 1: Standalone command** (Recommended)
```bash
modularity-tui
modularity-tui --registry http://localhost:5000
```

**Option 2: CLI subcommand**
```bash
modularity tui
```

**Recommendation**: Option 1 (standalone) - cleaner separation, focused tool

---

## Part 3: Implementation Roadmap

### Phase 1: Real-Time Infrastructure (Priority)

1. **Add SSE endpoint to Registry** (`/api/events`)
   - Broadcast service lifecycle events
   - Test with curl/postman

2. **Add connection tracking** (`/api/track/invocation`, `/api/connections/{id}`)
   - Track consumer → provider relationships
   - Store connection metadata

3. **Modify SDK to track invocations**
   - Auto-report capability invocations to registry
   - Make tracking optional (config flag)

4. **Add connection graph endpoint** (`/api/graph`)
   - Return nodes and edges for visualization
   - Calculate metrics (request counts, latencies)

5. **Write tests**
   - SSE event broadcasting
   - Connection tracking accuracy
   - Concurrent access safety

6. **Update documentation**
   - API reference for new endpoints
   - SDK integration guide
   - Migration guide for existing services

**Estimated Effort**: 2-3 weeks

### Phase 2: Registry TUI (After Real-Time Complete)

1. **Set up new package** (`packages/registry-tui`)
   - Initialize with uv
   - Add Textual dependency

2. **Build core widgets**
   - ServiceList (left panel)
   - ServiceDetail (right panel)
   - HeaderBar (stats)

3. **Implement SSE client**
   - Connect to `/api/events`
   - Parse and dispatch events to UI

4. **Add interactivity**
   - Keyboard navigation
   - Service selection
   - Filtering

5. **Polish UI**
   - Colors and styling
   - Loading states
   - Error handling

6. **Testing and docs**
   - Unit tests for widgets
   - Integration tests
   - User guide

**Estimated Effort**: 1-2 weeks

---

## Part 4: Open Questions

### Registry Real-Time Design

1. **Event Filtering**: Should SSE clients be able to subscribe to specific events only?
   ```
   /api/events?filter=service.registered,service.status_changed
   ```

2. **Authentication**: Real-time endpoints need auth? (currently registry has none)

3. **Rate Limiting**: Should we limit event broadcast frequency to prevent overwhelming clients?

4. **Persistence**: Should connection history be persisted to disk or memory-only?

5. **Metrics Aggregation**: Should registry calculate metrics (avg latency, request rate) or just store raw events?

### TUI Design

1. **Graph View**: Add a third view showing service dependency graph (Graphviz-style)?

2. **Historical Data**: Show graphs/charts for request rate over time? (requires time-series storage)

3. **Multi-Registry**: Support monitoring multiple registries simultaneously?

4. **Export**: Allow exporting current state to JSON/CSV for analysis?

5. **Alerts**: Should TUI support alert rules? (e.g., notify when service goes inactive)

---

## Part 5: Benefits Beyond TUI

Once real-time infrastructure is built, it enables:

1. **IDE Integration**: VS Code extension showing live service status
2. **CI/CD Integration**: Wait for services to be healthy in deployment scripts
3. **Debug Tools**: Live request tracing and inspection
4. **Metrics Dashboards**: Prometheus/Grafana integration
5. **Service Mesh Integration**: Foundation for Istio/Linkerd observability
6. **Load Balancing**: Smart routing based on real-time metrics
7. **Auto-Scaling**: Scale services based on capability demand
8. **Chaos Engineering**: Inject failures and observe propagation in real-time

---

## Part 6: References

### Technologies
- [Textual](https://textual.textualize.io/) - Modern Python TUI framework
- [Server-Sent Events (SSE)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) - HTTP streaming standard
- [Flask-SSE](https://github.com/singingwolfboy/flask-sse) - SSE support for Flask

### Related Work
- [htop](https://htop.dev/) - Inspiration for UI layout
- [lazydocker](https://github.com/jesseduffield/lazydocker) - TUI for Docker monitoring
- [k9s](https://k9scli.io/) - Kubernetes TUI (excellent UX reference)

### Internal Docs
- `packages/registry/README.md` - Registry API documentation
- `packages/sdk-python/README.md` - SDK integration guide
- `docs/architecture/overview.md` - Overall system architecture

---

## Appendix A: Preliminary Code Sketches

### SSE Event Stream (Registry)

```python
# packages/registry/registry_service.py

from queue import Queue
from typing import List

# Global event queues for SSE clients
sse_clients: List[Queue] = []

@app.route('/api/events')
def stream_events():
    """Server-Sent Events endpoint for real-time updates"""
    def generate():
        q = Queue()
        sse_clients.append(q)
        try:
            # Send initial connection event
            yield f"data: {json.dumps({'event': 'connected', 'timestamp': datetime.now().isoformat()})}\n\n"

            # Stream events as they arrive
            while True:
                event = q.get()  # Blocks until event available
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            sse_clients.remove(q)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

def broadcast_event(event_type: str, data: dict):
    """Broadcast event to all connected SSE clients"""
    event = {
        'event': event_type,
        'timestamp': datetime.now().isoformat(),
        'data': data
    }

    for client_queue in sse_clients:
        try:
            client_queue.put_nowait(event)
        except:
            pass  # Client disconnected, will be removed on next iteration
```

### Connection Tracking (Registry)

```python
# packages/registry/registry_service.py

from dataclasses import dataclass
from typing import Dict, List

@dataclass
class ConnectionInfo:
    consumer_id: str
    provider_id: str
    capability: str
    first_seen: datetime
    last_seen: datetime
    request_count: int = 0
    success_count: int = 0
    total_latency_ms: float = 0.0

# Track connections: consumer_id -> List[ConnectionInfo]
connections: Dict[str, List[ConnectionInfo]] = {}

@app.route('/api/track/invocation', methods=['POST'])
def track_invocation():
    """Track a capability invocation between services"""
    data = request.json

    required = ['consumer_id', 'provider_id', 'capability', 'success', 'latency_ms']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing required fields'}), 400

    consumer_id = data['consumer_id']

    # Find or create connection record
    if consumer_id not in connections:
        connections[consumer_id] = []

    conn_list = connections[consumer_id]
    conn = next(
        (c for c in conn_list
         if c.provider_id == data['provider_id'] and c.capability == data['capability']),
        None
    )

    now = datetime.now()
    if conn is None:
        # New connection
        conn = ConnectionInfo(
            consumer_id=consumer_id,
            provider_id=data['provider_id'],
            capability=data['capability'],
            first_seen=now,
            last_seen=now,
            request_count=1,
            success_count=1 if data['success'] else 0,
            total_latency_ms=data['latency_ms']
        )
        conn_list.append(conn)
    else:
        # Update existing connection
        conn.last_seen = now
        conn.request_count += 1
        if data['success']:
            conn.success_count += 1
        conn.total_latency_ms += data['latency_ms']

    # Broadcast event
    broadcast_event('capability.invoked', {
        'consumer_id': consumer_id,
        'provider_id': data['provider_id'],
        'capability': data['capability'],
        'success': data['success'],
        'latency_ms': data['latency_ms']
    })

    return jsonify({'message': 'Invocation tracked'}), 200

@app.route('/api/connections/<service_id>')
def get_connections(service_id: str):
    """Get connections for a service (both as consumer and provider)"""
    with registry_lock:
        if service_id not in registry:
            return jsonify({'error': 'Service not found'}), 404

        # Find where this service is a consumer
        as_consumer = connections.get(service_id, [])

        # Find where this service is a provider
        as_provider = []
        for consumer_id, conn_list in connections.items():
            for conn in conn_list:
                if conn.provider_id == service_id:
                    as_provider.append({
                        'consumer_id': consumer_id,
                        'consumer_name': registry.get(consumer_id, {}).get('name', 'Unknown'),
                        'capability': conn.capability,
                        'request_count': conn.request_count,
                        'success_rate': conn.success_count / conn.request_count if conn.request_count > 0 else 0,
                        'avg_latency_ms': conn.total_latency_ms / conn.request_count if conn.request_count > 0 else 0,
                        'last_seen': conn.last_seen.isoformat()
                    })

        return jsonify({
            'service_id': service_id,
            'as_consumer': [{
                'provider_id': c.provider_id,
                'provider_name': registry.get(c.provider_id, {}).get('name', 'Unknown'),
                'capability': c.capability,
                'request_count': c.request_count,
                'success_rate': c.success_count / c.request_count if c.request_count > 0 else 0,
                'avg_latency_ms': c.total_latency_ms / c.request_count if c.request_count > 0 else 0,
                'last_seen': c.last_seen.isoformat()
            } for c in as_consumer],
            'as_provider': as_provider
        })
```

### Textual TUI Skeleton

```python
# packages/registry-tui/modularity_tui/app.py

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Header, Footer, Static, ListView, ListItem
from textual.reactive import reactive
import httpx
import asyncio

class ServiceList(ListView):
    """Scrollable list of services"""

    def on_mount(self):
        # Load services from registry
        self.refresh_services()

    async def refresh_services(self):
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:5000/api/services")
            services = response.json()['services']

            self.clear()
            for service in services:
                status = "●" if service['status'] == 'active' else "○"
                self.append(ListItem(Static(f"{status} {service['name']}")))

class ServiceDetail(Static):
    """Service detail panel"""

    service_id = reactive(None)

    async def watch_service_id(self, service_id: str):
        if service_id:
            await self.load_service_details(service_id)

    async def load_service_details(self, service_id: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:5000/api/services/{service_id}")
            service = response.json()

            # Format service details
            details = f"""
Name: {service['name']}
Status: {service['status']}
Version: {service['version']}
Location: {service['location']}

Capabilities:
{chr(10).join(f"  • {cap}" for cap in service['capabilities'])}
"""
            self.update(details)

class RegistryTUI(App):
    """A Textual TUI for monitoring the Modularity Registry."""

    CSS = """
    #service-list {
        width: 40%;
    }

    #service-detail {
        width: 60%;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield ServiceList(id="service-list")
            yield ServiceDetail(id="service-detail")
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected):
        """Handle service selection"""
        service_detail = self.query_one("#service-detail", ServiceDetail)
        # Extract service ID from selected item
        # service_detail.service_id = selected_service_id

    def action_refresh(self):
        """Refresh data"""
        service_list = self.query_one("#service-list", ServiceList)
        asyncio.create_task(service_list.refresh_services())

def main():
    app = RegistryTUI()
    app.run()

if __name__ == "__main__":
    main()
```

---

## Document History

- **2025-10-17**: Initial draft during TUI feature discovery
  - Identified real-time infrastructure as prerequisite
  - Documented TUI requirements pending real-time implementation
  - Marked as TBD until foundation is built
