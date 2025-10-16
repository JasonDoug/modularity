# Getting Started with Modularity

This comprehensive guide will take you from zero to running your first polymorphic service in under 30 minutes.

**What you'll learn:**
- ✅ How to install Modularity
- ✅ How to run the Registry service
- ✅ How to run the Hello World example
- ✅ How to test services with curl and the CLI
- ✅ How to create your own service

**Prerequisites:**
- Python 3.8 or higher
- pip (Python package manager)
- curl (for testing)
- Basic Python knowledge

---

## Step 1: Installation (5 minutes)

### Clone the Repository

```bash
git clone https://github.com/JasonDoug/modularity.git
cd modularity
```

### Install Python SDK

```bash
cd packages/sdk-python
pip install -r requirements.txt

# Optional: Install in development mode
pip install -e .
```

### Install Registry Service

```bash
cd ../registry
pip install -r requirements.txt
```

### Install CLI Tools

```bash
cd ../cli
pip install -e .

# Verify installation
modularity --version
```

### Install Example Dependencies

```bash
cd ../../examples/01-hello-world/hello-service
pip install -r requirements.txt
```

**✅ Checkpoint:** You should now have all dependencies installed.

---

## Step 2: Start the Registry (2 minutes)

The Registry service provides service discovery for distributed deployments.

### Start the Registry

```bash
# From project root
cd packages/registry
python registry_service.py
```

You should see:

```
==================================================
Ecosystem Registry Service
==================================================
Starting on http://127.0.0.1:5000
API Documentation:
  POST   /api/register          - Register a service
  DELETE /api/unregister/<id>   - Unregister a service
  GET    /api/services          - List all services
  GET    /api/services/<id>     - Get service details
  GET    /api/capabilities      - List all capabilities
  GET    /api/capabilities/<name> - Find service by capability
  POST   /api/heartbeat/<id>    - Send heartbeat
  POST   /api/discover          - Discover services by requirements
  GET    /api/stats             - Get registry statistics
  GET    /health                - Registry health check
==================================================
```

### Test the Registry

Open a new terminal and test the registry:

```bash
# Health check
curl http://localhost:5000/health

# Expected response:
# {
#   "status": "healthy",
#   "service": "ecosystem-registry",
#   "timestamp": "2025-10-16T10:30:00.123456"
# }

# List services (should be empty initially)
curl http://localhost:5000/api/services

# Expected response:
# {
#   "services": [],
#   "count": 0
# }
```

**✅ Checkpoint:** Registry is running on port 5000 and responding to requests.

---

## Step 3: Run Hello World Example (3 minutes)

Now let's run your first Modularity service!

### Start the Hello Service

Open a new terminal (keep Registry running):

```bash
cd examples/01-hello-world/hello-service
python src/standalone.py
```

You should see:

```
==================================================
Starting Hello Service...
==================================================
HelloModule initialized with greeting: 'Hello'
 * Running on http://127.0.0.1:3100
Try: curl http://localhost:3100/_module/invoke \
       -H 'Content-Type: application/json' \
       -d '{"capability": "greet", "params": {"name": "Alice"}}'

Health check: curl http://localhost:3100/_module/health
Capabilities: curl http://localhost:3100/_module/capabilities
==================================================
```

### Test the Service

Open a new terminal (keep both Registry and Hello Service running):

```bash
# 1. Health check
curl http://localhost:3100/_module/health

# Expected response:
# {
#   "status": "healthy",
#   "app": "Hello World Service",
#   "timestamp": "2025-10-16T10:30:00.123456"
# }

# 2. List capabilities
curl http://localhost:3100/_module/capabilities

# Expected response:
# {
#   "capabilities": ["greet"]
# }

# 3. Invoke the greet capability
curl -X POST http://localhost:3100/_module/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "greet", "params": {"name": "World"}}'

# Expected response:
# {
#   "message": "Hello, World!",
#   "timestamp": "2025-10-16T10:30:00.123456"
# }

# 4. Try with a different name
curl -X POST http://localhost:3100/_module/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "greet", "params": {"name": "Alice"}}'

# Expected response:
# {
#   "message": "Hello, Alice!",
#   "timestamp": "2025-10-16T10:30:00.123456"
# }

# 5. Try with a custom greeting
curl -X POST http://localhost:3100/_module/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "greet", "params": {"name": "Bob", "greeting": "Hi"}}'

# Expected response:
# {
#   "message": "Hi, Bob!",
#   "timestamp": "2025-10-16T10:30:00.123456"
# }
```

