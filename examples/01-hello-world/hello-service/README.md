# Hello World Service

The simplest possible ecosystem-compatible service. Perfect for learning the basics and as a template for new services.

**Time to understand:** 5 minutes
**Lines of code:** ~50 lines
**Complexity:** Minimal

---

## Overview

A minimal "Hello World" service that demonstrates the absolute basics:
- ✅ Valid manifest
- ✅ ModuleInterface implementation
- ✅ One simple capability
- ✅ Runs standalone
- ✅ Loads as module
- ✅ Ecosystem compatible

**What it does:** Provides a single `greet` capability that returns a greeting message.

---

## Quick Start

### 1. Install Dependencies

```bash
cd examples/01-hello-world/hello-service
uv sync
```

### 2. Run Standalone

```bash
uv run python src/standalone.py
```

The service will start on port 3100.

### 3. Test It

```bash
# Health check
curl http://localhost:3100/_module/health

# Get capabilities
curl http://localhost:3100/_module/capabilities

# Invoke the greet capability
curl -X POST http://localhost:3100/_module/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "greet", "params": {"name": "Alice"}}'

# Response:
# {
#   "message": "Hello, Alice!",
#   "timestamp": "2025-10-16T10:30:00.123456"
# }
```

### 4. Run Tests

```bash
uv run python test_hello.py
```

---

## Directory Structure

```
hello-service/
├── app.manifest.json          # Service declaration
├── config.defaults.json       # Default configuration
├── src/
│   ├── module.py             # Module implementation
│   └── standalone.py         # Standalone entry point
├── test_hello.py             # Basic tests
├── pyproject.toml            # Dependencies (uv format)
└── README.md                 # This file
```

---

## How It Works

### 1. Manifest Declaration

The `app.manifest.json` declares what the service provides:

```json
{
  "id": "hello-service",
  "provides": {
    "capabilities": ["greet"]
  },
  "interfaces": {
    "http": {
      "port": 3100
    }
  }
}
```

### 2. Module Implementation

The `src/module.py` implements the business logic:

```python
class HelloModule(ModuleInterface):
    def get_capabilities(self):
        return ['greet']

    def invoke(self, capability, params):
        if capability == 'greet':
            name = params.get('name', 'World')
            return {'message': f"Hello, {name}!"}
```

### 3. Standalone Runner

The `src/standalone.py` starts an HTTP server:

```python
sdk = ModularitySDK("app.manifest.json")
sdk.run_standalone(port=3100)
```

That's it! The SDK handles:
- Loading the module
- Starting the HTTP server
- Exposing standard endpoints (`/_module/health`, `/_module/invoke`, etc.)
- Request/response handling
- Error handling

---

## Usage Examples

### Example 1: Basic Greeting

```bash
curl -X POST http://localhost:3100/_module/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "greet", "params": {}}'

# Response:
# {
#   "message": "Hello, World!",
#   "timestamp": "2025-10-16T10:30:00.123456"
# }
```

### Example 2: Custom Name

```bash
curl -X POST http://localhost:3100/_module/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "greet", "params": {"name": "Alice"}}'

# Response:
# {
#   "message": "Hello, Alice!",
#   "timestamp": "2025-10-16T10:30:00.123456"
# }
```

### Example 3: Custom Greeting

```bash
curl -X POST http://localhost:3100/_module/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "greet", "params": {"name": "Bob", "greeting": "Hi"}}'

# Response:
# {
#   "message": "Hi, Bob!",
#   "timestamp": "2025-10-16T10:30:00.123456"
# }
```

### Example 4: Use as Module (In-Process)

```python
from modularity_sdk import ModularitySDK

# Load hello service as in-process module
sdk = ModularitySDK("app.manifest.json")
hello = sdk.load_as_module({'default_greeting': 'Hi'})

# Use it directly (no network calls!)
result = hello.invoke('greet', {'name': 'Alice'})
print(result['message'])  # "Hi, Alice!"
```

---

## Configuration

### Via Config File

Edit `config.defaults.json`:

```json
{
  "default_greeting": "Howdy",
  "default_name": "Partner"
}
```

### Via Environment Variables

