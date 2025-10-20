"""
Modularity Registry TUI - Real-time dashboard for service registry

An htop-like interface showing:
- List of registered services (left panel)
- Service details and connections (right panel)
- Real-time updates via SSE
"""

import json
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin

import requests
from sseclient import SSEClient
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, DataTable, Label, ListItem, ListView
from textual.reactive import reactive
from textual import work


class ServiceListItem(ListItem):
    """A list item representing a service"""

    def __init__(self, service_id: str, service_data: Dict[str, Any]):
        self.service_id = service_id
        self.service_data = service_data

        # Format label text
        status = service_data.get('status', 'unknown')
        name = service_data.get('name', self.service_id)
        status_icon = "●" if status == "active" else "○"
        status_color = "green" if status == "active" else "red"
        cap_count = len(service_data.get('capabilities', []))
        label_text = f"[{status_color}]{status_icon}[/] {name} [{cap_count} cap{'s' if cap_count != 1 else ''}]"

        # Initialize ListItem with a Label child
        super().__init__(Label(label_text))
        self._label = self.children[0]

    def update_data(self, service_data: Dict[str, Any]):
        """Update the service data and label"""
        self.service_data = service_data
        status = service_data.get('status', 'unknown')
        name = service_data.get('name', self.service_id)

        # Status indicator
        status_icon = "●" if status == "active" else "○"
        status_color = "green" if status == "active" else "red"

        # Format the label
        label_text = f"[{status_color}]{status_icon}[/] {name}"

        # Add capability count
        cap_count = len(service_data.get('capabilities', []))
        label_text += f" [{cap_count} cap{'s' if cap_count != 1 else ''}]"

        # Update the label widget
        self._label.update(label_text)


class ServiceListWidget(Vertical):
    """Left panel showing list of services"""

    def __init__(self):
        super().__init__()
        self.services: Dict[str, Dict[str, Any]] = {}

    def compose(self) -> ComposeResult:
        yield Static("Services", classes="panel-title")
        yield ListView(id="service-list")

    def update_services(self, services: List[Dict[str, Any]]):
        """Update the service list"""
        list_view = self.query_one("#service-list", ListView)

        # Update services dict
        self.services = {s['id']: s for s in services}

        # Clear and rebuild list
        list_view.clear()
        for service in sorted(services, key=lambda s: s.get('name', s['id'])):
            item = ServiceListItem(service['id'], service)
            list_view.append(item)

    def update_service(self, service_id: str, service_data: Dict[str, Any]):
        """Update a single service in the list"""
        self.services[service_id] = service_data
        list_view = self.query_one("#service-list", ListView)

        # Find and update the item
        for item in list_view.children:
            if isinstance(item, ServiceListItem) and item.service_id == service_id:
                item.update_data(service_data)
                return

        # If not found, add it
        new_item = ServiceListItem(service_id, service_data)
        list_view.append(new_item)

    def remove_service(self, service_id: str):
        """Remove a service from the list"""
        if service_id in self.services:
            del self.services[service_id]

        list_view = self.query_one("#service-list", ListView)
        for item in list_view.children:
            if isinstance(item, ServiceListItem) and item.service_id == service_id:
                item.remove()
                return


