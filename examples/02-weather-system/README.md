# Weather System Example

Demonstrates service-to-service communication and service discovery patterns.

## Overview

This example will showcase:
- Multiple services working together
- Service discovery via registry
- Inter-service communication
- Real-world API integration patterns

## Services

- **weather-service** - Fetches and provides weather data
- **location-service** - Geocoding and location resolution
- **dashboard** - Aggregates data from both services

## Setup

This example is **coming soon** and will use the modern uv workflow:

```bash
# When implemented, setup will be:
cd examples/02-weather-system
uv sync                      # Install all services
uv run python setup.py       # Configure services
```

## Quick Start (Planned)

```bash
# Terminal 1: Start registry
uv run --directory ../../packages/registry python registry_service.py

# Terminal 2: Start weather service
cd weather-service
uv run python src/standalone.py

# Terminal 3: Start location service
cd location-service
uv run python src/standalone.py

# Terminal 4: Start dashboard
cd dashboard
uv run python src/standalone.py
```

## Implementation Status

⏳ **Planned** - This example is not yet implemented but will follow the uv workspace pattern when created.

## Interested in Contributing?

This would be a great example to implement! See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.
