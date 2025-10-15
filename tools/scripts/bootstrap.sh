#!/bin/bash
# Bootstrap script for new developers

echo "Bootstrapping development environment..."
make install
make dev-setup
echo "✓ Bootstrap complete!"
