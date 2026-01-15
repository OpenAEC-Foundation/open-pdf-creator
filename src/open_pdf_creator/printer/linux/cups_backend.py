#!/usr/bin/python3
"""CUPS backend for Open PDF Creator virtual printer.

This script is called by CUPS when a print job is sent to the
Open PDF Creator printer. It receives the print data and triggers
the GUI application to handle the save dialog.

CUPS Backend Protocol:
- When called with no arguments: output device URI and description
- When called with job arguments: process the print job

Arguments from CUPS:
    argv[1] = job ID
    argv[2] = user name
    argv[3] = job title
    argv[4] = number of copies
    argv[5] = print options
    argv[6] = file to print (optional, if not stdin)
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configuration
SOCKET_PATH = "/tmp/open-pdf-creator.sock"
LOG_FILE = "/tmp/open-pdf-creator-cups.log"


def _log(msg: str) -> None:
    """Write to log file immediately."""
    try:
        with open(LOG_FILE, "a") as f:
            from datetime import datetime as dt
            f.write(f"[{dt.now()}] {msg}\n")
            f.flush()
    except Exception:
        pass


# Log immediately on import
_log(f"=== CUPS Backend Loaded ===")
_log(f"Python: {sys.executable}")
_log(f"Args: {sys.argv}")
_log(f"UID: {os.getuid()}, EUID: {os.geteuid()}")


def get_user_home(username: str) -> Path:
    """Get home directory for a specific user."""
    import pwd
    try:
        return Path(pwd.getpwnam(username).pw_dir)
    except KeyError:
        # Fallback to /tmp if user not found
        return Path("/tmp")


def get_spool_dir(username: str) -> Path:
    """Get spool directory for a specific user.

    Uses /tmp because CUPS backend runs as 'lp' user and cannot
    access user home directories.
    """
    # Use /tmp because lp user cannot access home directories
    return Path("/tmp") / "open-pdf-creator-spool" / username


def discovery_mode() -> None:
    """Output device URI and description for CUPS discovery."""
    print(
        'direct open-pdf-creator "Unknown" "Open PDF Creator" '
        '"MFG:OpenAEC;MDL:PDF Creator;DES:Virtual PDF Printer;"'
    )


def process_job(
    job_id: str,
    user: str,
    title: str,
    copies: int,
    options: str,
    input_file: str | None = None,
) -> int:
    """Process a print job from CUPS.

    Args:
        job_id: CUPS job ID
        user: Username who submitted the job
        title: Document title
        copies: Number of copies
        options: Print options string
        input_file: Path to input file (None = read from stdin)

    Returns:
        Exit code (0 = success)
    """
    _log(f"Processing job {job_id} for user {user}")

    # Get user-specific spool directory
    spool_dir = get_spool_dir(user)
    _log(f"Spool dir: {spool_dir}")

    # Ensure spool directory exists with world-writable permissions
    # (needed because CUPS backend runs as 'lp' user)
    try:
        spool_dir.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(spool_dir.parent, 0o777)
    except Exception:
        pass

    try:
        spool_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(spool_dir, 0o777)
    except Exception as e:
        _log(f"Warning: Could not set spool dir permissions: {e}")

    # Set ownership to the user (we're running as root)
    try:
        import pwd
        pw = pwd.getpwnam(user)
        os.chown(spool_dir, pw.pw_uid, pw.pw_gid)
        os.chown(spool_dir.parent, pw.pw_uid, pw.pw_gid)
        os.chown(spool_dir.parent.parent, pw.pw_uid, pw.pw_gid)
    except (KeyError, OSError):
        pass

    # Create unique job file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() or c in "._-" else "_" for c in title)[:50]
    job_filename = f"{timestamp}_{job_id}_{safe_title}.pdf"
    job_path = spool_dir / job_filename

    # Read print data
    try:
        if input_file:
            # Copy from file
            shutil.copy(input_file, job_path)
        else:
            # Read from stdin
            with open(job_path, "wb") as f:
                # Read in chunks to handle large files
                while True:
                    chunk = sys.stdin.buffer.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
    except Exception as e:
        log_error(f"Failed to save print job: {e}")
        return 1

    # Make job file readable by the user
    # (chown won't work since we run as 'lp', not root)
    try:
        os.chmod(job_path, 0o644)
        _log(f"Set file permissions to 644")
    except OSError as e:
        _log(f"Warning: Could not chmod job file: {e}")

    # Create job metadata
    job_info = {
        "job_id": job_id,
        "user": user,
        "title": title,
        "copies": copies,
        "options": options,
        "file_path": str(job_path),
        "timestamp": timestamp,
    }

    # Try to notify the GUI application
    if not notify_gui(job_info):
        # GUI not running, try to start it
        start_gui_with_job(job_info, user)

    log_info(f"Job {job_id} spooled: {job_path}")
    return 0


def notify_gui(job_info: dict) -> bool:
    """Notify the GUI application about a new print job.

    Args:
        job_info: Job metadata dictionary

    Returns:
        True if GUI was notified, False otherwise
    """
    try:
        # Try Unix socket first
        if os.path.exists(SOCKET_PATH):
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.connect(SOCKET_PATH)
                sock.sendall(json.dumps(job_info).encode() + b"\n")
                return True
    except OSError:
        pass

    # Try TCP socket as fallback
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(("127.0.0.1", 19876))
            sock.sendall(json.dumps(job_info).encode() + b"\n")
            return True
    except OSError:
        pass

    return False


def start_gui_with_job(job_info: dict, user: str) -> None:
    """Start the GUI application with a pending job.

    Args:
        job_info: Job metadata dictionary
        user: Username who submitted the job
    """
    # Save job info to file for GUI to pick up
    spool_dir = get_spool_dir(user)
    pending_file = spool_dir / "pending_jobs.json"

    # Load existing pending jobs
    pending_jobs = []
    if pending_file.exists():
        try:
            with open(pending_file) as f:
                pending_jobs = json.load(f)
        except (json.JSONDecodeError, OSError):
            pending_jobs = []

    # Add new job
    pending_jobs.append(job_info)

    # Save pending jobs
    with open(pending_file, "w") as f:
        json.dump(pending_jobs, f)

    # Set correct ownership on pending file
    try:
        import pwd
        pw = pwd.getpwnam(user)
        os.chown(pending_file, pw.pw_uid, pw.pw_gid)
    except (KeyError, OSError):
        pass

    # Try to start GUI as the correct user
    try:
        import pwd
        pw = pwd.getpwnam(user)
        user_home = pw.pw_dir

        # Set up environment for the user
        env = os.environ.copy()
        env["HOME"] = user_home
        env["USER"] = user
        env["LOGNAME"] = user
        env["DISPLAY"] = os.environ.get("DISPLAY", ":0")
        env["XAUTHORITY"] = f"{user_home}/.Xauthority"

        # Try to start GUI as the user using su
        gui_commands = [
            ["su", "-", user, "-c", "open-pdf-creator"],
            ["sudo", "-u", user, "open-pdf-creator"],
        ]

        for cmd in gui_commands:
            try:
                subprocess.Popen(
                    cmd,
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=env,
                )
                log_info(f"Started GUI with: {' '.join(cmd)}")
                return
            except (OSError, FileNotFoundError):
                continue

        log_error("Could not start GUI application")
    except Exception as e:
        log_error(f"Failed to start GUI: {e}")


def log_info(message: str) -> None:
    """Log info message to CUPS and file."""
    _log(f"INFO: {message}")
    print(f"INFO: {message}", file=sys.stderr)


def log_error(message: str) -> None:
    """Log error message to CUPS and file."""
    _log(f"ERROR: {message}")
    print(f"ERROR: {message}", file=sys.stderr)


def main() -> int:
    """Main entry point for CUPS backend."""
    _log("main() called")
    argc = len(sys.argv)

    # Discovery mode - no arguments
    if argc == 1:
        _log("Discovery mode")
        discovery_mode()
        return 0

    # Job processing mode
    if argc < 6:
        log_error(f"Usage: {sys.argv[0]} job-id user title copies options [file]")
        return 1

    job_id = sys.argv[1]
    user = sys.argv[2]
    title = sys.argv[3]

    try:
        copies = int(sys.argv[4])
    except ValueError:
        copies = 1

    options = sys.argv[5]
    input_file = sys.argv[6] if argc > 6 else None

    return process_job(job_id, user, title, copies, options, input_file)


if __name__ == "__main__":
    try:
        _log("Starting main...")
        result = main()
        _log(f"main() returned: {result}")
        sys.exit(result)
    except Exception as e:
        import traceback
        _log(f"FATAL ERROR: {e}")
        _log(traceback.format_exc())
        sys.exit(1)
