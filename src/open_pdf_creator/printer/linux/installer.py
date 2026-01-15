#!/usr/bin/env python3
"""Linux printer installer for Open PDF Creator.

This module handles the installation and removal of the
Open PDF Creator virtual printer on Linux systems using CUPS.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Configuration
PRINTER_NAME = "Open-PDF-Creator"
PRINTER_DESCRIPTION = "Open PDF Creator - Virtual PDF Printer"
PRINTER_LOCATION = "Virtual"
BACKEND_NAME = "open-pdf-creator"
DEVICE_URI = f"{BACKEND_NAME}:/"

# Paths
CUPS_BACKEND_DIR = Path("/usr/lib/cups/backend")
CUPS_PPD_DIR = Path("/etc/cups/ppd")


def check_root() -> bool:
    """Check if running as root."""
    return os.geteuid() == 0


def check_cups_installed() -> bool:
    """Check if CUPS is installed."""
    return shutil.which("lpadmin") is not None


def get_backend_source() -> Path:
    """Get the path to the CUPS backend script."""
    # Try different locations
    locations = [
        Path(__file__).parent / "cups_backend.py",
        Path(sys.prefix) / "lib" / "open_pdf_creator" / "cups_backend.py",
        Path("/usr/share/open-pdf-creator/cups_backend.py"),
    ]

    for loc in locations:
        if loc.exists():
            return loc

    # Fallback: use the module path
    import open_pdf_creator.printer.linux.cups_backend as backend_module
    return Path(backend_module.__file__)


def install_backend() -> bool:
    """Install the CUPS backend script.

    Returns:
        True if successful, False otherwise
    """
    if not check_root():
        print("Error: Root privileges required to install backend")
        return False

    backend_source = get_backend_source()
    backend_dest = CUPS_BACKEND_DIR / BACKEND_NAME

    try:
        # Copy backend script
        shutil.copy(backend_source, backend_dest)

        # Set permissions (must be owned by root and executable)
        os.chown(backend_dest, 0, 0)  # root:root
        os.chmod(backend_dest, 0o755)  # rwxr-xr-x

        print(f"Installed backend: {backend_dest}")
        return True

    except OSError as e:
        print(f"Error installing backend: {e}")
        return False


def uninstall_backend() -> bool:
    """Remove the CUPS backend script.

    Returns:
        True if successful, False otherwise
    """
    if not check_root():
        print("Error: Root privileges required to uninstall backend")
        return False

    backend_path = CUPS_BACKEND_DIR / BACKEND_NAME

    try:
        if backend_path.exists():
            backend_path.unlink()
            print(f"Removed backend: {backend_path}")
        return True

    except OSError as e:
        print(f"Error removing backend: {e}")
        return False


def create_ppd() -> str:
    """Create a minimal PPD file for the printer.

    Returns:
        PPD file content as string
    """
    return """*PPD-Adobe: "4.3"
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
*PageSize B5/B5: "<</PageSize[516 729]/ImagingBBox null>>setpagedevice"
*PageSize Tabloid/Tabloid: "<</PageSize[792 1224]/ImagingBBox null>>setpagedevice"
*CloseUI: *PageSize

*OpenUI *PageRegion: PickOne
*OrderDependency: 10 AnySetup *PageRegion
*DefaultPageRegion: A4
*PageRegion A4/A4: "<</PageSize[595 842]/ImagingBBox null>>setpagedevice"
*PageRegion Letter/Letter: "<</PageSize[612 792]/ImagingBBox null>>setpagedevice"
*PageRegion Legal/Legal: "<</PageSize[612 1008]/ImagingBBox null>>setpagedevice"
*PageRegion A3/A3: "<</PageSize[842 1191]/ImagingBBox null>>setpagedevice"
*PageRegion A5/A5: "<</PageSize[420 595]/ImagingBBox null>>setpagedevice"
*PageRegion B5/B5: "<</PageSize[516 729]/ImagingBBox null>>setpagedevice"
*PageRegion Tabloid/Tabloid: "<</PageSize[792 1224]/ImagingBBox null>>setpagedevice"
*CloseUI: *PageRegion

*DefaultImageableArea: A4
*ImageableArea A4/A4: "0 0 595 842"
*ImageableArea Letter/Letter: "0 0 612 792"
*ImageableArea Legal/Legal: "0 0 612 1008"
*ImageableArea A3/A3: "0 0 842 1191"
*ImageableArea A5/A5: "0 0 420 595"
*ImageableArea B5/B5: "0 0 516 729"
*ImageableArea Tabloid/Tabloid: "0 0 792 1224"

