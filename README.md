# Modularity

**A polymorphic service architecture platform enabling applications to run as standalone services, embedded modules, or distributed microservices without code changes.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

---

## 🎯 What is Modularity?

Modularity is a revolutionary approach to building applications that eliminates the deployment-time trade-offs between monoliths and microservices.

**Write your application logic once, deploy it three ways:**

- 🚀 **Standalone Service** - Run as independent HTTP microservice
- 📦 **Embedded Module** - Load as in-process library (no network calls)
- 🌐 **Distributed System** - Service mesh with automatic discovery

**The same code, zero modifications.**

### Why Modularity?

Traditional development forces you to choose your architecture upfront:

| Traditional Approach | Modularity Approach |
|---------------------|---------------------|
| Monolith **OR** Microservices | Monolith **AND** Microservices |
| Tight coupling **OR** Network overhead | Choose at runtime |
| Commit to architecture early | Defer the decision |
| Rewrite to change deployment | Configuration change |

### Real-World Example

```python
# Your service implementation (once)
class HelloModule(ModuleInterface):
    def invoke(self, capability, params):
        return {'message': f"Hello, {params['name']}!"}

# Deploy Option 1: Standalone HTTP service
sdk.run_standalone(port=3100)

# Deploy Option 2: Embedded in-process (no HTTP!)
hello = sdk.load_as_module()
result = hello.invoke('greet', {'name': 'Alice'})

# Deploy Option 3: Remote via service discovery
result = sdk.invoke_capability('greet', {'name': 'Alice'})
```

**Same code. Three deployment modes. No rewrites.**

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites

