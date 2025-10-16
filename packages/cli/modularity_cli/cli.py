#!/usr/bin/env python3
"""
Modularity CLI Tool
Command-line interface for managing the modular application ecosystem
"""

import click
import requests
import json
from pathlib import Path
from typing import Dict, Any, Optional
import subprocess
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich import box
import yaml

console = Console()

DEFAULT_REGISTRY = "http://localhost:5000"
CONFIG_FILE = Path.home() / ".modularity" / "cli-config.json"


class ModularityCLI:
    """CLI helper class"""

    def __init__(self, registry_url: str = DEFAULT_REGISTRY):
        self.registry_url = registry_url
        self._load_config()

    def _load_config(self):
        """Load CLI configuration"""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                config = json.load(f)
                self.registry_url = config.get('registry_url', DEFAULT_REGISTRY)

    def _save_config(self):
        """Save CLI configuration"""
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'registry_url': self.registry_url}, f)

    def set_registry(self, url: str):
        """Set the registry URL"""
        self.registry_url = url
        self._save_config()

    def api_get(self, endpoint: str):
        """Make GET request to registry API"""
        try:
            response = requests.get(f"{self.registry_url}{endpoint}", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)

    def api_post(self, endpoint: str, data: Dict):
        """Make POST request to registry API"""
        try:
            response = requests.post(
                f"{self.registry_url}{endpoint}",
                json=data,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)

    def api_delete(self, endpoint: str):
        """Make DELETE request to registry API"""
        try:
            response = requests.delete(f"{self.registry_url}{endpoint}", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)


cli_helper = ModularityCLI()


@click.group()
@click.option('--registry', help='Registry URL', default=DEFAULT_REGISTRY)
def cli(registry):
    """Modularity CLI - Manage your modular application ecosystem"""
    if registry != DEFAULT_REGISTRY:
        cli_helper.set_registry(registry)


@cli.command()
def status():
    """Show modularity status and statistics"""
    stats = cli_helper.api_get("/api/stats")

    # Create status panel
    status_text = f"""
    [cyan]Total Services:[/cyan] {stats['total_services']}
    [green]Active:[/green] {stats['active_services']}
    [yellow]Inactive:[/yellow] {stats['inactive_services']}
    [blue]Capabilities:[/blue] {stats['total_capabilities']}
    """

    console.print(Panel(status_text, title="Modularity Status", border_style="green"))

    # Show services by runtime
    if stats['services_by_runtime']:
        console.print("\n[bold]Services by Runtime:[/bold]")
        for runtime, count in stats['services_by_runtime'].items():
            console.print(f"  • {runtime}: {count}")


@cli.command()
@click.option('--status', help='Filter by status (active/inactive)')
@click.option('--format', type=click.Choice(['table', 'json', 'yaml']), default='table')
def list(status, format):
    """List all registered services"""
    endpoint = "/api/services"
    if status:
        endpoint += f"?status={status}"

    data = cli_helper.api_get(endpoint)
    services = data['services']

    if format == 'json':
        console.print_json(data=services)
        return

    if format == 'yaml':
        console.print(yaml.dump(services, default_flow_style=False))
        return

    # Table format
    table = Table(title=f"Registered Services ({data['count']})", box=box.ROUNDED)
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Version")
    table.add_column("Status")
    table.add_column("Capabilities", style="blue")
    table.add_column("Location", style="dim")

    for service in services:
        status_color = "green" if service['status'] == 'active' else "red"
        caps = ", ".join(service['capabilities'][:3])
        if len(service['capabilities']) > 3:
            caps += f" (+{len(service['capabilities']) - 3} more)"

        table.add_row(
            service['id'],
            service['name'],
            service['version'],
            f"[{status_color}]{service['status']}[/{status_color}]",
            caps,
            service['location']
        )

    console.print(table)


@cli.command()
@click.argument('service_id')
@click.option('--format', type=click.Choice(['table', 'json', 'yaml']), default='table')
def info(service_id, format):
    """Show detailed information about a service"""
    service = cli_helper.api_get(f"/api/services/{service_id}")

    if format == 'json':
        console.print_json(data=service)
        return

    if format == 'yaml':
        console.print(yaml.dump(service, default_flow_style=False))
        return

    # Pretty format
    console.print(Panel(f"[bold cyan]{service['name']}[/bold cyan]",
                       subtitle=f"ID: {service['id']}",
                       border_style="cyan"))

    info_text = f"""
    [bold]Version:[/bold] {service['version']}
    [bold]Status:[/bold] {'[green]' if service['status'] == 'active' else '[red]'}{service['status']}
    [bold]Mode:[/bold] {service['mode']}
    [bold]Location:[/bold] {service['location']}
    [bold]Registered:[/bold] {service['registered_at']}
    [bold]Last Seen:[/bold] {service['last_seen']}
    """
    console.print(info_text)

    console.print("\n[bold]Capabilities:[/bold]")
    for cap in service['capabilities']:
        console.print(f"  • {cap}")


