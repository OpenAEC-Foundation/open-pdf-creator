#!/bin/bash
# Build Snap package for Open PDF Creator

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

cd "$PROJECT_DIR"

echo "Building Open PDF Creator Snap..."
echo "================================="

# Check if snapcraft is installed
if ! command -v snapcraft &> /dev/null; then
    echo "snapcraft not found. Installing..."
    sudo snap install snapcraft --classic
fi

# Copy snapcraft.yaml to project root
cp installer/linux/snap/snapcraft.yaml .

# Build the snap
snapcraft

# Move result
mkdir -p dist
mv *.snap dist/ 2>/dev/null || true

echo ""
echo "Build complete!"
echo "Snap package: dist/open-pdf-creator_*.snap"
echo ""
echo "To install locally:"
echo "  sudo snap install dist/open-pdf-creator_*.snap --dangerous"