*DefaultPaperDimension: A4
*PaperDimension A4/A4: "595 842"
*PaperDimension Letter/Letter: "612 792"
*PaperDimension Legal/Legal: "612 1008"
*PaperDimension A3/A3: "842 1191"
*PaperDimension A5/A5: "420 595"
*PaperDimension B5/B5: "516 729"
*PaperDimension Tabloid/Tabloid: "792 1224"

*OpenUI *Resolution/Resolution: PickOne
*OrderDependency: 20 AnySetup *Resolution
*DefaultResolution: 600dpi
*Resolution 150dpi/150 DPI: "<</HWResolution[150 150]>>setpagedevice"
*Resolution 300dpi/300 DPI: "<</HWResolution[300 300]>>setpagedevice"
*Resolution 600dpi/600 DPI: "<</HWResolution[600 600]>>setpagedevice"
*Resolution 1200dpi/1200 DPI: "<</HWResolution[1200 1200]>>setpagedevice"
*CloseUI: *Resolution

*DefaultFont: Courier
*Font Courier: Standard "(001.000)" Standard ROM
*Font Courier-Bold: Standard "(001.000)" Standard ROM
*Font Courier-BoldOblique: Standard "(001.000)" Standard ROM
*Font Courier-Oblique: Standard "(001.000)" Standard ROM
*Font Helvetica: Standard "(001.000)" Standard ROM
*Font Helvetica-Bold: Standard "(001.000)" Standard ROM
*Font Helvetica-BoldOblique: Standard "(001.000)" Standard ROM
*Font Helvetica-Oblique: Standard "(001.000)" Standard ROM
*Font Times-Bold: Standard "(001.000)" Standard ROM
*Font Times-BoldItalic: Standard "(001.000)" Standard ROM
*Font Times-Italic: Standard "(001.000)" Standard ROM
*Font Times-Roman: Standard "(001.000)" Standard ROM
"""


def install_printer() -> bool:
    """Install the virtual printer in CUPS.

    Returns:
        True if successful, False otherwise
    """
    if not check_cups_installed():
        print("Error: CUPS is not installed")
        return False

    # Install backend first
    if check_root():
        if not install_backend():
            return False
    else:
        print("Warning: Cannot install backend without root privileges")
        print("The printer will be installed but may not work until backend is installed")

    # Create PPD file
    ppd_content = create_ppd()
    ppd_path = Path("/tmp/open-pdf-creator.ppd")

    try:
        with open(ppd_path, "w") as f:
            f.write(ppd_content)

        # Install printer using lpadmin
        cmd = [
            "lpadmin",
            "-p", PRINTER_NAME,
            "-E",  # Enable printer
            "-v", DEVICE_URI,
            "-P", str(ppd_path),
            "-D", PRINTER_DESCRIPTION,
            "-L", PRINTER_LOCATION,
            "-o", "printer-is-shared=false",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Error installing printer: {result.stderr}")
            return False

        # Accept jobs
        subprocess.run(["cupsaccept", PRINTER_NAME], capture_output=True)

        # Enable printer
        subprocess.run(["cupsenable", PRINTER_NAME], capture_output=True)

        print(f"Installed printer: {PRINTER_NAME}")
        return True

    except Exception as e:
        print(f"Error installing printer: {e}")
        return False

    finally:
        # Cleanup temp PPD
        if ppd_path.exists():
            ppd_path.unlink()


def uninstall_printer() -> bool:
    """Remove the virtual printer from CUPS.

    Returns:
        True if successful, False otherwise
    """
    if not check_cups_installed():
        print("Error: CUPS is not installed")
        return False

    try:
        # Remove printer
        result = subprocess.run(
            ["lpadmin", "-x", PRINTER_NAME],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0 and "does not exist" not in result.stderr:
            print(f"Error removing printer: {result.stderr}")
            return False

        print(f"Removed printer: {PRINTER_NAME}")

        # Remove backend if root
        if check_root():
            uninstall_backend()

        return True

    except Exception as e:
        print(f"Error removing printer: {e}")
        return False


def is_printer_installed() -> bool:
    """Check if the printer is installed.

    Returns:
        True if installed, False otherwise
    """
    try:
        result = subprocess.run(
            ["lpstat", "-p", PRINTER_NAME],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def main() -> int:
    """Main entry point for installer."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Open PDF Creator printer installer"
    )
    parser.add_argument(
        "action",
        choices=["install", "uninstall", "status"],
        help="Action to perform",
    )

    args = parser.parse_args()

    if args.action == "install":
        success = install_printer()
        return 0 if success else 1

    elif args.action == "uninstall":
        success = uninstall_printer()
        return 0 if success else 1

    elif args.action == "status":
        if is_printer_installed():
            print(f"Printer '{PRINTER_NAME}' is installed")
            return 0
        else:
            print(f"Printer '{PRINTER_NAME}' is not installed")
            return 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
