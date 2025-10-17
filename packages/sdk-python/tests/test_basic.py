"""
Basic tests for the Modularity SDK
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from modularity_sdk import (
    ModuleInterface,
    ServiceInfo,
    ServiceProxy,
    ServiceLocator,
    EventBus,
    ModularitySDK,
    create_manifest_template
)


class TestModuleInterface:
    """Test ModuleInterface abstract base class"""

    def test_module_interface_is_abstract(self):
        """Verify ModuleInterface cannot be instantiated directly"""
        with pytest.raises(TypeError):
            ModuleInterface()


class TestServiceInfo:
    """Test ServiceInfo dataclass"""

    def test_service_info_creation(self):
        """Test creating a ServiceInfo instance"""
        service = ServiceInfo(
            id="test-service",
            location="http://localhost:3000",
            mode="http",
            capabilities=["cap1", "cap2"],
            status="healthy"
        )

        assert service.id == "test-service"
        assert service.location == "http://localhost:3000"
        assert service.mode == "http"
        assert service.capabilities == ["cap1", "cap2"]
        assert service.status == "healthy"


class TestServiceProxy:
    """Test ServiceProxy class"""

    def test_service_proxy_creation(self):
        """Test creating a ServiceProxy"""
        service_info = ServiceInfo(
            id="test",
            location="http://localhost:3000",
            mode="http",
            capabilities=["test-cap"],
            status="healthy"
        )
        proxy = ServiceProxy(service_info)
        assert proxy.service_info == service_info

    @patch('modularity_sdk.requests.post')
    def test_invoke_http(self, mock_post):
        """Test HTTP invocation"""
        mock_response = Mock()
        mock_response.json.return_value = {"result": "success"}
        mock_post.return_value = mock_response

        service_info = ServiceInfo(
            id="test",
            location="http://localhost:3000",
            mode="http",
            capabilities=["test-cap"],
            status="healthy"
        )
        proxy = ServiceProxy(service_info)
        result = proxy.invoke("test-cap", {"param": "value"})

        assert result == {"result": "success"}
        mock_post.assert_called_once()

    def test_invoke_unsupported_mode(self):
        """Test invoking with unsupported mode raises error"""
        service_info = ServiceInfo(
            id="test",
            location="unknown",
            mode="unsupported",
            capabilities=["test-cap"],
            status="healthy"
        )
        proxy = ServiceProxy(service_info)

        with pytest.raises(ValueError, match="Unsupported mode"):
            proxy.invoke("test-cap", {})


class TestServiceLocator:
    """Test ServiceLocator class"""

    def test_service_locator_creation(self):
        """Test creating a ServiceLocator"""
        locator = ServiceLocator("http://localhost:5000")
        assert locator.registry_url == "http://localhost:5000"

    @patch('modularity_sdk.requests.get')
    def test_get_capability(self, mock_get):
        """Test finding a service by capability"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'id': 'test-service',
            'location': 'http://localhost:3000',
            'mode': 'http',
            'capabilities': ['test-cap'],
            'status': 'healthy'
        }
        mock_get.return_value = mock_response

        locator = ServiceLocator()
        proxy = locator.get_capability("test-cap")

        assert isinstance(proxy, ServiceProxy)
        assert proxy.service_info.id == 'test-service'

    @patch('modularity_sdk.requests.get')
    def test_get_capability_uses_cache(self, mock_get):
        """Test that service locator caches results"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'id': 'test-service',
            'location': 'http://localhost:3000',
            'mode': 'http',
            'capabilities': ['test-cap'],
            'status': 'healthy'
        }
        mock_get.return_value = mock_response

        locator = ServiceLocator()
        proxy1 = locator.get_capability("test-cap")
        proxy2 = locator.get_capability("test-cap")

        # Should only call API once due to caching
        assert mock_get.call_count == 1
        assert proxy1.service_info.id == proxy2.service_info.id

    def test_clear_cache(self):
        """Test clearing the service cache"""
        locator = ServiceLocator()
        locator._cache["test"] = "value"
        locator._cache_time["test"] = 123456

        locator.clear_cache()

        assert len(locator._cache) == 0
        assert len(locator._cache_time) == 0


class TestEventBus:
    """Test EventBus class"""

    def test_event_bus_creation(self):
        """Test creating an EventBus"""
        bus = EventBus()
        assert len(bus._subscribers) == 0

    def test_subscribe_and_publish(self):
        """Test subscribing to and publishing events"""
        bus = EventBus()
        received_data = []

        def handler(data):
            received_data.append(data)

        bus.subscribe("test-event", handler)
        bus.publish("test-event", {"message": "hello"})

        # Give the thread a moment to execute
        import time
        time.sleep(0.1)

        assert len(received_data) == 1
        assert received_data[0] == {"message": "hello"}

    def test_multiple_subscribers(self):
        """Test multiple subscribers to the same event"""
        bus = EventBus()
        received_count = [0, 0]

        def handler1(data):
            received_count[0] += 1

        def handler2(data):
            received_count[1] += 1

        bus.subscribe("test-event", handler1)
        bus.subscribe("test-event", handler2)
        bus.publish("test-event", {})

        # Give threads a moment to execute
        import time
        time.sleep(0.1)

        assert received_count[0] == 1
        assert received_count[1] == 1

    def test_unsubscribe(self):
        """Test unsubscribing from events"""
        bus = EventBus()
        received_data = []

        def handler(data):
            received_data.append(data)

        bus.subscribe("test-event", handler)
        bus.unsubscribe("test-event", handler)
        bus.publish("test-event", {"message": "hello"})

        # Give the thread a moment to execute
        import time
        time.sleep(0.1)

        assert len(received_data) == 0


class TestModularitySDK:
    """Test ModularitySDK class"""

    def test_load_manifest(self):
        """Test loading a manifest file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "app.manifest.json"
            manifest_data = {
                "id": "test-app",
                "name": "Test App",
                "version": "1.0.0",
                "type": "module",
                "runtime": "python",
                "provides": {"capabilities": []},
                "interfaces": {}
            }
            with open(manifest_path, 'w') as f:
                json.dump(manifest_data, f)

            sdk = ModularitySDK(str(manifest_path))
            assert sdk.manifest['id'] == 'test-app'
            assert sdk.manifest['name'] == 'Test App'

    def test_load_manifest_not_found(self):
        """Test loading a non-existent manifest raises error"""
        with pytest.raises(FileNotFoundError):
            ModularitySDK("/nonexistent/path/app.manifest.json")

    def test_config_loading_from_env(self):
        """Test loading config from environment variables"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "app.manifest.json"
            manifest_data = {
                "id": "test-app",
                "name": "Test App",
                "version": "1.0.0",
                "type": "module",
                "runtime": "python",
                "provides": {"capabilities": []},
                "interfaces": {}
            }
            with open(manifest_path, 'w') as f:
                json.dump(manifest_data, f)

            with patch.dict('os.environ', {'TEST_APP_PORT': '8080'}):
                sdk = ModularitySDK(str(manifest_path))
                assert sdk.config.get('port') == '8080'

    @patch('modularity_sdk.requests.get')
    def test_invoke_capability(self, mock_get):
        """Test invoking a remote capability"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "app.manifest.json"
            manifest_data = {
                "id": "test-app",
                "name": "Test App",
                "version": "1.0.0",
                "type": "module",
                "runtime": "python",
                "provides": {"capabilities": []},
                "interfaces": {}
            }
            with open(manifest_path, 'w') as f:
                json.dump(manifest_data, f)

            # Mock the registry response
            mock_response = Mock()
            mock_response.json.return_value = {
                'id': 'remote-service',
                'location': 'http://localhost:3000',
                'mode': 'http',
                'capabilities': ['remote-cap'],
                'status': 'healthy'
            }
            mock_get.return_value = mock_response

            sdk = ModularitySDK(str(manifest_path))

            # Mock the actual capability invocation
            with patch('modularity_sdk.requests.post') as mock_post:
                mock_post_response = Mock()
                mock_post_response.json.return_value = {"result": "success"}
                mock_post.return_value = mock_post_response

                result = sdk.invoke_capability("remote-cap", {"param": "value"})
                assert result == {"result": "success"}

    def test_event_publishing(self):
        """Test publishing events"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "app.manifest.json"
            manifest_data = {
                "id": "test-app",
                "name": "Test App",
                "version": "1.0.0",
                "type": "module",
                "runtime": "python",
                "provides": {"capabilities": []},
                "interfaces": {}
            }
            with open(manifest_path, 'w') as f:
                json.dump(manifest_data, f)

            sdk = ModularitySDK(str(manifest_path))
            received_data = []

            def handler(data):
                received_data.append(data)

            sdk.subscribe_event("test-event", handler)
            sdk.publish_event("test-event", {"message": "hello"})

            # Give the thread a moment to execute
            import time
            time.sleep(0.1)

            assert len(received_data) == 1
            assert received_data[0] == {"message": "hello"}


class TestUtilityFunctions:
    """Test utility functions"""

    def test_create_manifest_template(self):
        """Test creating a manifest template"""
        manifest = create_manifest_template("test-app", "Test App", "python")

        assert manifest['id'] == 'test-app'
        assert manifest['name'] == 'Test App'
        assert manifest['runtime'] == 'python'
        assert manifest['version'] == '1.0.0'
        assert manifest['type'] == 'module'
        assert 'provides' in manifest
        assert 'requires' in manifest
        assert 'interfaces' in manifest
        assert 'config' in manifest


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
