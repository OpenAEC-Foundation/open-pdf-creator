#!/usr/bin/python3
"""Standalone CUPS backend - no external dependencies."""

import json
import os
import pwd
import shutil
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path

LOG_FILE = "/tmp/open-pdf-creator.log"

def log(msg):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now()}] {msg}\n")
    except:
        pass

def get_user_home(username):
    try:
        return Path(pwd.getpwnam(username).pw_dir)
    except KeyError:
        return Path("/tmp")

def get_spool_dir(username):
    return get_user_home(username) / ".local" / "share" / "open-pdf-creator" / "spool"

def main():
    log(f"Backend started with args: {sys.argv}")

    # Discovery mode
    if len(sys.argv) == 1:
        print('direct open-pdf-creator "Unknown" "Open PDF Creator" '
              '"MFG:OpenAEC;MDL:PDF Creator;DES:Virtual PDF Printer;"')
        return 0

    if len(sys.argv) < 6:
        log("Not enough arguments")
        return 1

    job_id = sys.argv[1]
    user = sys.argv[2]
    title = sys.argv[3]
    copies = sys.argv[4]
    options = sys.argv[5]
    input_file = sys.argv[6] if len(sys.argv) > 6 else None

    log(f"Job: {job_id}, User: {user}, Title: {title}")

    # Get spool directory
    spool_dir = get_spool_dir(user)
    log(f"Spool dir: {spool_dir}")

    # Create spool directory
    try:
        spool_dir.mkdir(parents=True, exist_ok=True)
        pw = pwd.getpwnam(user)
        os.chown(spool_dir, pw.pw_uid, pw.pw_gid)
        os.chown(spool_dir.parent, pw.pw_uid, pw.pw_gid)
        os.chown(spool_dir.parent.parent, pw.pw_uid, pw.pw_gid)
    except Exception as e:
        log(f"Error creating spool dir: {e}")

    # Create job file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() or c in "._- " else "_" for c in title)[:50]
    job_filename = f"{timestamp}_{job_id}_{safe_title}.pdf"
    job_path = spool_dir / job_filename

    log(f"Job path: {job_path}")

    # Read print data
    try:
        if input_file:
            shutil.copy(input_file, job_path)
            log(f"Copied from {input_file}")
        else:
            with open(job_path, "wb") as f:
                while True:
                    chunk = sys.stdin.buffer.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            log(f"Read from stdin")

        # Set ownership
        pw = pwd.getpwnam(user)
        os.chown(job_path, pw.pw_uid, pw.pw_gid)

    except Exception as e:
        log(f"Error saving job: {e}")
        return 1

    # Save job info
    job_info = {
        "job_id": job_id,
        "user": user,
        "title": title,
        "file_path": str(job_path),
        "timestamp": timestamp,
    }

    pending_file = spool_dir / "pending_jobs.json"
    try:
        pending = []
        if pending_file.exists():
            with open(pending_file) as f:
                pending = json.load(f)
        pending.append(job_info)
        with open(pending_file, "w") as f:
            json.dump(pending, f)
        os.chown(pending_file, pw.pw_uid, pw.pw_gid)
    except Exception as e:
        log(f"Error saving pending: {e}")

    # Try to notify GUI via socket
    notified = False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 19876))
        sock.sendall(json.dumps(job_info).encode() + b"\n")
        sock.close()
        notified = True
        log("Notified GUI via socket")
    except Exception as e:
        log(f"Socket notify failed: {e}")

    # Start GUI as user if not notified
    if not notified:
        try:
            user_home = get_user_home(user)
            display = os.environ.get("DISPLAY", ":0")

            # Use sudo -u to run as the user
            cmd = [
                "sudo", "-u", user,
                f"DISPLAY={display}",
                f"XAUTHORITY={user_home}/.Xauthority",
                "open-pdf-creator"
            ]

            subprocess.Popen(
                " ".join(cmd),
                shell=True,
                start_new_session=True,
                stdout=open("/dev/null", "w"),
                stderr=open("/dev/null", "w"),
            )
            log(f"Started GUI: {cmd}")
        except Exception as e:
            log(f"Failed to start GUI: {e}")

    log(f"Job {job_id} completed successfully")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log(f"Fatal error: {e}")
        sys.exit(1)
