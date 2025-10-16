"""
Tests for the Modularity CLI
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
import sys
import os

# Add parent directory to path to import modularity_cli
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modularity_cli.cli import (
    cli,
    ModularityCLI,
    _get_extension,
    _create_template_files
)


@pytest.fixture
def runner():
    """Create a CLI runner for testing"""
    return CliRunner()


@pytest.fixture
def mock_api():
    """Mock API responses"""
    with patch('modularity_cli.cli.requests') as mock_requests:
        yield mock_requests


class TestModularityCLI:
    """Test ModularityCLI helper class"""

    def test_cli_initialization(self):
        """Test CLI helper initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "cli-config.json"
            with patch('modularity_cli.cli.CONFIG_FILE', config_file):
                cli_helper = ModularityCLI()
                assert cli_helper.registry_url == "http://localhost:5000"

    def test_save_and_load_config(self):
        """Test saving and loading configuration"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "cli-config.json"
            with patch('modularity_cli.cli.CONFIG_FILE', config_file):
                cli_helper = ModularityCLI()
                cli_helper.set_registry("http://custom:5000")

                # Create new instance to test loading
                cli_helper2 = ModularityCLI()
                assert cli_helper2.registry_url == "http://custom:5000"


class TestStatusCommand:
    """Test the status command"""

    def test_status_command(self, runner, mock_api):
        """Test status command displays statistics"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'total_services': 5,
            'active_services': 4,
            'inactive_services': 1,
            'total_capabilities': 10,
            'services_by_runtime': {
                'python': 3,
                'javascript': 2
            }
        }
        mock_api.get.return_value = mock_response

        result = runner.invoke(cli, ['status'])

        assert result.exit_code == 0
        assert 'Modularity Status' in result.output
        assert '5' in result.output  # total services
        assert '4' in result.output  # active services