@cli.command()
@click.option('--format', type=click.Choice(['table', 'json']), default='table')
def capabilities(format):
    """List all available capabilities"""
    data = cli_helper.api_get("/api/capabilities")
    caps = data['capabilities']

    if format == 'json':
        console.print_json(data=caps)
        return

    table = Table(title=f"Available Capabilities ({data['count']})", box=box.ROUNDED)
    table.add_column("Capability", style="cyan")
    table.add_column("Providers", style="green")
    table.add_column("Count", justify="center")

    for cap in caps:
        providers = ", ".join(cap['providers'][:3])
        if cap['count'] > 3:
            providers += f" (+{cap['count'] - 3} more)"

        table.add_row(
            cap['capability'],
            providers,
            str(cap['count'])
        )

    console.print(table)


@cli.command()
@click.argument('capability_name')
def find(capability_name):
    """Find services providing a specific capability"""
    try:
        service = cli_helper.api_get(f"/api/capabilities/{capability_name}")
        console.print(f"\n[green]✓[/green] Found service: [bold]{service['name']}[/bold]")
        console.print(f"  ID: {service['id']}")
        console.print(f"  Location: {service['location']}")
        console.print(f"  Status: {service['status']}")
    except SystemExit:
        console.print(f"[red]✗[/red] No active services provide capability: {capability_name}")


@cli.command()
@click.argument('service_id')
def unregister(service_id):
    """Unregister a service from the modularity system"""
    if not click.confirm(f"Are you sure you want to unregister '{service_id}'?"):
        return

    result = cli_helper.api_delete(f"/api/unregister/{service_id}")
    console.print(f"[green]✓[/green] {result['message']}")


@cli.command()
@click.argument('app_id')
@click.argument('app_name')
@click.option('--runtime', type=click.Choice(['python', 'javascript', 'go', 'ruby']),
              default='python', help='Programming language runtime')
@click.option('--path', default='.', help='Directory to create the app')
def init(app_id, app_name, runtime, path):
    """Initialize a new modularity-compatible application"""
    app_path = Path(path) / app_id

    if app_path.exists():
        console.print(f"[red]Error: Directory {app_path} already exists[/red]")
        sys.exit(1)

    # Create directory structure
    app_path.mkdir(parents=True)
    (app_path / "src").mkdir()
    (app_path / "adapters").mkdir()

    # Create manifest
    manifest = {
        "id": app_id,
        "name": app_name,
        "version": "1.0.0",
        "type": "module",
        "runtime": runtime,
        "modes": {
            "standalone": True,
            "embeddable": True,
            "service": True
        },
        "provides": {
            "capabilities": [],
            "endpoints": [],
            "events": [],
            "commands": []
        },
        "requires": {
            "capabilities": [],
            "optional": []
        },
        "interfaces": {
            "http": {
                "port": 3000,
                "basePath": "/api"
            },
            "module": {
                "entry": f"src/module.{_get_extension(runtime)}",
                "class": "AppModule"
            }
        },
        "config": {
            "defaults": "config.defaults.json"
        }
    }

    with open(app_path / "app.manifest.json", 'w') as f:
        json.dump(manifest, f, indent=2)

    # Create default config
    with open(app_path / "config.defaults.json", 'w') as f:
        json.dump({}, f, indent=2)

    # Create template files based on runtime
    _create_template_files(app_path, runtime)

    console.print(f"\n[green]✓[/green] Created new {runtime} application: [bold]{app_name}[/bold]")
    console.print(f"  Location: {app_path}")
    console.print("\nNext steps:")
    console.print(f"  1. cd {app_path}")
    console.print("  2. Edit app.manifest.json to define capabilities")
    console.print(f"  3. Implement your module in src/module.{_get_extension(runtime)}")
    console.print("  4. Run with: modularity run")


@cli.command()
@click.option('--manifest', default='app.manifest.json', help='Path to manifest file')
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', type=int, help='Port to bind to (overrides manifest)')
def run(manifest, host, port):
    """Run an application in standalone mode"""
    manifest_path = Path(manifest)

    if not manifest_path.exists():
        console.print(f"[red]Error: Manifest not found: {manifest}[/red]")
        sys.exit(1)

    with open(manifest_path) as f:
        manifest_data = json.load(f)

    runtime = manifest_data['runtime']

    console.print(f"[cyan]Starting {manifest_data['name']}...[/cyan]")

    # Run based on runtime
    if runtime == 'python':
        _run_python_app(manifest_path, host, port)
    elif runtime == 'javascript':
        _run_javascript_app(manifest_path, host, port)
    else:
        console.print(f"[yellow]Runtime {runtime} not yet supported by CLI[/yellow]")
        console.print("Please run manually")


