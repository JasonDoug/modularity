# Ecosystem CLI

Command-line interface for managing the ecosystem.

## Installation

```bash
pip install -e .
```

## Usage

```bash
# List services
ecosystem list

# Show status
ecosystem status

# Create new service
ecosystem init my-service "My Service" --runtime python

# Run service
ecosystem run
```

## Development

```bash
pip install -e .[dev]
pytest
```
