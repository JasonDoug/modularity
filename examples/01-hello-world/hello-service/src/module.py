"""
Hello World Service - Module Implementation
Demonstrates the minimal ModuleInterface implementation
"""

import sys
import os
from pathlib import Path

# Add the SDK to Python path (monorepo structure)
sdk_path = Path(__file__).parent.parent.parent.parent.parent / "packages" / "sdk-python"
sys.path.insert(0, str(sdk_path))

from ecosystem_sdk import ModuleInterface


class HelloModule(ModuleInterface):
    """
    Simplest possible module implementation.
    Provides one capability: greet
    """

    def initialize(self, config):
        """
        Called when module is loaded.
        Store configuration for later use.
        """
        self.config = config
        self.greeting = config.get('default_greeting', 'Hello')
        self.name = config.get('default_name', 'World')

        print(f"HelloModule initialized with greeting: '{self.greeting}'")
        return True

    def get_capabilities(self):
        """
        Return the list of capabilities this module provides.
        """
        return ['greet']

    def invoke(self, capability, params):
        """
        Execute a capability with given parameters.

        Args:
            capability: The capability to invoke (e.g., 'greet')
            params: Dictionary of parameters

        Returns:
            Dictionary with the result
        """
        if capability == 'greet':
            # Get name from params, or use default
            name = params.get('name', self.name)
            greeting = params.get('greeting', self.greeting)

            # Return the greeting message
            return {
                'message': f"{greeting}, {name}!",
                'timestamp': self._get_timestamp()
            }

        # Unknown capability
        raise ValueError(f"Unknown capability: {capability}")

    def handle_event(self, event, data):
        """
        Handle events from other modules.
        Not used in this simple example.
        """
        print(f"Received event: {event} with data: {data}")

    def shutdown(self):
        """
        Cleanup before shutdown.
        """
        print("HelloModule shutting down")

    def _get_timestamp(self):
        """Helper method to get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