class ServiceDetailWidget(ScrollableContainer):
    """Right panel showing detailed service information"""

    selected_service_id: reactive[Optional[str]] = reactive(None)

    def __init__(self):
        super().__init__()
        self.service_data: Optional[Dict[str, Any]] = None
        self.connections_data: Optional[Dict[str, Any]] = None

    def compose(self) -> ComposeResult:
        yield Static("Service Details", classes="panel-title")
        yield Static("Select a service from the list", id="detail-content")

    def watch_selected_service_id(self, service_id: Optional[str]):
        """React to service selection changes"""
        if service_id:
            self.load_service_details(service_id)
        else:
            self.clear_details()

    def clear_details(self):
        """Clear the detail panel"""
        content = self.query_one("#detail-content", Static)
        content.update("Select a service from the list")
        self.service_data = None
        self.connections_data = None

    @work(thread=True)
    def load_service_details(self, service_id: str):
        """Load service details and connections from the registry"""
        try:
            # This will be set by the main app
            registry_url = self.app.registry_url

            # Get service details
            resp = requests.get(f"{registry_url}/api/services/{service_id}", timeout=5)
            if resp.status_code == 200:
                self.service_data = resp.json()

            # Get connections
            resp = requests.get(f"{registry_url}/api/connections/{service_id}", timeout=5)
            if resp.status_code == 200:
                self.connections_data = resp.json()

            # Update UI
            self.call_from_thread(self.render_details)
        except Exception as e:
            self.call_from_thread(self.show_error, str(e))

    def show_error(self, error: str):
        """Show error message"""
        content = self.query_one("#detail-content", Static)
        content.update(f"[red]Error: {error}[/red]")

    def render_details(self):
        """Render service details in the panel"""
        if not self.service_data:
            return

        lines = []

        # Service info
        lines.append(f"[bold cyan]{self.service_data['name']}[/bold cyan]")
        lines.append(f"ID: {self.service_data['id']}")
        lines.append(f"Version: {self.service_data.get('version', 'N/A')}")
        lines.append(f"Location: {self.service_data['location']}")
        lines.append(f"Mode: {self.service_data['mode']}")

        # Status
        status = self.service_data.get('status', 'unknown')
        status_color = "green" if status == "active" else "red"
        lines.append(f"Status: [{status_color}]{status.upper()}[/{status_color}]")
        lines.append(f"Failed checks: {self.service_data.get('failed_checks', 0)}")

        # Timestamps
        registered_at = self.service_data.get('registered_at', 'N/A')
        last_seen = self.service_data.get('last_seen', 'N/A')
        lines.append(f"Registered: {registered_at}")
        lines.append(f"Last seen: {last_seen}")

        # Capabilities
        lines.append("")
        lines.append("[bold yellow]Capabilities:[/bold yellow]")
        for cap in self.service_data.get('capabilities', []):
            lines.append(f"  • {cap}")

        # Metadata
        metadata = self.service_data.get('metadata', {})
        if metadata:
            lines.append("")
            lines.append("[bold yellow]Metadata:[/bold yellow]")
            for key, value in metadata.items():
                lines.append(f"  {key}: {value}")

        # Connections
        if self.connections_data:
            consuming = self.connections_data.get('consuming', [])
            providing = self.connections_data.get('providing', [])

            if consuming:
                lines.append("")
                lines.append("[bold magenta]Consuming From:[/bold magenta]")
                for conn in consuming:
                    avg_latency = conn.get('avg_latency_ms', 0)
                    success_rate = conn.get('success_rate', 0) * 100
                    lines.append(f"  → {conn['provider_name']} ({conn['capability']})")
                    lines.append(f"    Requests: {conn['request_count']} | Success: {success_rate:.1f}% | Latency: {avg_latency:.1f}ms")

            if providing:
                lines.append("")
                lines.append("[bold magenta]Providing To:[/bold magenta]")
                for conn in providing:
                    avg_latency = conn.get('avg_latency_ms', 0)
                    success_rate = conn.get('success_rate', 0) * 100
                    lines.append(f"  ← {conn['consumer_name']} ({conn['capability']})")
                    lines.append(f"    Requests: {conn['request_count']} | Success: {success_rate:.1f}% | Latency: {avg_latency:.1f}ms")

        content = self.query_one("#detail-content", Static)
        content.update("\n".join(lines))


class StatsHeader(Static):
    """Header showing registry statistics"""

    def __init__(self):
        super().__init__()
        self.stats: Dict[str, Any] = {}

    def on_mount(self):
        """Load initial stats"""
        self.update_stats()

    @work(thread=True)
    def update_stats(self):
        """Fetch and update registry stats"""
        try:
            registry_url = self.app.registry_url
            resp = requests.get(f"{registry_url}/api/stats", timeout=5)
            if resp.status_code == 200:
                self.stats = resp.json()
                self.call_from_thread(self.render_stats)
        except Exception:
            pass

    def render_stats(self):
        """Render stats in the header"""
        total = self.stats.get('total_services', 0)
        active = self.stats.get('active_services', 0)
        inactive = self.stats.get('inactive_services', 0)
        capabilities = self.stats.get('total_capabilities', 0)

        self.update(
            f"[bold cyan]Modularity Registry[/bold cyan] | "
            f"Services: {total} "
            f"([green]●{active}[/green] [red]○{inactive}[/red]) | "
            f"Capabilities: {capabilities}"
        )


