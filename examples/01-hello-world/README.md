# Example 01: Hello World

The simplest possible demonstration of the Modularity ecosystem.

## What's Included

- **hello-service/** - A minimal service that provides a "greet" capability

## Quick Start

```bash
# Install dependencies
cd hello-service
pip install -r requirements.txt

# Run the service
python src/standalone.py

# Test it (in another terminal)
curl -X POST http://localhost:3100/_module/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "greet", "params": {"name": "World"}}'
```

## Learning Objectives

This example teaches:
- ✅ How to create a valid manifest
- ✅ How to implement ModuleInterface
- ✅ How to run a service standalone
- ✅ How to invoke capabilities via HTTP
- ✅ How to load services as in-process modules

## File Structure

```
01-hello-world/
├── hello-service/           # The service implementation
│   ├── app.manifest.json   # Service declaration
│   ├── config.defaults.json # Configuration
│   ├── src/
│   │   ├── module.py       # ModuleInterface implementation
│   │   └── standalone.py   # Standalone entry point
│   ├── test_hello.py       # Basic tests
│   └── README.md           # Detailed documentation
└── README.md               # This file
```

## Time Investment

- **Reading:** 5 minutes
- **Running:** 2 minutes
- **Understanding:** 10 minutes
- **Modifying:** 5 minutes

## Next Steps

After completing this example:
1. Read the code in `hello-service/src/module.py`
2. Run the tests with `python test_hello.py`
3. Try modifying the service to add a new capability
4. Move on to more complex examples

---

See [hello-service/README.md](hello-service/README.md) for complete documentation.
