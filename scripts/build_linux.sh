#!/bin/bash
# Build standalone Linux application for Open PDF Creator
#
# This creates either:
# 1. A PyInstaller bundle (portable)
# 2. A Snap package (for distribution)
#
# Usage:
#   ./build_linux.sh          # Build PyInstaller bundle
#   ./build_linux.sh snap     # Build Snap package

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Open PDF Creator - Linux Build${NC}"
echo -e "${GREEN}============================================${NC}"

BUILD_TYPE="${1:-pyinstaller}"

if [ "$BUILD_TYPE" = "snap" ]; then
    # Build Snap package
    echo ""
    echo "Building Snap package..."

    # Check if snapcraft is installed
    if ! command -v snapcraft &> /dev/null; then
        echo "Installing snapcraft..."
        sudo snap install snapcraft --classic
    fi

    # Build snap
    cd installer/linux/snap
    snapcraft

    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}Snap build complete!${NC}"
    echo "Install with: sudo snap install open-pdf-creator_*.snap --dangerous"
    echo -e "${GREEN}============================================${NC}"

else
    # Build PyInstaller bundle
    echo ""
    echo "Building PyInstaller bundle..."

    # Create/activate virtual environment
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi

    source venv/bin/activate

    # Install dependencies
    echo "Installing dependencies..."
    pip install -e ".[dev]" pyinstaller

    # Build with PyInstaller
    echo "Building standalone application..."
    pyinstaller open_pdf_creator.spec --clean

    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}Build complete!${NC}"
    echo "Output: dist/OpenPDFCreator/"
    echo ""
    echo "To run: ./dist/OpenPDFCreator/OpenPDFCreator"
    echo -e "${GREEN}============================================${NC}"
fi