```bash
export MODULE_HOST=0.0.0.0  # Bind to all interfaces
export MODULE_PORT=3200     # Use different port
uv run python src/standalone.py
```

### Via Runtime Config

```python
hello = sdk.load_as_module({
    'default_greeting': 'Bonjour',
    'default_name': 'Monde'
})
```

---

## Extending This Example

### Add More Capabilities

1. Update the manifest:

```json
"provides": {
    "capabilities": ["greet", "farewell"]
}
```

2. Update the module:

```python
def get_capabilities(self):
    return ['greet', 'farewell']

def invoke(self, capability, params):
    if capability == 'greet':
        # ... existing code
    elif capability == 'farewell':
        name = params.get('name', self.name)
        return {
            'message': f"Goodbye, {name}!",
            'timestamp': self._get_timestamp()
        }
```

3. Test it:

```bash
curl -X POST http://localhost:3100/_module/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "farewell", "params": {"name": "Alice"}}'
```

---

## Testing

### Manual Testing

```bash
# Start the service
uv run python src/standalone.py

# In another terminal:

# 1. Health check
curl http://localhost:3100/_module/health

# 2. List capabilities
curl http://localhost:3100/_module/capabilities

# 3. Test greet with default
curl -X POST http://localhost:3100/_module/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "greet", "params": {}}'

# 4. Test greet with custom name
curl -X POST http://localhost:3100/_module/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "greet", "params": {"name": "Test"}}'

# 5. Test invalid capability (should error)
curl -X POST http://localhost:3100/_module/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "unknown", "params": {}}'
```

### Automated Testing

```bash
uv run python test_hello.py
```

Expected output:
```
✓ Capability 'greet' found
✓ Default greeting works: Hi, World!
✓ Custom name works: Hi, Alice!
✓ Custom greeting works: Hello, Bob!
✓ Timestamp present: 2025-10-16T10:30:00.123456
✓ Unknown capability properly rejected: Unknown capability: unknown

==================================================
✓ All tests passed!
==================================================
```

---

## Integration with Other Services

### Register with Registry

```bash
# Start registry first (from workspace root)
uv run --directory packages/registry python registry_service.py

# Start hello service (it auto-registers)
cd examples/01-hello-world/hello-service
uv run python src/standalone.py
```

### Discover and Use from Another Service

```python
from modularity_sdk import ModularitySDK

sdk = ModularitySDK()

# Find service by capability
result = sdk.invoke_capability('greet', {'name': 'Charlie'})
print(result['message'])  # "Hello, Charlie!"
```

---

## Troubleshooting

### Port Already in Use

If port 3100 is already taken:

```bash
export MODULE_PORT=3200
uv run python src/standalone.py
```

### Import Errors

Make sure you're in the monorepo root or have installed the SDK:

```bash
# Option 1: Run from monorepo with workspace dependencies
cd /path/to/modularity
uv sync  # Installs all workspace packages
cd examples/01-hello-world/hello-service
uv run python src/standalone.py

# Option 2: Install just the example
cd examples/01-hello-world/hello-service
uv sync  # Installs example dependencies
uv run python src/standalone.py
```

### Module Not Loading

Check that the paths in the manifest are correct:

```json
"interfaces": {
    "module": {
        "entry": "src/module.py",
        "class": "HelloModule"
    }
}
```

---

## Next Steps

Once you understand this minimal example:

1. **Study the Code** - Read through module.py to understand ModuleInterface
2. **Modify It** - Add a new capability like "farewell"
3. **Try More Examples** - Look at other examples in the examples/ directory
4. **Build Your Own** - Use this as a template for your own service

---

## Summary

This is the **absolute minimum** for an ecosystem-compatible service:

✅ ~50 lines of actual code
✅ One capability
✅ Works standalone or embedded
✅ 5 minutes to understand
✅ Perfect template for new services

**Core Files:**
- `app.manifest.json` - declares service (30 lines)
- `src/module.py` - implements logic (85 lines)
- `src/standalone.py` - runs as service (35 lines)
- `config.defaults.json` - configuration (4 lines)

**Total:** ~155 lines of code (excluding tests and docs)
**Core logic:** ~50 lines

Perfect for learning, perfect as a template! 🎉
