#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Building claudex-sandbox image..."
docker build -t claudex-sandbox:latest .

echo "Creating docker network (if not exists)..."
docker network create claudex-sandbox-net 2>/dev/null || true

echo "Done! Image built: claudex-sandbox:latest"
echo ""
echo "To test the image, run:"
echo "  docker run -it --rm claudex-sandbox:latest"