@cli.command()
@click.argument('manifest_path')
def validate(manifest_path):
    """Validate an application manifest"""
    path = Path(manifest_path)

    if not path.exists():
        console.print(f"[red]✗ Manifest not found: {manifest_path}[/red]")
        sys.exit(1)

    try:
        with open(path) as f:
            manifest = json.load(f)

        # Check required fields
        required = ['id', 'name', 'version', 'runtime', 'provides', 'interfaces']
        missing = [field for field in required if field not in manifest]

        if missing:
            console.print(f"[red]✗ Missing required fields: {', '.join(missing)}[/red]")
            sys.exit(1)

        console.print("[green]✓ Manifest is valid[/green]")

        # Show summary
        console.print(f"\n[bold]Application:[/bold] {manifest['name']}")
        console.print(f"[bold]ID:[/bold] {manifest['id']}")
        console.print(f"[bold]Runtime:[/bold] {manifest['runtime']}")
        console.print(f"[bold]Capabilities:[/bold] {len(manifest['provides']['capabilities'])}")

    except json.JSONDecodeError as e:
        console.print(f"[red]✗ Invalid JSON: {e}[/red]")
        sys.exit(1)


def _get_extension(runtime: str) -> str:
    """Get file extension for runtime"""
    extensions = {
        'python': 'py',
        'javascript': 'js',
        'go': 'go',
        'ruby': 'rb'
    }
    return extensions.get(runtime, 'txt')


def _create_template_files(app_path: Path, runtime: str):
    """Create template implementation files"""
    if runtime == 'python':
        module_code = '''"""Application module implementation"""

from ecosystem_sdk import ModuleInterface


class AppModule(ModuleInterface):
    """Main application module"""

    def initialize(self, config):
        """Initialize the module"""
        self.config = config
        print(f"Module initialized with config: {config}")
        return True

    def get_capabilities(self):
        """Return list of capabilities"""
        return []  # Add your capabilities here

    def invoke(self, capability, params):
        """Execute a capability"""
        raise NotImplementedError(f"Capability not implemented: {capability}")

    def handle_event(self, event, data):
        """Handle an event"""
        print(f"Received event: {event} with data: {data}")

    def shutdown(self):
        """Cleanup"""
        print("Module shutting down")
'''

        standalone_code = '''"""Standalone entry point"""

from ecosystem_sdk import EcosystemSDK

if __name__ == "__main__":
    sdk = EcosystemSDK("app.manifest.json")
    sdk.run_standalone()
'''

        (app_path / "src" / "module.py").write_text(module_code)
        (app_path / "src" / "standalone.py").write_text(standalone_code)

    elif runtime == 'javascript':
        module_code = '''/**
 * Application module implementation
 */

const { ModuleInterface } = require('ecosystem-sdk');

class AppModule extends ModuleInterface {
    async initialize(config) {
        this.config = config;
        console.log('Module initialized with config:', config);
        return true;
    }

    async getCapabilities() {
        return []; // Add your capabilities here
    }

    async invoke(capability, params) {
        throw new Error(`Capability not implemented: ${capability}`);
    }

    async handleEvent(event, data) {
        console.log('Received event:', event, 'with data:', data);
    }

    async shutdown() {
        console.log('Module shutting down');
    }
}

module.exports = { AppModule };
'''

        standalone_code = '''/**
 * Standalone entry point
 */

const { EcosystemSDK } = require('ecosystem-sdk');

async function main() {
    const sdk = new EcosystemSDK('app.manifest.json');
    await sdk.init();
    await sdk.runStandalone();
}

main().catch(console.error);
'''

        (app_path / "src" / "module.js").write_text(module_code)
        (app_path / "src" / "standalone.js").write_text(standalone_code)


def _run_python_app(manifest_path: Path, host: str, port: Optional[int]):
    """Run a Python application"""
    app_dir = manifest_path.parent
    standalone_script = app_dir / "src" / "standalone.py"

    if not standalone_script.exists():
        console.print(f"[red]Error: Standalone script not found: {standalone_script}[/red]")
        sys.exit(1)

    cmd = [sys.executable, str(standalone_script)]
    subprocess.run(cmd, cwd=app_dir)


def _run_javascript_app(manifest_path: Path, host: str, port: Optional[int]):
    """Run a JavaScript application"""
    app_dir = manifest_path.parent
    standalone_script = app_dir / "src" / "standalone.js"

    if not standalone_script.exists():
        console.print(f"[red]Error: Standalone script not found: {standalone_script}[/red]")
        sys.exit(1)

    cmd = ['node', str(standalone_script)]
    subprocess.run(cmd, cwd=app_dir)


if __name__ == '__main__':
    cli()
