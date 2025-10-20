"""
Tests for the Modularity Registry Service
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path to import registry_service
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from registry_service import app, registry, capability_index, registry_lock, RegistryStore, rebuild_capability_index, connections, connections_lock, sse_clients, sse_lock


@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear the registry before each test"""
    with registry_lock:
        registry.clear()
        capability_index.clear()
    with connections_lock:
        connections.clear()
    with sse_lock:
        sse_clients.clear()
    yield
    with registry_lock:
        registry.clear()
        capability_index.clear()
    with connections_lock:
        connections.clear()
    with sse_lock:
        sse_clients.clear()


class TestRegistryStore:
    """Test RegistryStore class"""

    def test_registry_store_save_and_load(self):
        """Test saving and loading registry data"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_registry.json"
            store = RegistryStore(str(storage_path))

            test_data = {
                'service1': {
                    'id': 'service1',
                    'name': 'Test Service',
                    'capabilities': ['cap1']
                }
            }

            store.save(test_data)
            loaded_data = store.load()

            assert loaded_data == test_data

    def test_registry_store_load_nonexistent(self):
        """Test loading from non-existent file returns empty dict"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "nonexistent.json"
            store = RegistryStore(str(storage_path))

            loaded_data = store.load()
            assert loaded_data == {}


class TestServiceRegistration:
    """Test service registration endpoints"""

    def test_register_service_success(self, client):
        """Test successful service registration"""
        service_data = {
            'id': 'test-service',
            'name': 'Test Service',
            'version': '1.0.0',
            'capabilities': ['test-cap1', 'test-cap2'],
            'location': 'http://localhost:3000',
            'mode': 'http'
        }

        response = client.post('/api/register',
                               data=json.dumps(service_data),
                               content_type='application/json')

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['message'] == 'Service registered successfully'
        assert data['service_id'] == 'test-service'

        # Verify service is in registry
        with registry_lock:
            assert 'test-service' in registry
            assert registry['test-service']['name'] == 'Test Service'
            assert 'test-cap1' in capability_index
            assert 'test-cap2' in capability_index

    def test_register_service_missing_fields(self, client):
        """Test registration with missing required fields"""
        service_data = {
            'id': 'test-service',
            'name': 'Test Service'
            # Missing capabilities, location, mode
        }

        response = client.post('/api/register',
                               data=json.dumps(service_data),
                               content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_register_multiple_services(self, client):
        """Test registering multiple services"""
        services = [
            {
                'id': 'service1',
                'name': 'Service 1',
                'capabilities': ['cap1'],
                'location': 'http://localhost:3001',
                'mode': 'http'
            },
            {
                'id': 'service2',
                'name': 'Service 2',
                'capabilities': ['cap2'],
                'location': 'http://localhost:3002',
                'mode': 'http'
            }
        ]

        for service in services:
            response = client.post('/api/register',
                                   data=json.dumps(service),
                                   content_type='application/json')
            assert response.status_code == 201

        with registry_lock:
            assert len(registry) == 2


class TestServiceUnregistration:
    """Test service unregistration endpoints"""

    def test_unregister_service_success(self, client):
        """Test successful service unregistration"""
        # First register a service
        service_data = {
            'id': 'test-service',
            'name': 'Test Service',
            'capabilities': ['test-cap'],
            'location': 'http://localhost:3000',
            'mode': 'http'
        }
        client.post('/api/register',
                    data=json.dumps(service_data),
                    content_type='application/json')

        # Then unregister it
        response = client.delete('/api/unregister/test-service')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'Service unregistered successfully'

        # Verify service is removed
        with registry_lock:
            assert 'test-service' not in registry
            assert 'test-cap' not in capability_index

    def test_unregister_nonexistent_service(self, client):
        """Test unregistering a non-existent service"""
        response = client.delete('/api/unregister/nonexistent-service')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data


class TestServiceListing:
    """Test service listing endpoints"""

    def test_list_services_empty(self, client):
        """Test listing services when registry is empty"""
        response = client.get('/api/services')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] == 0
        assert data['services'] == []

    def test_list_services(self, client):
        """Test listing registered services"""
        # Register two services
        services = [
            {
                'id': 'service1',
                'name': 'Service 1',
                'capabilities': ['cap1'],
                'location': 'http://localhost:3001',
                'mode': 'http'
            },
            {
                'id': 'service2',
                'name': 'Service 2',
                'capabilities': ['cap2'],
                'location': 'http://localhost:3002',
                'mode': 'http'
            }
        ]

        for service in services:
            client.post('/api/register',
                        data=json.dumps(service),
                        content_type='application/json')

        response = client.get('/api/services')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] == 2
        assert len(data['services']) == 2

    def test_list_services_with_status_filter(self, client):
        """Test listing services with status filter"""
        # Register a service
        service_data = {
            'id': 'test-service',
            'name': 'Test Service',
            'capabilities': ['test-cap'],
            'location': 'http://localhost:3000',
            'mode': 'http'
        }
        client.post('/api/register',
                    data=json.dumps(service_data),
                    content_type='application/json')

        # Mark as inactive
        with registry_lock:
            registry['test-service']['status'] = 'inactive'

        response = client.get('/api/services?status=active')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] == 0

        response = client.get('/api/services?status=inactive')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] == 1

    def test_get_service_by_id(self, client):
        """Test getting a specific service by ID"""
        service_data = {
            'id': 'test-service',
            'name': 'Test Service',
            'capabilities': ['test-cap'],
            'location': 'http://localhost:3000',
            'mode': 'http'
        }
        client.post('/api/register',
                    data=json.dumps(service_data),
                    content_type='application/json')

        response = client.get('/api/services/test-service')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['id'] == 'test-service'
        assert data['name'] == 'Test Service'

    def test_get_nonexistent_service(self, client):
        """Test getting a non-existent service"""
        response = client.get('/api/services/nonexistent')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data