class TestListCommand:
    """Test the list command"""

    def test_list_services_table(self, runner, mock_api):
        """Test listing services in table format"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'services': [
                {
                    'id': 'service1',
                    'name': 'Service 1',
                    'version': '1.0.0',
                    'status': 'active',
                    'capabilities': ['cap1', 'cap2'],
                    'location': 'http://localhost:3001'
                },
                {
                    'id': 'service2',
                    'name': 'Service 2',
                    'version': '1.0.0',
                    'status': 'inactive',
                    'capabilities': ['cap3'],
                    'location': 'http://localhost:3002'
                }
            ],
            'count': 2
        }
        mock_api.get.return_value = mock_response

        result = runner.invoke(cli, ['list'])

        assert result.exit_code == 0
        assert 'Service 1' in result.output
        assert 'Service 2' in result.output

    def test_list_services_json(self, runner, mock_api):
        """Test listing services in JSON format"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'services': [
                {
                    'id': 'service1',
                    'name': 'Service 1',
                    'version': '1.0.0',
                    'status': 'active',
                    'capabilities': ['cap1'],
                    'location': 'http://localhost:3001'
                }
            ],
            'count': 1
        }
        mock_api.get.return_value = mock_response

        result = runner.invoke(cli, ['list', '--format', 'json'])

        assert result.exit_code == 0
        assert 'service1' in result.output

    def test_list_services_with_status_filter(self, runner, mock_api):
        """Test listing services with status filter"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'services': [
                {
                    'id': 'service1',
                    'name': 'Service 1',
                    'version': '1.0.0',
                    'status': 'active',
                    'capabilities': ['cap1'],
                    'location': 'http://localhost:3001'
                }
            ],
            'count': 1
        }
        mock_api.get.return_value = mock_response

        result = runner.invoke(cli, ['list', '--status', 'active'])

        assert result.exit_code == 0
        mock_api.get.assert_called_once()
        call_args = mock_api.get.call_args[0][0]
        assert 'status=active' in call_args


class TestInfoCommand:
    """Test the info command"""

    def test_info_command(self, runner, mock_api):
        """Test getting service info"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'id': 'test-service',
            'name': 'Test Service',
            'version': '1.0.0',
            'status': 'active',
            'mode': 'http',
            'location': 'http://localhost:3000',
            'capabilities': ['cap1', 'cap2'],
            'registered_at': '2024-01-01T00:00:00',
            'last_seen': '2024-01-01T01:00:00'
        }
        mock_api.get.return_value = mock_response

        result = runner.invoke(cli, ['info', 'test-service'])

        assert result.exit_code == 0
        assert 'Test Service' in result.output
        assert 'test-service' in result.output
        assert 'cap1' in result.output
        assert 'cap2' in result.output

    def test_info_command_json(self, runner, mock_api):
        """Test getting service info in JSON format"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'id': 'test-service',
            'name': 'Test Service',
            'version': '1.0.0',
            'status': 'active',
            'mode': 'http',
            'location': 'http://localhost:3000',
            'capabilities': ['cap1'],
            'registered_at': '2024-01-01T00:00:00',
            'last_seen': '2024-01-01T01:00:00'
        }
        mock_api.get.return_value = mock_response

        result = runner.invoke(cli, ['info', 'test-service', '--format', 'json'])

        assert result.exit_code == 0


class TestCapabilitiesCommand:
    """Test the capabilities command"""

    def test_capabilities_command(self, runner, mock_api):
        """Test listing capabilities"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'capabilities': [
                {
                    'capability': 'cap1',
                    'providers': ['service1', 'service2'],
                    'count': 2
                },
                {
                    'capability': 'cap2',
                    'providers': ['service3'],
                    'count': 1
                }
            ],
            'count': 2
        }
        mock_api.get.return_value = mock_response

        result = runner.invoke(cli, ['capabilities'])

        assert result.exit_code == 0
        assert 'cap1' in result.output
        assert 'cap2' in result.output

    def test_capabilities_command_json(self, runner, mock_api):
        """Test listing capabilities in JSON format"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'capabilities': [
                {
                    'capability': 'cap1',
                    'providers': ['service1'],
                    'count': 1
                }
            ],
            'count': 1
        }
        mock_api.get.return_value = mock_response

        result = runner.invoke(cli, ['capabilities', '--format', 'json'])

        assert result.exit_code == 0
        assert 'cap1' in result.output


class TestFindCommand:
    """Test the find command"""

    def test_find_capability_success(self, runner, mock_api):
        """Test finding a capability successfully"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'id': 'service1',
            'name': 'Service 1',
            'location': 'http://localhost:3000',
            'status': 'active'
        }
        mock_api.get.return_value = mock_response

        result = runner.invoke(cli, ['find', 'test-cap'])

        assert result.exit_code == 0
        assert 'Service 1' in result.output
        assert 'service1' in result.output

    def test_find_capability_not_found(self, runner, mock_api):
        """Test finding a non-existent capability"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("Not found")
        mock_api.get.return_value = mock_response

        result = runner.invoke(cli, ['find', 'nonexistent-cap'])

        assert result.exit_code == 1
        assert 'No active services' in result.output


class TestUnregisterCommand:
    """Test the unregister command"""

    def test_unregister_command_confirmed(self, runner, mock_api):
        """Test unregistering a service with confirmation"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'message': 'Service unregistered successfully'
        }
        mock_api.delete.return_value = mock_response

        result = runner.invoke(cli, ['unregister', 'test-service'], input='y\n')

        assert result.exit_code == 0
        assert 'Service unregistered successfully' in result.output

    def test_unregister_command_cancelled(self, runner, mock_api):
        """Test cancelling service unregistration"""
        result = runner.invoke(cli, ['unregister', 'test-service'], input='n\n')

        assert result.exit_code == 0
        # Should not call API when cancelled
        mock_api.delete.assert_not_called()


class TestInitCommand:
    """Test the init command"""

    def test_init_python_app(self, runner):
        """Test initializing a Python application"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(cli, [
                'init',
                'test-app',
                'Test App',
                '--runtime', 'python',
                '--path', tmpdir
            ])

            assert result.exit_code == 0
            assert 'Created new python application' in result.output

            app_path = Path(tmpdir) / 'test-app'
            assert app_path.exists()
            assert (app_path / 'app.manifest.json').exists()
            assert (app_path / 'config.defaults.json').exists()
            assert (app_path / 'src' / 'module.py').exists()
            assert (app_path / 'src' / 'standalone.py').exists()
            assert (app_path / 'adapters').exists()

    def test_init_javascript_app(self, runner):
        """Test initializing a JavaScript application"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(cli, [
                'init',
                'test-app',
                'Test App',
                '--runtime', 'javascript',
                '--path', tmpdir
            ])

            assert result.exit_code == 0

            app_path = Path(tmpdir) / 'test-app'
            assert (app_path / 'src' / 'module.js').exists()
            assert (app_path / 'src' / 'standalone.js').exists()

    def test_init_existing_directory(self, runner):
        """Test initializing in an existing directory fails"""
        with tempfile.TemporaryDirectory() as tmpdir:
            app_path = Path(tmpdir) / 'test-app'
            app_path.mkdir()

            result = runner.invoke(cli, [
                'init',
                'test-app',
                'Test App',
                '--path', tmpdir
            ])

            assert result.exit_code == 1
            assert 'already exists' in result.output