class RegistryTUI(App):
    """Main TUI application"""

    CSS = """
    Screen {
        background: $surface;
    }

    StatsHeader {
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
    }

    #main-container {
        height: 1fr;
    }

    ServiceListWidget {
        width: 35%;
        border-right: solid $primary;
    }

    ServiceDetailWidget {
        width: 65%;
    }

    .panel-title {
        background: $panel;
        color: $text;
        text-style: bold;
        padding: 0 1;
        height: 1;
    }

    #service-list {
        height: 1fr;
    }

    ListView {
        background: $surface;
    }

    ListView > ListItem {
        padding: 0 1;
    }

    ListView > ListItem:hover {
        background: $accent;
    }

    #detail-content {
        padding: 1 2;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("r", "refresh", "Refresh"),
        Binding("up,k", "cursor_up", "Up", show=False),
        Binding("down,j", "cursor_down", "Down", show=False),
    ]

    def __init__(self, registry_url: str = "http://localhost:5000"):
        super().__init__()
        self.registry_url = registry_url
        self.sse_thread: Optional[threading.Thread] = None
        self.sse_running = False

    def compose(self) -> ComposeResult:
        yield StatsHeader()
        with Horizontal(id="main-container"):
            yield ServiceListWidget()
            yield ServiceDetailWidget()
        yield Footer()

    def on_mount(self):
        """Initialize the app"""
        self.title = "Modularity Registry TUI"
        self.load_initial_data()
        self.start_sse_listener()

    @work(thread=True)
    def load_initial_data(self):
        """Load initial service list"""
        try:
            resp = requests.get(f"{self.registry_url}/api/services", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                services = data.get('services', [])
                self.call_from_thread(self.update_service_list, services)
        except Exception as e:
            self.call_from_thread(self.notify, f"Error loading services: {e}", severity="error")

    def update_service_list(self, services: List[Dict[str, Any]]):
        """Update the service list widget"""
        service_list = self.query_one(ServiceListWidget)
        service_list.update_services(services)

    def start_sse_listener(self):
        """Start SSE listener in background thread"""
        self.sse_running = True
        self.sse_thread = threading.Thread(target=self.sse_listener, daemon=True)
        self.sse_thread.start()

    def sse_listener(self):
        """Listen for SSE events from the registry"""
        while self.sse_running:
            try:
                url = f"{self.registry_url}/api/events"
                client = SSEClient(url)

                for event in client:
                    if not self.sse_running:
                        break

                    if event.data:
                        try:
                            data = json.loads(event.data)
                            self.call_from_thread(self.handle_sse_event, data)
                        except json.JSONDecodeError:
                            pass
            except Exception:
                # Reconnect after a delay
                time.sleep(5)

    def handle_sse_event(self, event_data: Dict[str, Any]):
        """Handle incoming SSE events"""
        event_type = event_data.get('event')
        data = event_data.get('data', {})

        if event_type == 'service.registered':
            # Refresh service list
            self.action_refresh()
        elif event_type == 'service.unregistered':
            # Remove service from list
            service_id = data.get('service_id')
            if service_id:
                service_list = self.query_one(ServiceListWidget)
                service_list.remove_service(service_id)
        elif event_type == 'service.status_changed':
            # Refresh service list
            self.action_refresh()
        elif event_type == 'capability.invoked':
            # Refresh detail view if it's showing the affected service
            detail_widget = self.query_one(ServiceDetailWidget)
            if detail_widget.selected_service_id in [data.get('consumer_id'), data.get('provider_id')]:
                detail_widget.load_service_details(detail_widget.selected_service_id)
            # Update stats
            stats_header = self.query_one(StatsHeader)
            stats_header.update_stats()

    def on_list_view_selected(self, event: ListView.Selected):
        """Handle service selection"""
        if isinstance(event.item, ServiceListItem):
            detail_widget = self.query_one(ServiceDetailWidget)
            detail_widget.selected_service_id = event.item.service_id

    def action_refresh(self):
        """Refresh all data"""
        self.load_initial_data()
        stats_header = self.query_one(StatsHeader)
        stats_header.update_stats()
        # Refresh detail view if service is selected
        detail_widget = self.query_one(ServiceDetailWidget)
        if detail_widget.selected_service_id:
            detail_widget.load_service_details(detail_widget.selected_service_id)

    def action_quit(self):
        """Quit the application"""
        self.sse_running = False
        self.exit()


def main():
    """Entry point for the TUI application"""
    import argparse

    parser = argparse.ArgumentParser(description="Modularity Registry TUI Dashboard")
    parser.add_argument(
        "--registry-url",
        default="http://localhost:5000",
        help="URL of the Modularity Registry (default: http://localhost:5000)"
    )

    args = parser.parse_args()

    app = RegistryTUI(registry_url=args.registry_url)
    app.run()


if __name__ == "__main__":
    main()