class TestCapabilities:
    """Test capability endpoints"""

    def test_list_capabilities_empty(self, client):
        """Test listing capabilities when registry is empty"""
        response = client.get('/api/capabilities')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] == 0
        assert data['capabilities'] == []

    def test_list_capabilities(self, client):
        """Test listing capabilities"""
        services = [
            {
                'id': 'service1',
                'name': 'Service 1',
                'capabilities': ['cap1', 'cap2'],
                'location': 'http://localhost:3001',
                'mode': 'http'
            },
            {
                'id': 'service2',
                'name': 'Service 2',
                'capabilities': ['cap2', 'cap3'],
                'location': 'http://localhost:3002',
                'mode': 'http'
            }
        ]

        for service in services:
            client.post('/api/register',
                        data=json.dumps(service),
                        content_type='application/json')

        response = client.get('/api/capabilities')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] == 3  # cap1, cap2, cap3

    def test_get_capability_success(self, client):
        """Test getting a service by capability"""
        service_data = {
            'id': 'test-service',
            'name': 'Test Service',
            'capabilities': ['test-cap'],
            'location': 'http://localhost:3000',
            'mode': 'http'
        }
        client.post('/api/register',
                    data=json.dumps(service_data),
                    content_type='application/json')

        response = client.get('/api/capabilities/test-cap')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['id'] == 'test-service'

    def test_get_capability_not_found(self, client):
        """Test getting a non-existent capability"""
        response = client.get('/api/capabilities/nonexistent-cap')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_get_capability_no_active_services(self, client):
        """Test getting a capability when no active services provide it"""
        service_data = {
            'id': 'test-service',
            'name': 'Test Service',
            'capabilities': ['test-cap'],
            'location': 'http://localhost:3000',
            'mode': 'http'
        }
        client.post('/api/register',
                    data=json.dumps(service_data),
                    content_type='application/json')

        # Mark service as inactive
        with registry_lock:
            registry['test-service']['status'] = 'inactive'

        response = client.get('/api/capabilities/test-cap')

        assert response.status_code == 503
        data = json.loads(response.data)
        assert 'error' in data


class TestHeartbeat:
    """Test heartbeat endpoint"""

    def test_heartbeat_success(self, client):
        """Test sending heartbeat for a service"""
        service_data = {
            'id': 'test-service',
            'name': 'Test Service',
            'capabilities': ['test-cap'],
            'location': 'http://localhost:3000',
            'mode': 'http'
        }
        client.post('/api/register',
                    data=json.dumps(service_data),
                    content_type='application/json')

        # Mark as inactive first
        with registry_lock:
            registry['test-service']['status'] = 'inactive'
            registry['test-service']['failed_checks'] = 5

        response = client.post('/api/heartbeat/test-service')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'Heartbeat received'

        # Verify status is updated
        with registry_lock:
            assert registry['test-service']['status'] == 'active'
            assert registry['test-service']['failed_checks'] == 0

    def test_heartbeat_nonexistent_service(self, client):
        """Test sending heartbeat for non-existent service"""
        response = client.post('/api/heartbeat/nonexistent')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data