class TestValidateCommand:
    """Test the validate command"""

    def test_validate_valid_manifest(self, runner):
        """Test validating a valid manifest"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / 'app.manifest.json'
            manifest = {
                'id': 'test-app',
                'name': 'Test App',
                'version': '1.0.0',
                'runtime': 'python',
                'provides': {'capabilities': []},
                'interfaces': {'http': {'port': 3000}}
            }

            with open(manifest_path, 'w') as f:
                json.dump(manifest, f)

            result = runner.invoke(cli, ['validate', str(manifest_path)])

            assert result.exit_code == 0
            assert 'Manifest is valid' in result.output

    def test_validate_invalid_manifest(self, runner):
        """Test validating an invalid manifest"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / 'app.manifest.json'
            manifest = {
                'id': 'test-app',
                'name': 'Test App'
                # Missing required fields
            }

            with open(manifest_path, 'w') as f:
                json.dump(manifest, f)

            result = runner.invoke(cli, ['validate', str(manifest_path)])

            assert result.exit_code == 1
            assert 'Missing required fields' in result.output

    def test_validate_nonexistent_file(self, runner):
        """Test validating a non-existent file"""
        result = runner.invoke(cli, ['validate', '/nonexistent/manifest.json'])

        assert result.exit_code == 1
        assert 'Manifest not found' in result.output

    def test_validate_invalid_json(self, runner):
        """Test validating invalid JSON"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / 'app.manifest.json'
            with open(manifest_path, 'w') as f:
                f.write('{ invalid json }')

            result = runner.invoke(cli, ['validate', str(manifest_path)])

            assert result.exit_code == 1
            assert 'Invalid JSON' in result.output


class TestRunCommand:
    """Test the run command"""

    def test_run_python_app(self, runner):
        """Test running a Python application"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / 'app.manifest.json'
            manifest = {
                'id': 'test-app',
                'name': 'Test App',
                'runtime': 'python'
            }

            with open(manifest_path, 'w') as f:
                json.dump(manifest, f)

            # Create dummy standalone script
            src_dir = Path(tmpdir) / 'src'
            src_dir.mkdir()
            standalone_script = src_dir / 'standalone.py'
            standalone_script.write_text('print("Running")')

            with patch('modularity_cli.cli.subprocess.run') as mock_run:
                result = runner.invoke(cli, ['run', '--manifest', str(manifest_path)])

                # Check that subprocess.run was called
                mock_run.assert_called_once()

    def test_run_nonexistent_manifest(self, runner):
        """Test running with non-existent manifest"""
        result = runner.invoke(cli, ['run', '--manifest', '/nonexistent/manifest.json'])

        assert result.exit_code == 1
        assert 'Manifest not found' in result.output


class TestUtilityFunctions:
    """Test utility functions"""

    def test_get_extension(self):
        """Test getting file extensions for runtimes"""
        assert _get_extension('python') == 'py'
        assert _get_extension('javascript') == 'js'
        assert _get_extension('go') == 'go'
        assert _get_extension('ruby') == 'rb'
        assert _get_extension('unknown') == 'txt'

    def test_create_template_files_python(self):
        """Test creating Python template files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            app_path = Path(tmpdir)
            (app_path / "src").mkdir()

            _create_template_files(app_path, 'python')

            assert (app_path / "src" / "module.py").exists()
            assert (app_path / "src" / "standalone.py").exists()

            # Check content
            module_content = (app_path / "src" / "module.py").read_text()
            assert 'class AppModule' in module_content
            assert 'ModuleInterface' in module_content

    def test_create_template_files_javascript(self):
        """Test creating JavaScript template files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            app_path = Path(tmpdir)
            (app_path / "src").mkdir()

            _create_template_files(app_path, 'javascript')

            assert (app_path / "src" / "module.js").exists()
            assert (app_path / "src" / "standalone.js").exists()

            # Check content
            module_content = (app_path / "src" / "module.js").read_text()
            assert 'class AppModule' in module_content


class TestCLIOptions:
    """Test CLI global options"""

    def test_custom_registry_option(self, runner, mock_api):
        """Test using custom registry URL"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'total_services': 0,
            'active_services': 0,
            'inactive_services': 0,
            'total_capabilities': 0,
            'services_by_runtime': {}
        }
        mock_api.get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "cli-config.json"
            with patch('modularity_cli.cli.CONFIG_FILE', config_file):
                result = runner.invoke(cli, ['--registry', 'http://custom:5000', 'status'])

                assert result.exit_code == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
