# Modularity SDK - Python

Python implementation of the Modularity SDK for building polymorphic applications.

## Installation

### From Workspace Root

```bash
# Install all workspace packages including SDK
uv sync
```

### Standalone Installation

```bash
cd packages/sdk-python
uv pip install -e .
```

### Install with Dev Dependencies

```bash
cd packages/sdk-python
uv sync  # Installs dev dependencies from pyproject.toml
```

## Usage

### Basic Usage

```python
from modularity_sdk import ModularitySDK, ModuleInterface

# Load SDK with manifest
sdk = ModularitySDK("app.manifest.json")

# Option 1: Run as standalone HTTP service
sdk.run_standalone(port=3000)

# Option 2: Load as embedded module (in-process)
module = sdk.load_as_module(config={'key': 'value'})
result = module.invoke('capability-name', {'param': 'value'})

# Option 3: Invoke remote capability via service discovery
result = sdk.invoke_capability('capability-name', {'param': 'value'})
```

### Implementing a Module

```python
from modularity_sdk import ModuleInterface
from typing import Dict, List, Any

class MyModule(ModuleInterface):
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Called when module is loaded"""
        self.config = config
        return True

    def get_capabilities(self) -> List[str]:
        """Return list of capabilities"""
        return ['my-capability']

    def invoke(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a capability"""
        if capability == 'my-capability':
            return {'result': 'success', 'data': params}
        raise ValueError(f"Unknown capability: {capability}")

    def handle_event(self, event: str, data: Dict[str, Any]):
        """Handle events from other modules"""
        print(f"Received event: {event}")

    def shutdown(self):
        """Cleanup before module unload"""
        pass
```

### Service Discovery

```python
from modularity_sdk import ServiceLocator

# Create service locator
locator = ServiceLocator(registry_url="http://localhost:5000")

# Find a service providing a specific capability
proxy = locator.get_capability("user-authentication")

# Invoke the capability
result = proxy.invoke("authenticate", {
    "username": "alice",
    "password": "secret"
})
```

### Event Bus

```python
from modularity_sdk import EventBus

# Create event bus
bus = EventBus()

# Subscribe to events
def handle_user_created(data):
    print(f"New user: {data['username']}")

bus.subscribe("user.created", handle_user_created)

# Publish events
bus.publish("user.created", {"username": "alice", "id": 123})
```

## Development

### Running Tests

```bash
# From SDK directory
cd packages/sdk-python
uv run pytest tests/ -v

# With coverage
uv run pytest tests/ --cov=modularity_sdk --cov-report=html

# From workspace root
uv run --directory packages/sdk-python pytest tests/
```

### Code Quality

```bash
# Run linting
uv run flake8 modularity_sdk/

# Format code
uv run black modularity_sdk/ tests/

# Type checking (if using mypy)
uv run mypy modularity_sdk/
```

### Adding Dependencies

```bash
# Add a runtime dependency
cd packages/sdk-python
uv add <package-name>

# Add a dev dependency
uv add --dev <package-name>
```

## Package Details

- **Package Name:** `modularity-sdk`
- **Module Name:** `modularity_sdk`
- **Main Class:** `ModularitySDK`
- **Python Version:** >=3.9
- **Dependencies:** flask, flask-cors, requests

### Development Dependencies
- pytest >=7.4.3
- pytest-cov >=4.1.0
- flake8 >=7.0.0
- black >=23.12.1

## API Reference

### ModularitySDK

Main SDK class for ecosystem integration.

**Constructor:**
```python
ModularitySDK(manifest_path: str = "app.manifest.json",
              registry_url: str = "http://localhost:5000")
```

**Methods:**
- `run_standalone(host: str = "0.0.0.0", port: Optional[int] = None)` - Run as standalone HTTP service
- `load_as_module(parent_config: Optional[Dict] = None) -> ModuleInterface` - Load as embedded module
- `invoke_capability(capability: str, params: Dict) -> Dict` - Invoke remote capability
- `publish_event(event_name: str, data: Dict)` - Publish event to ecosystem
- `subscribe_event(event_name: str, handler: Callable)` - Subscribe to events
- `load_local_module(module_path: str, config: Optional[Dict] = None) -> ModuleInterface` - Load another local module

### ModuleInterface

Abstract base class for all modules.

**Abstract Methods:**
- `initialize(config: Dict[str, Any]) -> bool` - Initialize the module
- `get_capabilities() -> List[str]` - Return list of capabilities
- `invoke(capability: str, params: Dict[str, Any]) -> Dict[str, Any]` - Execute a capability
- `handle_event(event: str, data: Dict[str, Any])` - Handle events
- `shutdown()` - Cleanup before unload

### ServiceLocator

Find and connect to services by capability.

**Constructor:**
```python
ServiceLocator(registry_url: str = "http://localhost:5000")
```

**Methods:**
- `get_capability(capability_name: str) -> ServiceProxy` - Find service by capability
- `clear_cache()` - Clear the service cache

### ServiceProxy

Proxy for invoking remote services.

**Methods:**
- `invoke(capability: str, params: Dict[str, Any]) -> Dict[str, Any]` - Invoke remote capability

### EventBus

In-memory event bus for pub/sub messaging.

**Methods:**
- `publish(event_name: str, data: Dict[str, Any])` - Publish an event
- `subscribe(event_name: str, handler: Callable)` - Subscribe to events
- `unsubscribe(event_name: str, handler: Callable)` - Unsubscribe from events

## Examples

See the [examples directory](../../examples/) for complete working examples:
- [Hello World](../../examples/01-hello-world/) - Minimal example
- [Weather System](../../examples/02-weather-system/) - Multi-service example

## License

MIT License - see [LICENSE](../../LICENSE) for details.