class TestStats:
    """Test statistics endpoint"""

    def test_get_stats_empty(self, client):
        """Test getting stats when registry is empty"""
        response = client.get('/api/stats')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['total_services'] == 0
        assert data['active_services'] == 0
        assert data['inactive_services'] == 0
        assert data['total_capabilities'] == 0

    def test_get_stats(self, client):
        """Test getting registry statistics"""
        services = [
            {
                'id': 'service1',
                'name': 'Service 1',
                'capabilities': ['cap1', 'cap2'],
                'location': 'http://localhost:3001',
                'mode': 'http',
                'metadata': {'runtime': 'python'}
            },
            {
                'id': 'service2',
                'name': 'Service 2',
                'capabilities': ['cap3'],
                'location': 'http://localhost:3002',
                'mode': 'http',
                'metadata': {'runtime': 'node'}
            }
        ]

        for service in services:
            client.post('/api/register',
                        data=json.dumps(service),
                        content_type='application/json')

        # Mark one as inactive
        with registry_lock:
            registry['service2']['status'] = 'inactive'

        response = client.get('/api/stats')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['total_services'] == 2
        assert data['active_services'] == 1
        assert data['inactive_services'] == 1
        assert data['total_capabilities'] == 3
        assert data['services_by_runtime']['python'] == 1
        assert data['services_by_runtime']['node'] == 1


class TestServiceDiscovery:
    """Test service discovery endpoint"""

    def test_discover_services_by_required_capabilities(self, client):
        """Test discovering services by required capabilities"""
        services = [
            {
                'id': 'service1',
                'name': 'Service 1',
                'capabilities': ['cap1', 'cap2', 'cap3'],
                'location': 'http://localhost:3001',
                'mode': 'http'
            },
            {
                'id': 'service2',
                'name': 'Service 2',
                'capabilities': ['cap1', 'cap2'],
                'location': 'http://localhost:3002',
                'mode': 'http'
            },
            {
                'id': 'service3',
                'name': 'Service 3',
                'capabilities': ['cap1'],
                'location': 'http://localhost:3003',
                'mode': 'http'
            }
        ]

        for service in services:
            client.post('/api/register',
                        data=json.dumps(service),
                        content_type='application/json')

        # Discover services with required capabilities
        discovery_request = {
            'capabilities': ['cap1', 'cap2']
        }

        response = client.post('/api/discover',
                               data=json.dumps(discovery_request),
                               content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] == 2  # service1 and service2
        assert len(data['matches']) == 2

    def test_discover_services_with_optional_capabilities(self, client):
        """Test discovering services with optional capabilities"""
        services = [
            {
                'id': 'service1',
                'name': 'Service 1',
                'capabilities': ['cap1', 'cap2', 'cap3'],
                'location': 'http://localhost:3001',
                'mode': 'http'
            },
            {
                'id': 'service2',
                'name': 'Service 2',
                'capabilities': ['cap1', 'cap2'],
                'location': 'http://localhost:3002',
                'mode': 'http'
            }
        ]

        for service in services:
            client.post('/api/register',
                        data=json.dumps(service),
                        content_type='application/json')

        # Discover with optional capabilities
        discovery_request = {
            'capabilities': ['cap1'],
            'optional': ['cap3']
        }

        response = client.post('/api/discover',
                               data=json.dumps(discovery_request),
                               content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] == 2
        # service1 should have higher match score
        assert data['matches'][0]['service']['id'] == 'service1'

    def test_discover_no_matches(self, client):
        """Test discovering when no services match"""
        service_data = {
            'id': 'service1',
            'name': 'Service 1',
            'capabilities': ['cap1'],
            'location': 'http://localhost:3001',
            'mode': 'http'
        }
        client.post('/api/register',
                    data=json.dumps(service_data),
                    content_type='application/json')

        discovery_request = {
            'capabilities': ['nonexistent-cap']
        }

        response = client.post('/api/discover',
                               data=json.dumps(discovery_request),
                               content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] == 0


class TestHealthCheck:
    """Test health check endpoint"""

    def test_registry_health(self, client):
        """Test registry health check"""
        response = client.get('/health')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['service'] == 'modularity-registry'
        assert 'timestamp' in data


class TestUtilityFunctions:
    """Test utility functions"""

    def test_rebuild_capability_index(self):
        """Test rebuilding capability index"""
        with registry_lock:
            registry['service1'] = {
                'id': 'service1',
                'capabilities': ['cap1', 'cap2']
            }
            registry['service2'] = {
                'id': 'service2',
                'capabilities': ['cap2', 'cap3']
            }

        rebuild_capability_index()

        with registry_lock:
            assert 'cap1' in capability_index
            assert 'cap2' in capability_index
            assert 'cap3' in capability_index
            assert capability_index['cap1'] == ['service1']
            assert set(capability_index['cap2']) == {'service1', 'service2'}
            assert capability_index['cap3'] == ['service2']


