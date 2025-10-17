# Modularity CLI

Command-line interface for managing the Modularity ecosystem.

## Installation

### From Workspace Root

```bash
# Install all workspace packages including CLI
uv sync
```

### Standalone Installation

```bash
cd packages/cli
uv pip install -e .
```

## Usage

```bash
# List services
modularity list

# Show status
modularity status

# Find services by capability
modularity find <capability-name>

# Create new service
modularity init my-service "My Service" --runtime python

# Run service
modularity run

# Show service info
modularity info <service-id>

# Validate manifest
modularity validate app.manifest.json

# List capabilities
modularity capabilities

# Unregister service
modularity unregister <service-id>
```

## Running via uv

```bash
# From workspace root
uv run --directory packages/cli modularity --help

# Or activate the workspace venv
source .venv/bin/activate
modularity --help
```

## Development

```bash
# Install with dev dependencies
cd packages/cli
uv sync

# Run tests
uv run pytest

# Run linter
uv run ruff check .
```

## Package Details

- **Package Name:** `modularity-cli`
- **Entry Point:** `modularity` command
- **Main Module:** `modularity_cli.cli`
- **Dependencies:** click, rich, requests, pyyaml
