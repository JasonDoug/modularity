"""
Simple test for Hello Service
"""

import sys
from pathlib import Path

# Add the SDK to Python path (monorepo structure)
sdk_path = Path(__file__).parent.parent.parent.parent / "packages" / "sdk-python"
sys.path.insert(0, str(sdk_path))

from modularity_sdk import ModularitySDK


def test_hello_module():
    """Test the hello module works"""

    # Load as module
    manifest_path = Path(__file__).parent / "app.manifest.json"
    sdk = ModularitySDK(str(manifest_path))
    hello = sdk.load_as_module({'default_greeting': 'Hi'})

    # Test capabilities
    capabilities = hello.get_capabilities()
    assert 'greet' in capabilities, f"Expected 'greet' in capabilities, got {capabilities}"
    print("✓ Capability 'greet' found")

    # Test greet with default
    result = hello.invoke('greet', {})
    assert 'message' in result, f"Expected 'message' in result, got {result}"
    assert 'Hi, World!' in result['message'], f"Expected 'Hi, World!' in message, got {result['message']}"
    print(f"✓ Default greeting works: {result['message']}")

    # Test greet with name
    result = hello.invoke('greet', {'name': 'Alice'})
    assert 'Hi, Alice!' in result['message'], f"Expected 'Hi, Alice!' in message, got {result['message']}"
    print(f"✓ Custom name works: {result['message']}")

    # Test custom greeting
    result = hello.invoke('greet', {'name': 'Bob', 'greeting': 'Hello'})
    assert 'Hello, Bob!' in result['message'], f"Expected 'Hello, Bob!' in message, got {result['message']}"
    print(f"✓ Custom greeting works: {result['message']}")

    # Test timestamp is present
    assert 'timestamp' in result, f"Expected 'timestamp' in result, got {result}"
    print(f"✓ Timestamp present: {result['timestamp']}")

    # Test unknown capability raises error
    try:
        hello.invoke('unknown', {})
        assert False, "Expected ValueError for unknown capability"
    except ValueError as e:
        assert 'Unknown capability' in str(e)
        print(f"✓ Unknown capability properly rejected: {e}")

    print()
    print("=" * 50)
    print("✓ All tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    test_hello_module()
