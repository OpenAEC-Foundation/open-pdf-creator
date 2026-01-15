#!/usr/bin/env python3
"""Build script for Windows installer.

This script:
1. Creates a standalone executable using PyInstaller
2. Bundles with Ghostscript for PS to PDF conversion
3. Creates an Inno Setup installer

Requirements:
- PyInstaller: pip install pyinstaller
- Inno Setup: Download from https://jrsoftware.org/isinfo.php

Usage:
    python build.py
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent.parent
SRC_DIR = PROJECT_DIR / "src"
DIST_DIR = PROJECT_DIR / "dist"
BUILD_DIR = PROJECT_DIR / "build"

APP_NAME = "Open PDF Creator"
APP_VERSION = "1.0.0"
APP_PUBLISHER = "OpenAEC Foundation"
APP_URL = "https://github.com/OpenAEC-Foundation/open-pdf-creator"


def clean():
    """Clean build directories."""
    print("Cleaning build directories...")
    shutil.rmtree(DIST_DIR, ignore_errors=True)
    shutil.rmtree(BUILD_DIR, ignore_errors=True)


def build_exe():
    """Build executable with PyInstaller."""
    print("Building executable with PyInstaller...")

    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "OpenPDFCreator",
        "--windowed",  # No console window
        "--onedir",  # Create a directory with all files
        "--icon", str(SRC_DIR / "open_pdf_creator" / "gui" / "resources" / "icon.ico"),
        "--add-data", f"{SRC_DIR / 'open_pdf_creator' / 'gui' / 'resources'};open_pdf_creator/gui/resources",
        "--hidden-import", "PySide6.QtSvg",
        "--hidden-import", "PIL",
        "--collect-all", "pypdf",
        "--collect-all", "pikepdf",
        str(SRC_DIR / "open_pdf_creator" / "main.py"),
    ]

    subprocess.run(cmd, check=True, cwd=PROJECT_DIR)


def create_ico():
    """Create ICO file from PNG."""
    print("Creating ICO file...")
    try:
        from PIL import Image

        png_path = SRC_DIR / "open_pdf_creator" / "gui" / "resources" / "icon_128.png"
        ico_path = SRC_DIR / "open_pdf_creator" / "gui" / "resources" / "icon.ico"

        if png_path.exists():
            img = Image.open(png_path)
            img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)])
            print(f"Created {ico_path}")
    except ImportError:
        print("Pillow not available, skipping ICO creation")


def build_installer():
    """Build Inno Setup installer."""
    print("Building Inno Setup installer...")

    iscc_path = shutil.which("ISCC") or r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

    if not Path(iscc_path).exists():
        print(f"Inno Setup not found at {iscc_path}")
        print("Please install Inno Setup from https://jrsoftware.org/isinfo.php")
        return False

    iss_file = SCRIPT_DIR / "setup.iss"
    subprocess.run([iscc_path, str(iss_file)], check=True)
    return True


def main():
    """Main build process."""
    print(f"Building {APP_NAME} v{APP_VERSION}")
    print("=" * 50)

    # Check if on Windows
    if sys.platform != "win32":
        print("This script is intended for Windows.")
        print("For cross-compilation, use a Windows VM or CI/CD.")
        return 1

    clean()
    create_ico()
    build_exe()
    build_installer()

    print()
    print("=" * 50)
    print("Build complete!")
    print(f"Installer: {DIST_DIR / 'OpenPDFCreator-Setup.exe'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