**✅ Checkpoint:** Hello service is running and responding to capability invocations!

---

## Step 4: Understanding the Architecture (5 minutes)

Let's understand what just happened.

### The Service Manifest

Every service has an `app.manifest.json` file that declares what it provides:

```json
{
  "id": "hello-service",
  "name": "Hello World Service",
  "version": "1.0.0",
  "type": "module",
  "runtime": "python",
  "provides": {
    "capabilities": ["greet"]
  },
  "interfaces": {
    "http": {
      "port": 3100,
      "basePath": "/api"
    },
    "module": {
      "entry": "src/module.py",
      "class": "HelloModule"
    }
  }
}
```

**Key parts:**
- `id`: Unique service identifier
- `provides.capabilities`: List of operations this service can perform
- `interfaces.http`: Configuration for standalone mode
- `interfaces.module`: Entry point for embedded mode

### The Module Implementation

The service implements `ModuleInterface`:

```python
from ecosystem_sdk import ModuleInterface

class HelloModule(ModuleInterface):
    def initialize(self, config):
        """Called when module loads"""
        self.greeting = config.get('default_greeting', 'Hello')
        return True

    def get_capabilities(self):
        """Return list of capabilities"""
        return ['greet']

    def invoke(self, capability, params):
        """Execute a capability"""
        if capability == 'greet':
            name = params.get('name', 'World')
            greeting = params.get('greeting', self.greeting)
            return {
                'message': f"{greeting}, {name}!",
                'timestamp': self._get_timestamp()
            }
        raise ValueError(f"Unknown capability: {capability}")

    def handle_event(self, event, data):
        """Handle events from other services"""
        pass

    def shutdown(self):
        """Cleanup before shutdown"""
        pass
```

**Key methods:**
- `initialize()`: Setup configuration
- `get_capabilities()`: Declare what the service can do
- `invoke()`: Execute capabilities
- `handle_event()`: Respond to events (optional)
- `shutdown()`: Cleanup (optional)

### The Standalone Runner

The `standalone.py` file starts an HTTP server:

```python
from ecosystem_sdk import EcosystemSDK

sdk = EcosystemSDK("app.manifest.json")
sdk.run_standalone(host='127.0.0.1', port=3100)
```

That's it! The SDK:
- Loads the manifest
- Instantiates your module
- Starts an HTTP server
- Exposes standard endpoints (`/_module/health`, `/_module/invoke`, etc.)
- Handles request/response serialization

**✅ Checkpoint:** You understand the basic architecture.

---

## Step 5: Try Different Deployment Modes (10 minutes)

The power of Modularity is that you can deploy the same code in multiple ways.

### Mode 1: Standalone Service (You Already Did This!)

```bash
python src/standalone.py
# Service runs on HTTP port 3100
```

### Mode 2: Embedded Module (No Network!)

Create a test file `test_embedded.py`:

```python
import sys
from pathlib import Path

# Add SDK to path
sdk_path = Path(__file__).parent.parent.parent.parent / "packages" / "sdk-python"
sys.path.insert(0, str(sdk_path))

from ecosystem_sdk import EcosystemSDK

# Load as in-process module
sdk = EcosystemSDK("app.manifest.json")
hello = sdk.load_as_module({'default_greeting': 'Hi'})

# Use directly - no network calls!
result = hello.invoke('greet', {'name': 'Alice'})
print(f"Result: {result}")
# Output: Result: {'message': 'Hi, Alice!', 'timestamp': '...'}

result = hello.invoke('greet', {'name': 'Bob', 'greeting': 'Hello'})
print(f"Result: {result}")
# Output: Result: {'message': 'Hello, Bob!', 'timestamp': '...'}
```

Run it:

```bash
cd examples/01-hello-world/hello-service
python test_embedded.py
```

**Key difference:** No HTTP server, no network calls, just direct function calls!

### Mode 3: Remote Invocation via Registry

The Registry can track which services provide which capabilities.

**Register the service manually:**

```bash
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "id": "hello-service-1",
    "name": "Hello World Service",
    "version": "1.0.0",
    "capabilities": ["greet"],
    "location": "http://localhost:3100",
    "mode": "http",
    "metadata": {"runtime": "python"}
  }'

# Expected response:
# {
#   "message": "Service registered successfully",
#   "service_id": "hello-service-1"
# }
```

