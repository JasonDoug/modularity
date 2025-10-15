# Modularity

A polymorphic service architecture platform enabling applications to run as standalone services, embedded modules, or distributed microservices without code changes.

## 🎯 Overview

Write your application logic once, deploy it any way you want:
- **Standalone** - Run as independent microservice
- **Embedded** - Load as in-process module
- **Distributed** - Service mesh with discovery

## 🏗️ Repository Structure

```
modularity/
├── packages/          # Core components
│   ├── sdk-python/
│   ├── sdk-javascript/
│   ├── sdk-go/
│   ├── sdk-rust/
│   ├── sdk-ruby/
│   ├── registry/
│   └── cli/
├── examples/          # Reference implementations
├── certification/     # Test harness
├── docs/             # Documentation
└── tools/            # Utilities
```

## 🚀 Quick Start

### Install Dependencies

```bash
make install
```

### Run Registry

```bash
cd packages/registry
python registry_service.py
```

### Run Example

```bash
cd examples/01-hello-world
python src/standalone.py
```

## 📚 Documentation

- [Architecture Overview](docs/architecture/overview.md)
- [Getting Started Guide](docs/guides/getting-started.md)
- [API Reference](docs/api-reference/README.md)

## 🧪 Testing

```bash
# Test all components
make test

# Test specific component
cd packages/sdk-python && pytest
```

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

[MIT License](LICENSE)

## 🔗 Links

- Documentation: [docs/](docs/)
- Examples: [examples/](examples/)
- Issues: [GitHub Issues](../../issues)
