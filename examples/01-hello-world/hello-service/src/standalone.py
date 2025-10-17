"""
Hello World Service - Standalone Mode
Runs the service as an independent HTTP server
"""

import sys
import os
from pathlib import Path

# Add the SDK to Python path (monorepo structure)
sdk_path = Path(__file__).parent.parent.parent.parent.parent / "packages" / "sdk-python"
sys.path.insert(0, str(sdk_path))

from modularity_sdk import ModularitySDK


if __name__ == "__main__":
    # Load the SDK with our manifest
    manifest_path = Path(__file__).parent.parent / "app.manifest.json"
    sdk = ModularitySDK(str(manifest_path))

    # Run in standalone mode (starts HTTP server)
    print("=" * 50)
    print("Starting Hello Service...")
    print("=" * 50)
    print("Try: curl http://localhost:3100/_module/invoke \\")
    print("       -H 'Content-Type: application/json' \\")
    print("       -d '{\"capability\": \"greet\", \"params\": {\"name\": \"Alice\"}}'")
    print()
    print("Health check: curl http://localhost:3100/_module/health")
    print("Capabilities: curl http://localhost:3100/_module/capabilities")
    print("=" * 50)
    print()

    # Get host and port from environment or use defaults
    host = os.getenv('MODULE_HOST', '127.0.0.1')
    port = int(os.getenv('MODULE_PORT', '3100'))

    sdk.run_standalone(host=host, port=port)