**Query services by capability:**

```bash
# Find service providing "greet" capability
curl http://localhost:5000/api/capabilities/greet

# Expected response:
# {
#   "id": "hello-service-1",
#   "name": "Hello World Service",
#   "capabilities": ["greet"],
#   "location": "http://localhost:3100",
#   "status": "active",
#   ...
# }
```

**Discover services by requirements:**

```bash
curl -X POST http://localhost:5000/api/discover \
  -H "Content-Type: application/json" \
  -d '{
    "capabilities": ["greet"],
    "optional": []
  }'

# Expected response:
# {
#   "matches": [
#     {
#       "service": { ... hello-service details ... },
#       "match_score": 1,
#       "provides_required": ["greet"],
#       "provides_optional": []
#     }
#   ],
#   "count": 1
# }
```

**✅ Checkpoint:** You've deployed the same service in three different modes!

---

## Step 6: Run Automated Tests (2 minutes)

The Hello World example includes automated tests:

```bash
cd examples/01-hello-world/hello-service
python test_hello.py
```

Expected output:

```
HelloModule initialized with greeting: 'Hi'
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

**✅ Checkpoint:** All tests pass!

---

## Step 7: Create Your Own Service (10 minutes)

Now let's create your own service from scratch.

### 1. Create Directory Structure

```bash
cd examples
mkdir my-calculator
cd my-calculator
mkdir src
```

### 2. Create Manifest

Create `app.manifest.json`:

```json
{
  "id": "calculator-service",
  "name": "Calculator Service",
  "version": "1.0.0",
  "type": "module",
  "runtime": "python",
  "modes": {
    "standalone": true,
    "embeddable": true,
    "service": true
  },
  "provides": {
    "capabilities": ["add", "subtract", "multiply", "divide"],
    "endpoints": [],
    "events": [],
    "commands": []
  },
  "requires": {
    "capabilities": [],
    "optional": []
  },
  "interfaces": {
    "http": {
      "port": 3200,
      "basePath": "/api"
    },
    "module": {
      "entry": "src/module.py",
      "class": "CalculatorModule"
    }
  },
  "config": {
    "defaults": "config.defaults.json"
  }
}
```

### 3. Create Configuration

Create `config.defaults.json`:

```json
{
  "precision": 2
}
```

### 4. Create Dependencies

Create `requirements.txt`:

```
Flask>=3.0.0
flask-cors>=4.0.0
requests>=2.31.0
```

### 5. Implement the Module

Create `src/module.py`:

```python
"""
Calculator Service - Module Implementation
"""

import sys
import os
from pathlib import Path

# Add SDK to path
sdk_path = Path(__file__).parent.parent.parent.parent / "packages" / "sdk-python"
sys.path.insert(0, str(sdk_path))

from ecosystem_sdk import ModuleInterface


class CalculatorModule(ModuleInterface):
    """
    Calculator service providing basic math operations.
    """

    def initialize(self, config):
        """Initialize with configuration"""
        self.config = config
        self.precision = config.get('precision', 2)
        print(f"CalculatorModule initialized with precision: {self.precision}")
        return True

    def get_capabilities(self):
        """Return available capabilities"""
        return ['add', 'subtract', 'multiply', 'divide']

    def invoke(self, capability, params):
        """Execute a capability"""
        # Get operands
        a = params.get('a')
        b = params.get('b')

        if a is None or b is None:
            raise ValueError("Parameters 'a' and 'b' are required")

        # Convert to float
        try:
            a = float(a)
            b = float(b)
        except (TypeError, ValueError):
            raise ValueError("Parameters must be numbers")

        # Perform operation
        if capability == 'add':
            result = a + b
        elif capability == 'subtract':
            result = a - b
        elif capability == 'multiply':
            result = a * b
        elif capability == 'divide':
            if b == 0:
                raise ValueError("Cannot divide by zero")
            result = a / b
        else:
            raise ValueError(f"Unknown capability: {capability}")

        # Round to precision
        result = round(result, self.precision)

        return {
            'result': result,
            'operation': capability,
            'operands': {'a': a, 'b': b}
        }

    def handle_event(self, event, data):
        """Handle events"""
        print(f"Received event: {event} with data: {data}")

    def shutdown(self):
        """Cleanup"""
        print("CalculatorModule shutting down")
