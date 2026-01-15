#!/usr/bin/python3
"""Debug wrapper for CUPS backend."""

import sys
import os
import traceback

# Log file
LOG_FILE = "/tmp/open-pdf-creator-debug.log"

def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"{msg}\n")

try:
    log(f"=== Backend called ===")
    log(f"Arguments: {sys.argv}")
    log(f"UID: {os.getuid()}, EUID: {os.geteuid()}")
    log(f"CWD: {os.getcwd()}")
    log(f"PATH: {os.environ.get('PATH', 'NOT SET')}")

    # Import the actual backend
    sys.path.insert(0, "/home/maarten/Documents/GitHub/open-pdf-creator/src")

    from open_pdf_creator.printer.linux import cups_backend

    log("Import successful")

    # Run main
    result = cups_backend.main()
    log(f"Result: {result}")
    sys.exit(result)

except Exception as e:
    log(f"ERROR: {e}")
    log(traceback.format_exc())
    sys.exit(1)
