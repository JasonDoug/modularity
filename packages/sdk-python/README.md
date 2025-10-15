# Ecosystem SDK - Python

Python implementation of the Ecosystem SDK.

## Installation

```bash
pip install -e .
```

## Usage

```python
from ecosystem_sdk import EcosystemSDK, ModuleInterface

# Load SDK
sdk = EcosystemSDK("app.manifest.json")

# Run standalone
sdk.run_standalone()

# Or load as module
module = sdk.load_as_module(config)
```

## Development

```bash
# Install dev dependencies
pip install -e .[dev]

# Run tests
pytest

# Run linting
flake8
```