class TestSSEEvents:
    """Test Server-Sent Events endpoint"""

    def test_sse_connection(self, client):
        """Test connecting to SSE endpoint"""
        response = client.get('/api/events', buffered=False)
        assert response.status_code == 200
        assert response.mimetype == 'text/event-stream'

    # Note: SSE event streaming tests using threading are not included here
    # due to Flask test client limitations with thread-local contexts.
    # SSE functionality has been manually verified and works correctly in production.


class TestInvocationTracking:
    """Test capability invocation tracking"""

    def test_track_invocation_success(self, client):
        """Test tracking a successful capability invocation"""
        invocation_data = {
            'consumer_id': 'consumer1',
            'provider_id': 'provider1',
            'capability': 'test-cap',
            'success': True,
            'latency_ms': 42.5
        }

        response = client.post('/api/track/invocation',
                              data=json.dumps(invocation_data),
                              content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'Invocation tracked'

        # Verify connection was recorded
        with connections_lock:
            assert 'consumer1' in connections
            assert len(connections['consumer1']) == 1
            conn = connections['consumer1'][0]
            assert conn.consumer_id == 'consumer1'
            assert conn.provider_id == 'provider1'
            assert conn.capability == 'test-cap'
            assert conn.request_count == 1
            assert conn.success_count == 1
            assert conn.total_latency_ms == 42.5

    def test_track_invocation_failure(self, client):
        """Test tracking a failed capability invocation"""
        invocation_data = {
            'consumer_id': 'consumer1',
            'provider_id': 'provider1',
            'capability': 'test-cap',
            'success': False,
            'latency_ms': 15.0
        }

        response = client.post('/api/track/invocation',
                              data=json.dumps(invocation_data),
                              content_type='application/json')

        assert response.status_code == 200

        # Verify connection metrics
        with connections_lock:
            conn = connections['consumer1'][0]
            assert conn.request_count == 1
            assert conn.success_count == 0

    def test_track_multiple_invocations(self, client):
        """Test tracking multiple invocations aggregates correctly"""
        for i in range(5):
            invocation_data = {
                'consumer_id': 'consumer1',
                'provider_id': 'provider1',
                'capability': 'test-cap',
                'success': True,
                'latency_ms': 10.0 + i
            }
            client.post('/api/track/invocation',
                       data=json.dumps(invocation_data),
                       content_type='application/json')

        # Verify aggregated metrics
        with connections_lock:
            conn = connections['consumer1'][0]
            assert conn.request_count == 5
            assert conn.success_count == 5
            assert conn.total_latency_ms == 60.0  # 10+11+12+13+14

    def test_track_invocation_missing_fields(self, client):
        """Test tracking with missing required fields"""
        invocation_data = {
            'consumer_id': 'consumer1',
            'provider_id': 'provider1'
            # Missing capability, success, latency_ms
        }

        response = client.post('/api/track/invocation',
                              data=json.dumps(invocation_data),
                              content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    # Note: Event broadcasting tests are omitted due to Flask test client
    # threading limitations. Event broadcasting has been manually verified.


class TestConnectionsEndpoint:
    """Test connections endpoint"""

    def test_get_connections_empty(self, client):
        """Test getting connections for a service with no connections"""
        # Register a service first
        service_data = {
            'id': 'test-service',
            'name': 'Test Service',
            'capabilities': ['test-cap'],
            'location': 'http://localhost:3000',
            'mode': 'http'
        }
        client.post('/api/register',
                   data=json.dumps(service_data),
                   content_type='application/json')

        response = client.get('/api/connections/test-service')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['service_id'] == 'test-service'
        assert len(data['consuming']) == 0
        assert len(data['providing']) == 0

    def test_get_connections_as_consumer(self, client):
        """Test getting connections where service is the consumer"""
        # Register services
        for i in range(3):
            service_data = {
                'id': f'service{i}',
                'name': f'Service {i}',
                'capabilities': [f'cap{i}'],
                'location': f'http://localhost:300{i}',
                'mode': 'http'
            }
            client.post('/api/register',
                       data=json.dumps(service_data),
                       content_type='application/json')

        # Track invocations where service0 is consumer (calling service1 and service2)
        for i in [1, 2]:
            invocation_data = {
                'consumer_id': 'service0',
                'provider_id': f'service{i}',
                'capability': f'cap{i}',
                'success': True,
                'latency_ms': 10.0 + i
            }
            client.post('/api/track/invocation',
                       data=json.dumps(invocation_data),
                       content_type='application/json')

        response = client.get('/api/connections/service0')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['consuming']) == 2
        assert len(data['providing']) == 0

    def test_get_connections_as_provider(self, client):
        """Test getting connections where service is the provider"""
        # Register services
        for i in range(3):
            service_data = {
                'id': f'service{i}',
                'name': f'Service {i}',
                'capabilities': [f'cap{i}'],
                'location': f'http://localhost:300{i}',
                'mode': 'http'
            }
            client.post('/api/register',
                       data=json.dumps(service_data),
                       content_type='application/json')

        # Track invocations where service0 is provider
        for i in [1, 2]:
            invocation_data = {
                'consumer_id': f'service{i}',
                'provider_id': 'service0',
                'capability': 'cap0',
                'success': True,
                'latency_ms': 20.0 + i
            }
            client.post('/api/track/invocation',
                       data=json.dumps(invocation_data),
                       content_type='application/json')

        response = client.get('/api/connections/service0')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['consuming']) == 0
        assert len(data['providing']) == 2

    def test_get_connections_nonexistent_service(self, client):
        """Test getting connections for non-existent service"""
        response = client.get('/api/connections/nonexistent')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data


