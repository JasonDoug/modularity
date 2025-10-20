# Modularity Registry TUI - Quick Start Guide

This guide will help you get the Registry TUI dashboard up and running in minutes.

## Prerequisites

- Python >= 3.9
- Modularity Registry running (the TUI connects to it)
- `uv` package manager (already set up in this workspace)

## Step 1: Start the Registry

From the workspace root:

```bash
cd packages/registry
uv run python registry_service.py
```

The registry will start on `http://localhost:5000` by default.

## Step 2: Launch the TUI

```bash
cd packages/registry-tui
uv run python -m registry_tui.tui
```

Or specify a custom registry URL:

```bash
uv run python -m registry_tui.tui --registry-url http://localhost:5000
```

## What You'll See

The TUI displays:

### Left Panel - Service List
- All registered services with status indicators
  - `●` (green) = Active service
  - `○` (red) = Inactive service
- Service name and capability count
- Use arrow keys (↑/↓) or `j`/`k` to navigate

### Right Panel - Service Details
When you select a service, you'll see:
- **Basic Info**: ID, version, location, status
- **Capabilities**: All capabilities the service provides
- **Consuming From**: Services this service calls
  - Request counts, success rates, average latency
- **Providing To**: Services calling this service
  - Request counts, success rates, average latency
- **Metadata**: Custom service metadata (runtime, framework, etc.)

### Header
Shows registry-wide statistics:
- Total services count
- Active/inactive breakdown
- Total capabilities available

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `↑` / `k` | Move up in service list |
| `↓` / `j` | Move down in service list |
| `r` | Refresh all data |
| `q` | Quit the application |

## Real-Time Updates

The TUI automatically updates when:
- New services register
- Services unregister
- Service status changes
- Capabilities are invoked between services

All updates are delivered via Server-Sent Events (SSE) from the registry.

## Example Workflow

1. **Monitor Services**: Launch the TUI to see all registered services
2. **Inspect Details**: Select a service to view its capabilities and connections
3. **Watch Live**: Leave it running to see real-time updates as services interact
4. **Refresh**: Press `r` to manually refresh if needed

## Troubleshooting

### "Connection refused" error
- Ensure the registry is running on the expected URL
- Check the registry URL with `--registry-url` flag

### No services shown
- Verify services are registered: `curl http://localhost:5000/api/services`
- Make sure you've registered some services first (see "Registering Services" section below)

### SSE connection issues
- Check that `/api/events` endpoint is accessible
- Verify no firewall is blocking the connection

## Registering Services

To see services in the TUI, you need to register them with the Registry. Here are a few ways:

### Method 1: Using curl (for testing)

```bash
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "id": "my-service",
    "name": "My Test Service",
    "version": "1.0.0",
    "capabilities": ["test.capability"],
    "location": "http://localhost:3001",
    "mode": "http"
  }'
```

### Method 2: Using the Modularity SDK

Create a service using the SDK (see SDK documentation for full details):

```python
from modularity_sdk import ModularitySDK

sdk = ModularitySDK()
sdk.start(host="0.0.0.0", port=3001)
```

The SDK will automatically register your service with the Registry.

### Method 3: Check existing examples

Look at the examples in the `examples/` directory for working service implementations.

## Advanced Usage

### Development Mode
For TUI development with hot reloading (from the registry-tui directory):

```bash
cd packages/registry-tui
uv run textual run --dev registry_tui/tui.py
```

### Textual Console
Debug the TUI in a separate terminal:

```bash
# Terminal 1: Start the console
textual console

# Terminal 2: Run the TUI
cd packages/registry-tui
uv run python -m registry_tui.tui
```

## Next Steps

- Register your own services using the Modularity SDK
- Monitor service interactions in real-time
- Use connection metrics to optimize service performance
- Export registry data via REST API for custom dashboards
