# Modularity Registry TUI

A real-time terminal user interface (TUI) dashboard for monitoring the Modularity Registry, inspired by `htop`.

## Features

- **Real-time service monitoring**: View all registered services with live status updates
- **Service details**: See comprehensive information about each service including:
  - Service metadata (name, version, location, status)
  - Capabilities provided
  - Connection metrics (consuming from/providing to other services)
  - Success rates and latency statistics
- **Live updates**: Automatic refresh via Server-Sent Events (SSE)
- **Interactive navigation**: Keyboard shortcuts for easy navigation

## Installation

From the workspace root:

```bash
uv sync
```

## Usage

**Important**: The Registry must be running before you start the TUI.

### Start the Registry

From the workspace root:

```bash
cd packages/registry
uv run python registry_service.py
```

The registry will start on `http://localhost:5000` by default.

### Start the TUI

From the workspace root:

```bash
cd packages/registry-tui
uv run python -m registry_tui.tui
```

Or specify a custom registry URL:

```bash
uv run python -m registry_tui.tui --registry-url http://localhost:5000
```

## Keyboard Shortcuts

- `↑/k` or `↓/j` - Navigate through services
- `r` - Refresh all data
- `q` - Quit

## Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ Modularity Registry | Services: 5 (●3 ○2) | Capabilities: 12      │
├──────────────────────────┬──────────────────────────────────────────┤
│ Services                 │ Service Details                          │
│                          │                                          │
│ ● Service A [3 caps]     │ My Service A                            │
│ ● Service B [2 caps]     │ ID: service-a                           │
│ ○ Service C [1 cap]      │ Status: ACTIVE                          │
│                          │                                          │
│                          │ Capabilities:                            │
│                          │   • capability1                          │
│                          │   • capability2                          │
│                          │                                          │
│                          │ Consuming From:                          │
│                          │   → Service B (capability-x)             │
│                          │     Requests: 150 | Success: 98.7%       │
│                          │     Latency: 42.5ms                      │
└──────────────────────────┴──────────────────────────────────────────┘
```

## Requirements

- Python >= 3.9
- Modularity Registry running (default: http://localhost:5000)
- Dependencies: textual, requests, sseclient-py

## Development

Run with development mode for hot reloading (from the registry-tui directory):

```bash
cd packages/registry-tui
uv run textual run --dev registry_tui/tui.py
```

Or use the Textual console for debugging:

```bash
# Terminal 1: Start the console
textual console

# Terminal 2: Run the TUI
cd packages/registry-tui
uv run python -m registry_tui.tui
```

## Architecture

The TUI consists of several key components:

- **ServiceListWidget**: Left panel displaying all services with status indicators
- **ServiceDetailWidget**: Right panel showing detailed information and connections
- **StatsHeader**: Top bar with registry-wide statistics
- **SSE Listener**: Background thread receiving real-time events from the registry

Events are automatically handled to update the UI when:
- Services register/unregister
- Service status changes
- Capabilities are invoked
