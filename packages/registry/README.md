# Modularity Registry Service

Central service discovery and health monitoring for the Modularity ecosystem.

## Overview

The Registry Service provides:
- **Service Discovery** - Find services by capability
- **Health Monitoring** - Track service health status
- **Capability Mapping** - Map capabilities to service instances
- **RESTful API** - Simple HTTP interface for all operations

## Installation

### From Workspace Root

```bash
# Install all workspace packages including registry
uv sync
```

### Standalone Installation

```bash
cd packages/registry
uv pip install -e .
```

## Usage

### Starting the Registry

```bash
# From workspace root
uv run --directory packages/registry python registry_service.py

# Or from registry directory
cd packages/registry
uv run python registry_service.py

# Or with activated venv
source ../../.venv/bin/activate
python registry_service.py
```

The registry will start on **http://localhost:5000** by default.

### Command-Line Options

```bash
# Custom host and port
python registry_service.py --host 0.0.0.0 --port 8080

# Enable debug mode
python registry_service.py --debug
```

## API Endpoints

### Service Registration

**POST /api/register**

Register a new service with the registry.

```bash
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "id": "hello-service",
    "name": "Hello Service",
    "version": "1.0.0",
    "capabilities": ["greet", "farewell"],
    "location": "http://localhost:3000",
    "mode": "http"
  }'
```

**Response:**
```json
{
  "status": "registered",
  "service_id": "hello-service"
}
```

### List Services

**GET /api/services**

Get all registered services.

```bash
curl http://localhost:5000/api/services
```

**Response:**
```json
{
  "services": [
    {
      "id": "hello-service",
      "name": "Hello Service",
      "status": "healthy",
      "capabilities": ["greet", "farewell"],
      "location": "http://localhost:3000"
    }
  ]
}
```

### Find Service by Capability

**GET /api/capabilities/{capability_name}**

Find a service that provides a specific capability.

```bash
curl http://localhost:5000/api/capabilities/greet
```

**Response:**
```json
{
  "id": "hello-service",
  "name": "Hello Service",
  "location": "http://localhost:3000",
  "mode": "http",
  "capabilities": ["greet", "farewell"],
  "status": "healthy"
}
```

### Get Service Details

**GET /api/services/{service_id}**

Get detailed information about a specific service.

```bash
curl http://localhost:5000/api/services/hello-service
```

### Unregister Service

**DELETE /api/services/{service_id}**

Remove a service from the registry.

```bash
curl -X DELETE http://localhost:5000/api/services/hello-service
```

### Health Check

**GET /health**

Check if the registry is running.

```bash
curl http://localhost:5000/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "modularity-registry",
  "timestamp": "2025-10-17T02:59:31.123456"
}
```

## Configuration

### Environment Variables

- `REGISTRY_HOST` - Host to bind to (default: 127.0.0.1)
- `REGISTRY_PORT` - Port to listen on (default: 5000)
- `REGISTRY_DEBUG` - Enable debug mode (default: false)
- `HEALTH_CHECK_INTERVAL` - Seconds between health checks (default: 30)

### Example

```bash
export REGISTRY_HOST=0.0.0.0
export REGISTRY_PORT=8080
export REGISTRY_DEBUG=true
uv run python registry_service.py
```

## Development

### Running Tests

```bash
# From registry directory
cd packages/registry
uv run pytest tests/ -v

# With coverage
uv run pytest tests/ --cov=. --cov-report=html

# From workspace root
uv run --directory packages/registry pytest tests/
```

### Code Quality

```bash
# Run linting
uv run flake8 registry_service.py

# Format code
uv run black registry_service.py tests/

# Type checking
uv run mypy registry_service.py
```

### Adding Dependencies

```bash
cd packages/registry
uv add <package-name>
```

## Package Details

- **Package Name:** `modularity-registry`
- **Main Script:** `registry_service.py`
- **Python Version:** >=3.9
- **Dependencies:** flask, flask-cors, requests

## Architecture

```
┌─────────────────────────────────────────┐
│         Registry Service                 │
│  ┌────────────────────────────────┐     │
│  │   Service Store (In-Memory)    │     │
│  │  - Service metadata            │     │
│  │  - Capability index            │     │
│  │  - Health status               │     │
│  └────────────────────────────────┘     │
│                                          │
│  ┌────────────────────────────────┐     │
│  │   Health Monitor (Background)  │     │
│  │  - Periodic health checks      │     │
│  │  - Status updates              │     │
│  └────────────────────────────────┘     │
│                                          │
│  ┌────────────────────────────────┐     │
│  │      REST API (Flask)          │     │
│  │  - Registration                │     │
│  │  - Discovery                   │     │
│  │  - Query                       │     │
│  └────────────────────────────────┘     │
└─────────────────────────────────────────┘
```

## Security

The registry implements several security measures:

- **CORS Protection** - Configured allowed origins
- **Input Validation** - All endpoints validate input
- **SSRF Protection** - Health check URLs validated
- **Localhost Binding** - Default bind to 127.0.0.1
- **No Execution** - Registry doesn't execute remote code

### Production Deployment

For production:

1. Use environment variables for configuration
2. Enable TLS/HTTPS (via reverse proxy)
3. Implement authentication/authorization
4. Use persistent storage (Redis/PostgreSQL)
5. Monitor registry health
6. Set up service mesh integration

## Scaling

The current implementation uses in-memory storage. For production:

### Option 1: Redis Backend
```python
# Store services in Redis for persistence
import redis
r = redis.Redis(host='localhost', port=6379)
```

### Option 2: Distributed Registry
```python
# Use Consul, etcd, or ZooKeeper
# For multi-datacenter deployments
```

### Option 3: Database Backend
```python
# PostgreSQL for persistent service catalog
# With proper indexing on capabilities
```

## Monitoring

Key metrics to monitor:

- **Service Count** - Number of registered services
- **Health Check Success Rate** - % of successful checks
- **API Response Time** - Registry endpoint latency
- **Registration Rate** - Services registered per minute
- **Query Rate** - Discovery queries per second

## Troubleshooting

### Registry Won't Start

```bash
# Check if port is already in use
lsof -i :5000

# Try a different port
uv run python registry_service.py --port 8080
```

### Services Not Registering

```bash
# Check registry is accessible
curl http://localhost:5000/health

# Verify network connectivity
ping localhost

# Check firewall rules
```

### Health Checks Failing

```bash
# Check service is running
curl http://localhost:3000/_module/health

# Verify service URL is correct
# Check SSRF protection settings
```

## Examples

See the [examples directory](../../examples/) for complete working examples showing registry integration:
- [Hello World](../../examples/01-hello-world/) - Basic registration
- [Weather System](../../examples/02-weather-system/) - Multi-service discovery

## License

MIT License - see [LICENSE](../../LICENSE) for details.
