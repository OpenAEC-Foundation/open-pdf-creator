"""Print job handler service for Open PDF Creator.

This module provides the service that:
1. Listens for incoming print jobs from the CUPS backend
2. Manages the job queue
3. Triggers the GUI to handle save dialogs
"""

from __future__ import annotations

import json
import os
import socket
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Signal

# Configuration
UNIX_SOCKET_PATH = "/tmp/open-pdf-creator.sock"
TCP_PORT = 19876


def get_spool_dir() -> Path:
    """Get spool directory - uses /tmp because CUPS backend runs as lp user."""
    import getpass
    username = getpass.getuser()
    return Path("/tmp") / "open-pdf-creator-spool" / username


SPOOL_DIR = get_spool_dir()


@dataclass
class PrintJob:
    """Represents a print job."""
    job_id: str
    user: str
    title: str
    copies: int
    options: str
    file_path: Path
    timestamp: str
    processed: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> PrintJob:
        """Create PrintJob from dictionary."""
        return cls(
            job_id=data.get("job_id", ""),
            user=data.get("user", ""),
            title=data.get("title", "Untitled"),
            copies=data.get("copies", 1),
            options=data.get("options", ""),
            file_path=Path(data.get("file_path", "")),
            timestamp=data.get("timestamp", datetime.now().strftime("%Y%m%d_%H%M%S")),
        )


class PrintJobHandler(QObject):
    """Handler for incoming print jobs.

    Emits signals when new jobs arrive so the GUI can respond.
    """

    job_received = Signal(object)  # Emits PrintJob

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._unix_socket: socket.socket | None = None
        self._tcp_socket: socket.socket | None = None
        self._threads: list[threading.Thread] = []
        self._pending_jobs: list[PrintJob] = []

    def start(self) -> None:
        """Start listening for print jobs."""
        if self._running:
            return

        self._running = True

        # Load any pending jobs from disk
        self._load_pending_jobs()

        # Start Unix socket listener
        unix_thread = threading.Thread(target=self._unix_listener, daemon=True)
        unix_thread.start()
        self._threads.append(unix_thread)

        # Start TCP socket listener as fallback
        tcp_thread = threading.Thread(target=self._tcp_listener, daemon=True)
        tcp_thread.start()
        self._threads.append(tcp_thread)

    def stop(self) -> None:
        """Stop listening for print jobs."""
        self._running = False

        # Close sockets
        if self._unix_socket:
            try:
                self._unix_socket.close()
            except Exception:
                pass

        if self._tcp_socket:
            try:
                self._tcp_socket.close()
            except Exception:
                pass

        # Remove Unix socket file
        try:
            if os.path.exists(UNIX_SOCKET_PATH):
                os.unlink(UNIX_SOCKET_PATH)
        except Exception:
            pass

    def get_pending_jobs(self) -> list[PrintJob]:
        """Get list of pending (unprocessed) jobs."""
        return [j for j in self._pending_jobs if not j.processed]

    def mark_job_processed(self, job: PrintJob) -> None:
        """Mark a job as processed."""
        job.processed = True
        self._save_pending_jobs()

    def _load_pending_jobs(self) -> None:
        """Load pending jobs from disk."""
        pending_file = SPOOL_DIR / "pending_jobs.json"

        if not pending_file.exists():
            return

        try:
            with open(pending_file) as f:
                jobs_data = json.load(f)

            for data in jobs_data:
                job = PrintJob.from_dict(data)
                if job.file_path.exists():
                    self._pending_jobs.append(job)
                    # Emit signal for each pending job
                    self.job_received.emit(job)

            # Clear the pending file after loading
            pending_file.unlink()

        except (json.JSONDecodeError, OSError) as e:
            print(f"Error loading pending jobs: {e}")

    def _save_pending_jobs(self) -> None:
        """Save unprocessed jobs to disk."""
        pending_file = SPOOL_DIR / "pending_jobs.json"
        SPOOL_DIR.mkdir(parents=True, exist_ok=True)

        unprocessed = [j for j in self._pending_jobs if not j.processed]

        if not unprocessed:
            if pending_file.exists():
                pending_file.unlink()
            return

        try:
            data = [
                {
                    "job_id": j.job_id,
                    "user": j.user,
                    "title": j.title,
                    "copies": j.copies,
                    "options": j.options,
                    "file_path": str(j.file_path),
                    "timestamp": j.timestamp,
                }
                for j in unprocessed
            ]

            with open(pending_file, "w") as f:
                json.dump(data, f)

        except OSError as e:
            print(f"Error saving pending jobs: {e}")

    def _unix_listener(self) -> None:
        """Listen for connections on Unix socket."""
        # Remove existing socket file
        try:
            if os.path.exists(UNIX_SOCKET_PATH):
                os.unlink(UNIX_SOCKET_PATH)
        except Exception:
            pass

        try:
            self._unix_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._unix_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._unix_socket.bind(UNIX_SOCKET_PATH)
            self._unix_socket.listen(5)

            # Make socket accessible
            os.chmod(UNIX_SOCKET_PATH, 0o666)

            while self._running:
                try:
                    self._unix_socket.settimeout(1.0)
                    conn, _ = self._unix_socket.accept()
                    self._handle_connection(conn)
                except TimeoutError:
                    continue
                except Exception as e:
                    if self._running:
                        print(f"Unix socket error: {e}")
                    break

        except Exception as e:
            print(f"Failed to create Unix socket: {e}")

    def _tcp_listener(self) -> None:
        """Listen for connections on TCP socket."""
        try:
            self._tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._tcp_socket.bind(("127.0.0.1", TCP_PORT))
            self._tcp_socket.listen(5)

            while self._running:
                try:
                    self._tcp_socket.settimeout(1.0)
                    conn, _ = self._tcp_socket.accept()
                    self._handle_connection(conn)
                except TimeoutError:
                    continue
                except Exception as e:
                    if self._running:
                        print(f"TCP socket error: {e}")
                    break

        except Exception as e:
            print(f"Failed to create TCP socket: {e}")

    def _handle_connection(self, conn: socket.socket) -> None:
        """Handle an incoming connection."""
        try:
            data = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b"\n" in data:
                    break

            if data:
                job_data = json.loads(data.decode().strip())
                job = PrintJob.from_dict(job_data)
                self._pending_jobs.append(job)
                self.job_received.emit(job)

        except Exception as e:
            print(f"Error handling connection: {e}")

        finally:
            conn.close()