class TestServiceGraph:
    """Test service dependency graph endpoint"""

    def test_get_graph_empty(self, client):
        """Test getting graph when no services are registered"""
        response = client.get('/api/graph')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['nodes']) == 0
        assert len(data['edges']) == 0

    def test_get_graph_with_services(self, client):
        """Test getting graph with registered services"""
        # Register services
        services = [
            {
                'id': 'service1',
                'name': 'Service 1',
                'capabilities': ['cap1'],
                'location': 'http://localhost:3001',
                'mode': 'http'
            },
            {
                'id': 'service2',
                'name': 'Service 2',
                'capabilities': ['cap2'],
                'location': 'http://localhost:3002',
                'mode': 'http'
            }
        ]

        for service in services:
            client.post('/api/register',
                       data=json.dumps(service),
                       content_type='application/json')

        response = client.get('/api/graph')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['nodes']) == 2
        assert len(data['edges']) == 0

    def test_get_graph_with_connections(self, client):
        """Test getting graph with connections between services"""
        # Register services
        services = [
            {
                'id': 'service1',
                'name': 'Service 1',
                'capabilities': ['cap1'],
                'location': 'http://localhost:3001',
                'mode': 'http'
            },
            {
                'id': 'service2',
                'name': 'Service 2',
                'capabilities': ['cap2'],
                'location': 'http://localhost:3002',
                'mode': 'http'
            }
        ]

        for service in services:
            client.post('/api/register',
                       data=json.dumps(service),
                       content_type='application/json')

        # Track invocations (service1 -> service2)
        for i in range(3):
            invocation_data = {
                'consumer_id': 'service1',
                'provider_id': 'service2',
                'capability': 'cap2',
                'success': i < 2,  # 2 successes, 1 failure
                'latency_ms': 10.0 + i
            }
            client.post('/api/track/invocation',
                       data=json.dumps(invocation_data),
                       content_type='application/json')

        response = client.get('/api/graph')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['nodes']) == 2
        assert len(data['edges']) == 1

        edge = data['edges'][0]
        assert edge['from'] == 'service1'
        assert edge['to'] == 'service2'
        assert edge['capability'] == 'cap2'
        assert edge['weight'] == 3
        assert abs(edge['success_rate'] - 0.6667) < 0.001  # 2/3
        assert abs(edge['avg_latency_ms'] - 11.0) < 0.001  # (10+11+12)/3

    def test_get_graph_with_multiple_edges(self, client):
        """Test graph with multiple connections between services"""
        # Register services
        for i in range(3):
            service_data = {
                'id': f'service{i}',
                'name': f'Service {i}',
                'capabilities': [f'cap{i}'],
                'location': f'http://localhost:300{i}',
                'mode': 'http'
            }
            client.post('/api/register',
                       data=json.dumps(service_data),
                       content_type='application/json')

        # Create connections: service0 -> service1, service0 -> service2
        connections_to_create = [
            ('service0', 'service1', 'cap1'),
            ('service0', 'service2', 'cap2')
        ]

        for consumer, provider, cap in connections_to_create:
            invocation_data = {
                'consumer_id': consumer,
                'provider_id': provider,
                'capability': cap,
                'success': True,
                'latency_ms': 15.0
            }
            client.post('/api/track/invocation',
                       data=json.dumps(invocation_data),
                       content_type='application/json')

        response = client.get('/api/graph')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['nodes']) == 3
        assert len(data['edges']) == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
