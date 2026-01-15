"""Main entry point for Open PDF Creator."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from open_pdf_creator.core.settings import Settings
from open_pdf_creator.gui.main_window import MainWindow


def main() -> int:
    """Main application entry point."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Open PDF Creator")
    app.setOrganizationName("OpenAEC")
    app.setOrganizationDomain("openaec.org")

    # Set application style
    app.setStyle("Fusion")

    # Load settings
    settings = Settings.load()

    # Create main window
    window = MainWindow(settings)

    # Handle command line arguments (files to open)
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            path = Path(arg)
            if path.exists() and path.suffix.lower() == ".pdf":
                window.combiner.add_pdf(path)

    # Show window
    if settings.start_minimized and window.tray_icon:
        window.tray_icon.show()
    else:
        window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
