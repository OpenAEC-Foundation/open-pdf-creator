#!/bin/bash
# Install Open PDF Creator printer on Linux
#
# This script:
# 1. Installs the CUPS backend
# 2. Creates the virtual printer
#
# Usage: sudo ./install_printer.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Open PDF Creator - Printer Installation${NC}"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
    exit 1
fi

# Check if CUPS is installed
if ! command -v lpadmin &> /dev/null; then
    echo -e "${RED}Error: CUPS is not installed${NC}"
    echo "Install with: sudo apt install cups"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER="${SUDO_USER:-$USER}"
ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)

# Paths
CUPS_BACKEND_DIR="/usr/lib/cups/backend"
BACKEND_NAME="open-pdf-creator"
BACKEND_SOURCE="$PROJECT_DIR/src/open_pdf_creator/printer/linux/cups_backend.py"
BACKEND_DEST="$CUPS_BACKEND_DIR/$BACKEND_NAME"

# Printer settings
PRINTER_NAME="Open-PDF-Creator"
PRINTER_DESC="Open PDF Creator - Virtual PDF Printer"
DEVICE_URI="$BACKEND_NAME:/"

echo ""
echo "Installing CUPS backend..."

# Copy backend script
if [ -f "$BACKEND_SOURCE" ]; then
    cp "$BACKEND_SOURCE" "$BACKEND_DEST"
    chown root:root "$BACKEND_DEST"
    chmod 755 "$BACKEND_DEST"
    echo -e "${GREEN}✓ Backend installed: $BACKEND_DEST${NC}"
else
    echo -e "${RED}Error: Backend source not found: $BACKEND_SOURCE${NC}"
    exit 1
fi

echo ""
echo "Creating PPD file..."

# Create PPD file
PPD_FILE="/tmp/open-pdf-creator.ppd"
cat > "$PPD_FILE" << 'EOF'
*PPD-Adobe: "4.3"
*FormatVersion: "4.3"
*FileVersion: "1.0"
*LanguageVersion: English
*LanguageEncoding: ISOLatin1
*PCFileName: "OPENPDF.PPD"
*Manufacturer: "OpenAEC"
*Product: "(Open PDF Creator)"
*ModelName: "Open PDF Creator"
*ShortNickName: "Open PDF Creator"
*NickName: "Open PDF Creator Virtual Printer"
*PSVersion: "(3010) 0"
*LanguageLevel: "3"
*ColorDevice: True
*DefaultColorSpace: RGB
*FileSystem: False
*Throughput: "1"
*TTRasterizer: Type42

*OpenUI *PageSize/Media Size: PickOne
*OrderDependency: 10 AnySetup *PageSize
*DefaultPageSize: A4
*PageSize A4/A4: "<</PageSize[595 842]/ImagingBBox null>>setpagedevice"
*PageSize Letter/Letter: "<</PageSize[612 792]/ImagingBBox null>>setpagedevice"
*PageSize Legal/Legal: "<</PageSize[612 1008]/ImagingBBox null>>setpagedevice"
*PageSize A3/A3: "<</PageSize[842 1191]/ImagingBBox null>>setpagedevice"
*PageSize A5/A5: "<</PageSize[420 595]/ImagingBBox null>>setpagedevice"
*CloseUI: *PageSize

*OpenUI *PageRegion: PickOne
*OrderDependency: 10 AnySetup *PageRegion
*DefaultPageRegion: A4
*PageRegion A4/A4: "<</PageSize[595 842]/ImagingBBox null>>setpagedevice"
*PageRegion Letter/Letter: "<</PageSize[612 792]/ImagingBBox null>>setpagedevice"
*PageRegion Legal/Legal: "<</PageSize[612 1008]/ImagingBBox null>>setpagedevice"
*PageRegion A3/A3: "<</PageSize[842 1191]/ImagingBBox null>>setpagedevice"
*PageRegion A5/A5: "<</PageSize[420 595]/ImagingBBox null>>setpagedevice"
*CloseUI: *PageRegion

*DefaultImageableArea: A4
*ImageableArea A4/A4: "0 0 595 842"
*ImageableArea Letter/Letter: "0 0 612 792"
*ImageableArea Legal/Legal: "0 0 612 1008"
*ImageableArea A3/A3: "0 0 842 1191"
*ImageableArea A5/A5: "0 0 420 595"

*DefaultPaperDimension: A4
*PaperDimension A4/A4: "595 842"
*PaperDimension Letter/Letter: "612 792"
*PaperDimension Legal/Legal: "612 1008"
*PaperDimension A3/A3: "842 1191"
*PaperDimension A5/A5: "420 595"

*OpenUI *Resolution/Resolution: PickOne
*OrderDependency: 20 AnySetup *Resolution
*DefaultResolution: 600dpi
*Resolution 150dpi/150 DPI: "<</HWResolution[150 150]>>setpagedevice"
*Resolution 300dpi/300 DPI: "<</HWResolution[300 300]>>setpagedevice"
*Resolution 600dpi/600 DPI: "<</HWResolution[600 600]>>setpagedevice"
*CloseUI: *Resolution

*DefaultFont: Courier
*Font Courier: Standard "(001.000)" Standard ROM
*Font Helvetica: Standard "(001.000)" Standard ROM
*Font Times-Roman: Standard "(001.000)" Standard ROM
EOF

echo -e "${GREEN}✓ PPD file created${NC}"

echo ""
echo "Installing printer..."

# Remove existing printer if present
lpadmin -x "$PRINTER_NAME" 2>/dev/null || true

# Install printer
lpadmin -p "$PRINTER_NAME" -E -v "$DEVICE_URI" -P "$PPD_FILE" -D "$PRINTER_DESC" -L "Virtual" -o printer-is-shared=false

# Accept jobs and enable printer
cupsaccept "$PRINTER_NAME"
cupsenable "$PRINTER_NAME"

# Cleanup
rm -f "$PPD_FILE"

echo -e "${GREEN}✓ Printer installed: $PRINTER_NAME${NC}"

echo ""
echo "Creating spool directory..."

# Create spool directory with correct permissions
SPOOL_DIR="$ACTUAL_HOME/.local/share/open-pdf-creator/spool"
mkdir -p "$SPOOL_DIR"
chown -R "$ACTUAL_USER:$ACTUAL_USER" "$ACTUAL_HOME/.local/share/open-pdf-creator"
chmod 755 "$SPOOL_DIR"

echo -e "${GREEN}✓ Spool directory created: $SPOOL_DIR${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "The printer '$PRINTER_NAME' is now available."
echo ""
echo "To test:"
echo "  1. Start the application: open-pdf-creator"
echo "  2. Print from any application to '$PRINTER_NAME'"
echo ""
echo "To uninstall:"
echo "  sudo ./uninstall_printer.sh"
