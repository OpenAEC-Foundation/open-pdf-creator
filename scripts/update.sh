#!/bin/bash
# Update Open PDF Creator
#
# Usage: ./scripts/update.sh
#        sudo ./scripts/update.sh  (om ook de CUPS backend te updaten)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Open PDF Creator - Update${NC}"
echo "=========================="

# 1. Git pull (als het een git repo is)
if [ -d ".git" ]; then
    echo ""
    echo "Pulling latest changes..."
    git pull || echo -e "${YELLOW}Warning: git pull failed (offline or no remote?)${NC}"
fi

# 2. Update Python dependencies
echo ""
echo "Updating Python dependencies..."
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install -e . --quiet
    echo -e "${GREEN}✓ Python packages updated${NC}"
else
    echo -e "${YELLOW}Warning: No venv found. Run: python3 -m venv venv && pip install -e .${NC}"
fi

# 3. Update CUPS backend (requires root)
echo ""
if [ "$EUID" -eq 0 ]; then
    echo "Updating CUPS backend..."
    cp "$PROJECT_DIR/src/open_pdf_creator/printer/linux/cups_backend.py" /usr/lib/cups/backend/open-pdf-creator
    chmod 755 /usr/lib/cups/backend/open-pdf-creator
    chown root:root /usr/lib/cups/backend/open-pdf-creator
    echo -e "${GREEN}✓ CUPS backend updated${NC}"
else
    echo -e "${YELLOW}⚠ Run with sudo to update CUPS backend${NC}"
    echo "  sudo $0"
fi

# 4. Kill running instance
echo ""
echo "Stopping running instances..."
pkill -f "open_pdf_creator" 2>/dev/null && echo -e "${GREEN}✓ Stopped running instance${NC}" || echo "No running instance found"

# 5. Done
echo ""
echo "=========================="
echo -e "${GREEN}Update complete!${NC}"
echo ""
echo "Start the application with:"
echo "  cd $PROJECT_DIR"
echo "  source venv/bin/activate"
echo "  open-pdf-creator"
