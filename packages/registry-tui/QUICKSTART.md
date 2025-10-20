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

## Step 2: (Optional) Populate Test Data

To see the TUI in action with sample data:

```bash
cd packages/registry-tui
uv run python populate_test_data.py
```

This will create:
- 5 active services (Auth, Database, API Gateway, Cache, Email)
- Multiple capability connections between services
- Sample metrics and statistics

## Step 3: Launch the TUI

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
- Try populating test data with the script in Step 2

### SSE connection issues
- Check that `/api/events` endpoint is accessible
- Verify no firewall is blocking the connection

## Advanced Usage

### Development Mode
For TUI development with hot reloading:

```bash
uv run textual run --dev registry_tui/tui.py
```

### Textual Console
Debug the TUI in a separate terminal:

```bash
textual console
# In another terminal:
uv run python -m registry_tui.tui
```

## Next Steps

- Register your own services using the Modularity SDK
- Monitor service interactions in real-time
- Use connection metrics to optimize service performance
- Export registry data via REST API for custom dashboards
