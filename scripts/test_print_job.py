#!/usr/bin/env python3
"""Test script to simulate a print job without going through CUPS.

Usage:
    python scripts/test_print_job.py [pdf_file]

This script:
1. Creates a test PDF (or uses provided file)
2. Copies it to the spool directory
3. Sends notification to GUI via socket
4. The GUI should show Save As dialog

Requirements:
- GUI must be running (open-pdf-creator)
"""

import json
import os
import shutil
import socket
import sys
from datetime import datetime
from pathlib import Path


def get_spool_dir() -> Path:
    """Get spool directory for current user."""
    import getpass
    username = getpass.getuser()
    return Path("/tmp") / "open-pdf-creator-spool" / username


def create_test_pdf(output_path: Path) -> None:
    """Create a simple test PDF."""
    # Minimal valid PDF content
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
   /Contents 4 0 R /Resources << >> >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 24 Tf
100 700 Td
(Test PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
306
%%EOF
"""
    with open(output_path, "wb") as f:
        f.write(pdf_content)


def send_to_gui(job_info: dict) -> bool:
    """Send job notification to GUI."""
    # Try Unix socket first
    unix_socket = "/tmp/open-pdf-creator.sock"
    if os.path.exists(unix_socket):
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.connect(unix_socket)
                sock.sendall(json.dumps(job_info).encode() + b"\n")
                print(f"✓ Sent via Unix socket")
                return True
        except Exception as e:
            print(f"  Unix socket failed: {e}")

    # Try TCP socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(("127.0.0.1", 19876))
            sock.sendall(json.dumps(job_info).encode() + b"\n")
            print(f"✓ Sent via TCP socket")
            return True
    except Exception as e:
        print(f"  TCP socket failed: {e}")

    return False


def main():
    print("=" * 50)
    print("Open PDF Creator - Test Print Job")
    print("=" * 50)

    # Check for PDF argument
    input_pdf = None
    if len(sys.argv) > 1:
        input_pdf = Path(sys.argv[1])
        if not input_pdf.exists():
            print(f"Error: File not found: {input_pdf}")
            return 1

    # Create spool directory
    spool_dir = get_spool_dir()
    spool_dir.mkdir(parents=True, exist_ok=True)
    print(f"Spool dir: {spool_dir}")

    # Create job file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_id = f"test-{timestamp}"
    title = input_pdf.stem if input_pdf else "Test Document"
    job_filename = f"{timestamp}_{job_id}_{title}.pdf"
    job_path = spool_dir / job_filename

    # Copy or create PDF
    if input_pdf:
        shutil.copy(input_pdf, job_path)
        print(f"✓ Copied: {input_pdf.name}")
    else:
        create_test_pdf(job_path)
        print(f"✓ Created test PDF")

    print(f"✓ Job file: {job_path}")

    # Create job info
    job_info = {
        "job_id": job_id,
        "user": os.environ.get("USER", "unknown"),
        "title": title,
        "copies": 1,
        "options": "",
        "file_path": str(job_path),
        "timestamp": timestamp,
    }

    # Send to GUI
    print()
    print("Sending to GUI...")
    if send_to_gui(job_info):
        print()
        print("✓ Job sent! The Save As dialog should appear.")
    else:
        print()
        print("✗ Could not connect to GUI.")
        print()
        print("Make sure the GUI is running:")
        print("  cd /home/maarten/Documents/GitHub/open-pdf-creator")
        print("  source venv/bin/activate")
        print("  open-pdf-creator")
        print()
        print("Job saved to pending_jobs.json for later pickup.")

        # Save to pending file
        pending_file = spool_dir / "pending_jobs.json"
        pending = []
        if pending_file.exists():
            try:
                with open(pending_file) as f:
                    pending = json.load(f)
            except:
                pass
        pending.append(job_info)
        with open(pending_file, "w") as f:
            json.dump(pending, f, indent=2)

    return 0


if __name__ == "__main__":
    sys.exit(main())
