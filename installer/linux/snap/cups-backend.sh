#!/bin/bash
# CUPS backend wrapper for Snap
# This script is called by CUPS when printing to Open PDF Creator

exec "$SNAP/bin/python3" "$SNAP/lib/python3.12/site-packages/open_pdf_creator/printer/linux/cups_backend.py" "$@"