```

### 6. Create Standalone Runner

Create `src/standalone.py`:

```python
"""
Calculator Service - Standalone Mode
"""

import sys
import os
from pathlib import Path

# Add SDK to path
sdk_path = Path(__file__).parent.parent.parent.parent / "packages" / "sdk-python"
sys.path.insert(0, str(sdk_path))

from ecosystem_sdk import EcosystemSDK


if __name__ == "__main__":
    manifest_path = Path(__file__).parent.parent / "app.manifest.json"
    sdk = EcosystemSDK(str(manifest_path))

    print("=" * 50)
    print("Starting Calculator Service...")
    print("=" * 50)
    print("Try: curl http://localhost:3200/_module/invoke \\")
    print("       -H 'Content-Type: application/json' \\")
    print("       -d '{\"capability\": \"add\", \"params\": {\"a\": 5, \"b\": 3}}'")
    print("=" * 50)
    print()

    host = os.getenv('MODULE_HOST', '127.0.0.1')
    port = int(os.getenv('MODULE_PORT', '3200'))

    sdk.run_standalone(host=host, port=port)
```

### 7. Test Your Service

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python src/standalone.py
```

In another terminal:

```bash
# Add two numbers
curl -X POST http://localhost:3200/_module/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "add", "params": {"a": 5, "b": 3}}'

# Expected: {"result": 8.0, "operation": "add", "operands": {"a": 5.0, "b": 3.0}}

# Subtract
curl -X POST http://localhost:3200/_module/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "subtract", "params": {"a": 10, "b": 4}}'

# Expected: {"result": 6.0, "operation": "subtract", "operands": {"a": 10.0, "b": 4.0}}

# Multiply
curl -X POST http://localhost:3200/_module/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "multiply", "params": {"a": 7, "b": 6}}'

# Expected: {"result": 42.0, "operation": "multiply", "operands": {"a": 7.0, "b": 6.0}}

# Divide
curl -X POST http://localhost:3200/_module/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "divide", "params": {"a": 15, "b": 3}}'

# Expected: {"result": 5.0, "operation": "divide", "operands": {"a": 15.0, "b": 3.0}}
```

**✅ Checkpoint:** You've created your own Modularity service!

---

## Common Issues and Troubleshooting

### Port Already in Use

If you see "Address already in use":

```bash
# Change port via environment variable
export MODULE_PORT=3200
python src/standalone.py
```

### Import Errors

If you see "ModuleNotFoundError: No module named 'ecosystem_sdk'":

```bash
# Make sure you're running from the correct directory
cd examples/01-hello-world/hello-service
python src/standalone.py

# Or install SDK in development mode
cd packages/sdk-python
pip install -e .
```

### Registry Not Running

If service discovery doesn't work:

```bash
# Make sure registry is running
cd packages/registry
python registry_service.py

# Test it
curl http://localhost:5000/health
```

---

## Next Steps

Congratulations! You've completed the getting started guide. Here's what to explore next:

### 1. Learn More About the Architecture

Read the [Architecture Overview](../architecture/overview.md) to understand how Modularity works under the hood.

### 2. Explore the SDK

Check out the [Python SDK Documentation](../../packages/sdk-python/README.md) for advanced usage patterns.

### 3. Use the CLI

Learn about the [CLI tools](../../packages/cli/README.md) for managing services.

### 4. Study More Examples

Look at additional examples in the `examples/` directory (coming soon):
- Weather service with external API calls
- Multi-service orchestration
- Event-driven patterns

### 5. Build Something Real

Take your own application and make it Modularity-compatible:
1. Create a manifest
2. Implement ModuleInterface
3. Add a standalone runner
4. Test in all three modes

---

## Summary

In this guide, you learned:

✅ How to install Modularity and all dependencies
✅ How to start the Registry service
✅ How to run the Hello World example
✅ How to test services with curl
✅ How the architecture works (manifest, module, standalone)
✅ How to deploy services in three different modes
✅ How to run automated tests
✅ How to create your own service from scratch

**You're now ready to build polymorphic applications with Modularity!**

For questions or issues, please check:
- [Architecture Documentation](../architecture/overview.md)
- [SDK Documentation](../../packages/sdk-python/README.md)
- [GitHub Issues](https://github.com/JasonDoug/modularity/issues)
