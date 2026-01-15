#!/bin/bash
# Uninstall Open PDF Creator printer on Linux
#
# Usage: sudo ./uninstall_printer.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}Open PDF Creator - Printer Uninstallation${NC}"
echo "============================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
    exit 1
fi

PRINTER_NAME="Open-PDF-Creator"
BACKEND_NAME="open-pdf-creator"
CUPS_BACKEND_DIR="/usr/lib/cups/backend"

echo ""
echo "Removing printer..."

# Remove printer
if lpstat -p "$PRINTER_NAME" &>/dev/null; then
    lpadmin -x "$PRINTER_NAME"
    echo -e "${GREEN}✓ Printer removed: $PRINTER_NAME${NC}"
else
    echo "Printer not found (already removed)"
fi

echo ""
echo "Removing CUPS backend..."

# Remove backend
BACKEND_PATH="$CUPS_BACKEND_DIR/$BACKEND_NAME"
if [ -f "$BACKEND_PATH" ]; then
    rm -f "$BACKEND_PATH"
    echo -e "${GREEN}✓ Backend removed: $BACKEND_PATH${NC}"
else
    echo "Backend not found (already removed)"
fi

echo ""
echo "============================================"
echo -e "${GREEN}Uninstallation complete!${NC}"
