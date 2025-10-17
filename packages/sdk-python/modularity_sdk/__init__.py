"""
Modularity SDK - Python Implementation
Allows apps to run standalone or as modules within larger applications
"""

import json
import os
import socket
import requests
import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
import time
from dataclasses import dataclass


@dataclass
class ServiceInfo:
    """Information about a registered service"""
    id: str
    location: str
    mode: str  # 'http', 'ipc', 'direct'
    capabilities: List[str]
    status: str


class ModuleInterface(ABC):
    """Base interface that all embeddable modules must implement"""

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Called when module is loaded"""
        pass

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities this module provides"""
        pass

    @abstractmethod
    def invoke(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a capability with given parameters"""
        pass

    @abstractmethod
    def handle_event(self, event: str, data: Dict[str, Any]):
        """Handle events from other modules"""
        pass

    @abstractmethod
    def shutdown(self):
        """Cleanup before module unload"""
        pass


class ServiceProxy:
    """Proxy for invoking remote services"""

    def __init__(self, service_info: ServiceInfo):
        self.service_info = service_info

    def invoke(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a capability on the remote service"""
        if self.service_info.mode == 'http':
            return self._invoke_http(capability, params)
        elif self.service_info.mode == 'ipc':
            return self._invoke_ipc(capability, params)
        else:
            raise ValueError(f"Unsupported mode: {self.service_info.mode}")

    def _invoke_http(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke via HTTP"""
        url = f"{self.service_info.location}/_module/invoke"
        response = requests.post(url, json={
            'capability': capability,
            'params': params
        }, timeout=30)
        response.raise_for_status()
        return response.json()

    def _invoke_ipc(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke via IPC socket"""
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(self.service_info.location)
            message = json.dumps({
                'jsonrpc': '2.0',
                'method': 'invoke',
                'params': {
                    'capability': capability,
                    'params': params
                },
                'id': 1
            })
            sock.sendall(message.encode() + b'\n')
            response = b''
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                if b'\n' in chunk:
                    break
            return json.loads(response.decode())['result']
        finally:
            sock.close()


class ServiceLocator:
    """Finds and connects to services providing specific capabilities"""

    def __init__(self, registry_url: str = "http://localhost:5000"):
        self.registry_url = registry_url
        self._cache = {}
        self._cache_ttl = 60  # Cache for 60 seconds
        self._cache_time = {}

    def get_capability(self, capability_name: str) -> ServiceProxy:
        """Find a service providing the specified capability"""
        # Check cache first
        if capability_name in self._cache:
            if time.time() - self._cache_time[capability_name] < self._cache_ttl:
                return self._cache[capability_name]

        # Query registry
        try:
            response = requests.get(
                f"{self.registry_url}/api/capabilities/{capability_name}",
                timeout=5
            )
            response.raise_for_status()
            service_data = response.json()

            service_info = ServiceInfo(
                id=service_data['id'],
                location=service_data['location'],
                mode=service_data['mode'],
                capabilities=service_data['capabilities'],
                status=service_data['status']
            )

            proxy = ServiceProxy(service_info)
            self._cache[capability_name] = proxy
            self._cache_time[capability_name] = time.time()

            return proxy
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to locate capability '{capability_name}': {e}")

    def clear_cache(self):
        """Clear the service cache"""
        self._cache.clear()
        self._cache_time.clear()


class EventBus:
    """Simple in-memory event bus (can be extended to use Redis/NATS)"""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()

    def publish(self, event_name: str, data: Dict[str, Any]):
        """Publish an event"""
        with self._lock:
            subscribers = self._subscribers.get(event_name, [])

        for handler in subscribers:
            try:
                threading.Thread(target=handler, args=(data,)).start()
            except Exception as e:
                print(f"Error handling event {event_name}: {e}")

    def subscribe(self, event_name: str, handler: Callable):
        """Subscribe to an event"""
        with self._lock:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            self._subscribers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: Callable):
        """Unsubscribe from an event"""
        with self._lock:
            if event_name in self._subscribers:
                self._subscribers[event_name].remove(handler)


class ModularitySDK:
    """Main SDK class for ecosystem integration"""

    def __init__(self, manifest_path: str = "app.manifest.json",
                 registry_url: str = "http://localhost:5000"):
        self.manifest_path = Path(manifest_path)
        self.manifest = self._load_manifest()
        self.registry_url = registry_url
        self.locator = ServiceLocator(registry_url)
        self.event_bus = EventBus()
        self.config = self._load_config()
        self._http_server = None
        self._ipc_server = None
        self._module_instance = None

    def _load_manifest(self) -> Dict[str, Any]:
        """Load the application manifest"""
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")

        with open(self.manifest_path) as f:
            return json.load(f)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration with cascade (defaults → env → file → runtime)"""
        config = {}

        # 1. Load defaults from manifest
        if 'config' in self.manifest and 'defaults' in self.manifest['config']:
            defaults_path = self.manifest_path.parent / self.manifest['config']['defaults']
            if defaults_path.exists():
                with open(defaults_path) as f:
                    config.update(json.load(f))

        # 2. Load from environment variables
        prefix = f"{self.manifest['id'].upper().replace('-', '_')}_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                config[config_key] = value

        # 3. Load from config file
        config_file = Path.home() / '.ecosystem' / f"{self.manifest['id']}.json"
        if config_file.exists():
            with open(config_file) as f:
                config.update(json.load(f))

        return config

    def run_standalone(self, host: str = "0.0.0.0", port: Optional[int] = None):
        """Run this app as a standalone service"""
        from flask import Flask, request, jsonify

        app = Flask(self.manifest['name'])

        # Load the module instance
        self._module_instance = self._load_module_instance()
        self._module_instance.initialize(self.config)

        # Standard module endpoints
        @app.route('/_module/health', methods=['GET'])
        def health():
            return jsonify({'status': 'healthy', 'app': self.manifest['name']})

        @app.route('/_module/capabilities', methods=['GET'])
        def capabilities():
            return jsonify({
                'capabilities': self._module_instance.get_capabilities()
            })

        @app.route('/_module/invoke', methods=['POST'])
        def invoke():
            data = request.json
            capability = data.get('capability')
            params = data.get('params', {})

            try:
                result = self._module_instance.invoke(capability, params)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Register with registry
        self._register_with_registry()

        # Start server
        if port is None:
            port = self.manifest.get('interfaces', {}).get('http', {}).get('port', 3000)

        print(f"Starting {self.manifest['name']} on {host}:{port}")
        app.run(host=host, port=port)

    def load_as_module(self, parent_config: Optional[Dict[str, Any]] = None) -> ModuleInterface:
        """Load this app as a module within another application"""
        if parent_config:
            self.config.update(parent_config)

        module = self._load_module_instance()
        module.initialize(self.config)
        return module

    def _load_module_instance(self) -> ModuleInterface:
        """Dynamically load the module class"""
        if 'module' not in self.manifest.get('interfaces', {}):
            raise ValueError("Module interface not defined in manifest")

        module_config = self.manifest['interfaces']['module']
        entry_file = self.manifest_path.parent / module_config['entry']
        class_name = module_config['class']

        # Dynamic import
        import importlib.util
        spec = importlib.util.spec_from_file_location("module", entry_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        module_class = getattr(module, class_name)
        return module_class()

    def invoke_capability(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a capability from another app in the ecosystem"""
        service = self.locator.get_capability(capability)
        return service.invoke(capability, params)

    def publish_event(self, event_name: str, data: Dict[str, Any]):
        """Publish an event to the ecosystem"""
        self.event_bus.publish(event_name, data)

    def subscribe_event(self, event_name: str, handler: Callable):
        """Subscribe to an ecosystem event"""
        self.event_bus.subscribe(event_name, handler)

    def _register_with_registry(self):
        """Register this service with the ecosystem registry"""
        registration_data = {
            'id': self.manifest['id'],
            'name': self.manifest['name'],
            'version': self.manifest['version'],
            'capabilities': self.manifest['provides']['capabilities'],
            'location': f"http://localhost:{self.manifest['interfaces']['http']['port']}",
            'mode': 'http'
        }

        try:
            response = requests.post(
                f"{self.registry_url}/api/register",
                json=registration_data,
                timeout=5
            )
            response.raise_for_status()
            print(f"Registered with ecosystem registry: {self.manifest['id']}")
        except requests.RequestException as e:
            print(f"Warning: Failed to register with registry: {e}")

    def load_local_module(self, module_path: str, config: Optional[Dict] = None) -> ModuleInterface:
        """Load another module from the local filesystem"""
        module_manifest_path = Path(module_path) / "app.manifest.json"
        module_sdk = ModularitySDK(str(module_manifest_path), self.registry_url)
        return module_sdk.load_as_module(config or {})


# Utility functions
def create_manifest_template(app_id: str, app_name: str, runtime: str) -> Dict[str, Any]:
    """Create a template manifest for a new application"""
    return {
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
                "entry": "src/module.py",
                "class": "AppModule"
            }
        },
        "config": {
            "defaults": "config.defaults.json"
        }
    }