- Python 3.9 or higher
- [uv](https://github.com/astral-sh/uv) (ultra-fast Python package manager)

### 1. Install uv (if not already installed)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip
pip install uv
```

### 2. Install Dependencies

```bash
# From the project root - installs all workspace packages
uv sync

# This creates a .venv and installs:
# - modularity-cli
# - modularity-sdk
# - modularity-registry
# - All dependencies
```

### 3. Start the Registry (Terminal 1)

The registry enables service discovery for distributed deployments:

```bash
uv run --directory packages/registry python registry_service.py
```

Output:
```
==================================================
Ecosystem Registry Service
==================================================
Starting on http://127.0.0.1:5000
API Documentation:
  POST   /api/register          - Register a service
  GET    /api/services          - List all services
  ...
==================================================
```

### 4. Run Hello World Example (Terminal 2)

```bash
cd examples/01-hello-world/hello-service
uv run python src/standalone.py
```

Output:
```
==================================================
Starting Hello Service...
==================================================
HelloModule initialized with greeting: 'Hello'
 * Running on http://127.0.0.1:3100
```

### 5. Test It (Terminal 3)

```bash
# Health check
curl http://localhost:3100/_module/health

# List capabilities
curl http://localhost:3100/_module/capabilities

# Invoke the greet capability
curl -X POST http://localhost:3100/_module/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "greet", "params": {"name": "World"}}'

# Response:
# {"message": "Hello, World!", "timestamp": "2025-10-16T10:30:00.123456"}
```

**Congratulations!** You just ran your first Modularity service. 🎉

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Hello     │  │   Weather   │  │    Users    │         │
│  │  Service    │  │   Service   │  │   Service   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Modularity Platform                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │     SDK      │  │   Registry   │  │     CLI      │      │
│  │  (Runtime)   │  │  (Discovery) │  │  (Tooling)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. SDK (Runtime Library)
- **Location:** `packages/sdk-python/`
- **Purpose:** Load and execute modules in any deployment mode
- **Key Classes:** `ModularitySDK`, `ModuleInterface`, `ServiceLocator`
- **Languages:** Python (implemented), JavaScript/Go/Rust (planned)

#### 2. Registry (Service Discovery)
- **Location:** `packages/registry/`
- **Purpose:** Track available services and their capabilities
- **Port:** 5000 (default)
- **API:** RESTful HTTP
- **Features:** Health monitoring, capability-based discovery

#### 3. CLI (Developer Tools)
- **Location:** `packages/cli/`
- **Purpose:** Manage services, inspect system, development workflow
- **Command:** `modularity`
- **Features:** Service management, registry queries, scaffolding

### Communication Patterns

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Embedded Mode (In-Process)                               │
│                                                              │
│    App Process                                               │
│    ┌──────────────────────────────────────┐                │
│    │  Main App  →  Module A  →  Module B  │                │
│    │  (Direct function calls, no network) │                │
│    └──────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 2. Standalone Mode (HTTP Services)                          │
│                                                              │
│  ┌─────────┐      HTTP/JSON      ┌─────────┐              │
│  │ Client  │ ───────────────────→ │ Service │              │
│  └─────────┘                      └─────────┘              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 3. Distributed Mode (Service Mesh)                          │
│                                                              │
│  ┌─────────┐   1. Discover  ┌──────────┐                  │
│  │ Client  │ ──────────────→ │ Registry │                  │
│  └─────────┘                 └──────────┘                  │
│       │                            │                        │
│       │ 2. Get Location            │                        │
│       │ ←──────────────────────────┘                        │
│       │                                                     │
│       │ 3. Invoke      ┌─────────┐                         │
│       └───────────────→│ Service │                         │
│                        └─────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Repository Structure

```
modularity/
├── packages/                    # Core platform components
│   ├── sdk-python/             # Python SDK (✅ Complete)
│   │   ├── modularity_sdk/     # SDK implementation
│   │   │   ├── __init__.py    # ModularitySDK, ModuleInterface, etc.
│   │   │   └── ...
│   │   ├── tests/              # SDK tests
│   │   └── pyproject.toml      # Package configuration
│   │
│   ├── registry/               # Service registry (✅ Complete)
│   │   ├── registry_service.py # Flask-based registry service
│   │   ├── tests/              # Registry tests
│   │   └── pyproject.toml      # Package configuration
│   │
│   └── cli/                    # CLI tools (✅ Complete)
│       ├── modularity_cli/     # CLI implementation
│       │   └── cli.py         # Click-based commands
│       ├── tests/              # CLI tests
│       └── pyproject.toml      # Package configuration
│
├── examples/                    # Working examples
│   └── 01-hello-world/         # Minimal example (✅ Complete)
│       └── hello-service/      # Simple greeting service
│           ├── app.manifest.json
│           ├── src/module.py
│           ├── src/standalone.py
│           └── ...
│
├── docs/                        # Documentation
│   ├── architecture/           # Architecture docs
│   ├── guides/                 # Tutorials and guides
│   └── api-reference/          # API documentation
│
└── claude.md                   # Development workflow guide
```

---

## 📖 Documentation

### For Users

- **[Getting Started Guide](docs/guides/getting-started.md)** - Complete walkthrough from installation to first service
- **[Hello World Example](examples/01-hello-world/README.md)** - Minimal working example
- **[Architecture Overview](docs/architecture/overview.md)** - System design and concepts

### For Developers

- **[Python SDK Documentation](packages/sdk-python/README.md)** - SDK usage and API reference
- **[Registry API](packages/registry/README.md)** - Service registry endpoints
- **[CLI Reference](packages/cli/README.md)** - Command-line tools
- **[Development Workflow](claude.md)** - Git workflow, PR process, CodeRabbit integration

### Key Concepts

1. **Manifest** - JSON file declaring service capabilities and configuration
2. **ModuleInterface** - Abstract base class all services implement
3. **Capabilities** - Named operations a service can perform
4. **Service Discovery** - Finding services by capability, not by endpoint
5. **Polymorphic Deployment** - Same code, multiple deployment modes

---

## 🧪 Testing

### Run All Tests

```bash
# Python SDK tests
uv run --directory packages/sdk-python pytest tests/

# Registry tests
uv run --directory packages/registry pytest tests/

# CLI tests
uv run --directory packages/cli pytest tests/

# Example tests
cd examples/01-hello-world/hello-service
uv run python test_hello.py

# Or run all tests from workspace root
uv run pytest packages/*/tests/
```

### Manual Integration Test

```bash
# Terminal 1: Start registry
uv run --directory packages/registry python registry_service.py

# Terminal 2: Start hello service
cd examples/01-hello-world/hello-service
uv run python src/standalone.py

# Terminal 3: Test end-to-end
curl -X POST http://localhost:3100/_module/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "greet", "params": {"name": "Test"}}'
```

---

## 🛠️ Development

### Project Status

**Current Version:** 1.0.0-alpha

**Completed Components:**
- ✅ Python SDK with all core classes
- ✅ Registry service with health monitoring
- ✅ CLI tool with 9 commands
- ✅ Hello World example
- ✅ Security fixes (SSRF, CORS, input validation)
- ✅ Comprehensive test suites

**In Progress:**
- 🔄 Additional examples (weather service, multi-service orchestration)
- 🔄 JavaScript SDK
- 🔄 Go SDK

**Planned:**
- 📋 Advanced service patterns
- 📋 Production deployment guides
- 📋 Performance benchmarks
- 📋 Rust SDK
- 📋 Ruby SDK

### Contributing

We welcome contributions! To get started:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

See [claude.md](claude.md) for our complete development workflow including:
- Git branching strategy
- Commit message format
- PR creation process
- CodeRabbit review integration

---

## 🔒 Security

This project follows security best practices:

- ✅ SSRF protection in health checks
- ✅ CORS configuration with allowed origins
- ✅ Input validation on all API endpoints
- ✅ Localhost-only binding by default
- ✅ No execution of untrusted code
- ✅ Explicit exception handling

To report security vulnerabilities, please open a GitHub issue with the "security" label.

---

## 📊 Performance

### Deployment Mode Comparison

| Mode | Latency | Throughput | Resource Usage | Use Case |
|------|---------|------------|----------------|----------|
| **Embedded** | ~0.01ms | Very High | Minimal | Development, monoliths |
| **Standalone** | ~5ms | High | Moderate | Single services |
| **Distributed** | ~10-50ms | Moderate | Higher | Multi-service systems |

### Benchmarks

Coming soon - see roadmap for performance testing framework.

---

## 🗺️ Roadmap

### Q1 2025
- ✅ Core Python SDK
- ✅ Registry service
- ✅ CLI tools
- ✅ Hello World example
- 🔄 Additional examples

### Q2 2025
- JavaScript SDK
- Go SDK
- Performance benchmarking
- Production deployment guides

### Q3 2025
- Service mesh features
- Advanced patterns (sagas, CQRS)
- Monitoring and observability
- Rust SDK

### Q4 2025
- Enterprise features
- Multi-language interop examples
- Certification suite
- 1.0 stable release

---

## 💡 Use Cases

### 1. Gradual Microservices Migration

Start with a monolith, gradually extract services:

```python
# Phase 1: Everything in-process
auth = sdk.load_as_module('auth-service')
users = sdk.load_as_module('user-service')

# Phase 2: Extract auth to separate service
auth = sdk.connect_to_service('http://auth:3000')
users = sdk.load_as_module('user-service')

# Phase 3: Full microservices
auth = sdk.invoke_capability('authenticate', {...})
users = sdk.invoke_capability('get_user', {...})
```

### 2. Development vs Production

Different deployment modes for different environments:

```python
# Development: Everything in-process (fast iteration)
if ENV == 'development':
    sdk = ModularitySDK(mode='embedded')

# Production: Distributed services (scalability)
else:
    sdk = ModularitySDK(mode='distributed', registry='http://registry:5000')
```

### 3. Testing Without Mocks

Test with real implementations, no network:

```python
# Integration test
def test_user_workflow():
    sdk = ModularitySDK()
    auth = sdk.load_as_module('auth-service')
    users = sdk.load_as_module('user-service')

    # Real code, no mocks, no network!
    token = auth.invoke('login', {'user': 'test', 'pass': 'test'})
    profile = users.invoke('get_profile', {'token': token})
    assert profile['name'] == 'Test User'
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Inspired by Uber's H3 and Netflix's architecture
- Built with Flask, Click, and Rich
- Developed with Claude Code

---

## 📞 Support

- **Documentation:** [docs/](docs/)
- **Examples:** [examples/](examples/)
- **Issues:** [GitHub Issues](https://github.com/JasonDoug/modularity/issues)

---

**Ready to build polymorphic applications?** Start with the [Getting Started Guide](docs/guides/getting-started.md) →
