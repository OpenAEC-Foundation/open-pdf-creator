"""Main application window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QCloseEvent, QDragEnterEvent, QDropEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStatusBar,
    QSystemTrayIcon,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from open_pdf_creator.core.settings import Settings
from open_pdf_creator.gui.combiner_widget import PDFCombinerWidget
from open_pdf_creator.gui.save_dialog import SaveDialog
from open_pdf_creator.gui.settings_dialog import SettingsDialog
from open_pdf_creator.service.print_handler import PrintJobHandler


class MainWindow(QMainWindow):
    """Main application window with PDF combiner functionality."""

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings
        self._setup_ui()
        self._setup_toolbar()
        self._setup_tray()
        self._setup_print_handler()
        self._restore_geometry()

        # Enable drag and drop
        self.setAcceptDrops(True)

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("Open PDF Creator")
        self.setMinimumSize(700, 500)

        # Set window icon
        icon_path = Path(__file__).parent / "resources" / "icon_128.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # PDF Combiner widget
        self.combiner = PDFCombinerWidget(self.settings)
        layout.addWidget(self.combiner)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._update_status()

        # Connect signals
        self.combiner.files_changed.connect(self._update_status)

    def _setup_toolbar(self) -> None:
        """Set up the toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        # Add files action
        self.add_action = QAction("Add Files", self)
        self.add_action.setShortcut("Ctrl+O")
        self.add_action.setStatusTip("Add PDF files to combine")
        self.add_action.triggered.connect(self._on_add_files)
        toolbar.addAction(self.add_action)

        toolbar.addSeparator()

        # Export/Save action
        self.export_action = QAction("Export PDF", self)
        self.export_action.setShortcut("Ctrl+S")
        self.export_action.setStatusTip("Export combined PDF")
        self.export_action.triggered.connect(self._on_export)
        toolbar.addAction(self.export_action)

        # Export as images action
        self.export_images_action = QAction("Export Images", self)
        self.export_images_action.setShortcut("Ctrl+Shift+S")
        self.export_images_action.setStatusTip("Export as images (PNG, JPEG, TIFF)")
        self.export_images_action.triggered.connect(self._on_export_images)
        toolbar.addAction(self.export_images_action)

        toolbar.addSeparator()

        # Clear action
        self.clear_action = QAction("Clear All", self)
        self.clear_action.setShortcut("Ctrl+Delete")
        self.clear_action.setStatusTip("Clear all files")
        self.clear_action.triggered.connect(self._on_clear)
        toolbar.addAction(self.clear_action)

        # Add spacer
        spacer = QWidget()
        spacer.setSizePolicy(
            spacer.sizePolicy().horizontalPolicy(),
            spacer.sizePolicy().verticalPolicy()
        )
        from PySide6.QtWidgets import QSizePolicy
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        # Settings action
        self.settings_action = QAction("Settings", self)
        self.settings_action.setShortcut("Ctrl+,")
        self.settings_action.setStatusTip("Open settings")
        self.settings_action.triggered.connect(self._on_settings)
        toolbar.addAction(self.settings_action)

    def _setup_tray(self) -> None:
        """Set up system tray icon."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = None
            return

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("Open PDF Creator")

        # Set tray icon
        icon_path = Path(__file__).parent / "resources" / "icon_32.png"
        if icon_path.exists():
            self.tray_icon.setIcon(QIcon(str(icon_path)))

        # Create tray menu
        tray_menu = QMenu()

        show_action = tray_menu.addAction("Show Window")
        show_action.triggered.connect(self.show_and_activate)

        tray_menu.addSeparator()

        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(self._on_quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)

        if self.settings.minimize_to_tray:
            self.tray_icon.show()

    def _setup_print_handler(self) -> None:
        """Set up the print job handler."""
        self.print_handler = PrintJobHandler(self)
        self.print_handler.job_received.connect(self._on_print_job)
        self.print_handler.start()

    def _on_print_job(self, job) -> None:
        """Handle incoming print job from CUPS backend.

        Shows the Save As dialog IMMEDIATELY when a print job arrives.
        """
        # Check file exists first
        if not job.file_path.exists():
            self.print_handler.mark_job_processed(job)
            return

        # Generate suggested filename
        safe_title = "".join(
            c if c.isalnum() or c in " ._-" else "_" for c in job.title
        ).strip() or "document"

        # Determine save directory
        save_dir = self.settings.get_output_directory()
        suggested_path = save_dir / f"{safe_title}.pdf"

        # Show Save As dialog IMMEDIATELY - no other UI first
        save_path, _ = QFileDialog.getSaveFileName(
            None,  # No parent - dialog appears immediately
            "Save PDF As - Open PDF Creator",
            str(suggested_path),
            "PDF Files (*.pdf);;All Files (*)",
        )

        if save_path:
            save_path = Path(save_path)
            try:
                # Copy/move the print job to the chosen location
                import shutil
                shutil.copy(job.file_path, save_path)

                # Update recent directories
                self.settings.add_recent_directory(str(save_path.parent))
                self.settings.save()

                # Delete the spool file after successful save
                job.file_path.unlink(missing_ok=True)

                # Show success notification
                if self.tray_icon:
                    self.tray_icon.showMessage(
                        "PDF Saved",
                        f"Saved: {save_path.name}",
                        QSystemTrayIcon.Information,
                        3000,
                    )

            except Exception as e:
                QMessageBox.critical(
                    None,
                    "Save Error",
                    f"Failed to save PDF:\n{e}",
                )
        else:
            # User cancelled - ask what to do
            reply = QMessageBox.question(
                None,
                "Print Job",
                "You cancelled saving. Would you like to add this document "
                "to the PDF combiner for later?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Yes:
                self.show_and_activate()
                self.combiner.add_pdf(job.file_path)
                self.status_bar.showMessage(
                    "Print job added to combiner. Export when ready.", 5000
                )
            else:
                # User doesn't want it - delete spool file
                job.file_path.unlink(missing_ok=True)

        # Mark job as processed
        self.print_handler.mark_job_processed(job)

    def _restore_geometry(self) -> None:
        """Restore window geometry from settings."""
        geom = self.settings.window_geometry
        self.setGeometry(
            geom.get("x", 100),
            geom.get("y", 100),
            geom.get("width", 900),
            geom.get("height", 700),
        )

    def _save_geometry(self) -> None:
        """Save window geometry to settings."""
        geom = self.geometry()
        self.settings.window_geometry = {
            "x": geom.x(),
            "y": geom.y(),
            "width": geom.width(),
            "height": geom.height(),
        }
        self.settings.save()

    def _update_status(self) -> None:
        """Update status bar."""
        count = self.combiner.file_count
        pages = self.combiner.total_pages
        if count == 0:
            self.status_bar.showMessage("Drop PDF files here or click 'Add Files'")
        else:
            self.status_bar.showMessage(f"{count} files, {pages} pages total")

    def show_and_activate(self) -> None:
        """Show and activate the window."""
        self.show()
        self.setWindowState(
            self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive
        )
        self.activateWindow()
        self.raise_()

    # Event handlers

    def _on_add_files(self) -> None:
        """Handle add files action."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select PDF Files",
            str(self.settings.get_output_directory()),
            "PDF Files (*.pdf);;All Files (*)",
        )
        if files:
            for file_path in files:
                self.combiner.add_pdf(Path(file_path))

    def _on_export(self) -> None:
        """Handle export action."""
        if self.combiner.file_count == 0:
            QMessageBox.information(
                self,
                "No Files",
                "Please add PDF files first.",
            )
            return

        dialog = SaveDialog(self.settings, export_type="pdf", parent=self)
        if dialog.exec():
            output_path = dialog.get_output_path()
            try:
                self.combiner.export_pdf(output_path)
                self.settings.add_recent_directory(str(output_path.parent))
                self.settings.save()
                QMessageBox.information(
                    self,
                    "Export Complete",
                    f"PDF saved to:\n{output_path}",
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Export Error",
                    f"Failed to export PDF:\n{e}",
                )

    def _on_export_images(self) -> None:
        """Handle export as images action."""
        if self.combiner.file_count == 0:
            QMessageBox.information(
                self,
                "No Files",
                "Please add PDF files first.",
            )
            return

        dialog = SaveDialog(self.settings, export_type="image", parent=self)
        if dialog.exec():
            output_path = dialog.get_output_path()
            format_type = dialog.get_image_format()
            try:
                paths = self.combiner.export_images(output_path.parent, format_type)
                self.settings.add_recent_directory(str(output_path.parent))
                self.settings.save()
                QMessageBox.information(
                    self,
                    "Export Complete",
                    f"Exported {len(paths)} images to:\n{output_path.parent}",
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Export Error",
                    f"Failed to export images:\n{e}",
                )

    def _on_clear(self) -> None:
        """Handle clear action."""
        if self.combiner.file_count > 0:
            reply = QMessageBox.question(
                self,
                "Clear All",
                "Remove all files from the list?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.combiner.clear()

    def _on_settings(self) -> None:
        """Handle settings action."""
        dialog = SettingsDialog(self.settings, parent=self)
        if dialog.exec():
            self.settings = dialog.get_settings()
            self.settings.save()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_and_activate()

    def _on_quit(self) -> None:
        """Handle quit action."""
        self._save_geometry()
        self.print_handler.stop()
        QApplication.quit()

    # Drag and drop

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            # Check if any URLs are PDF files
            for url in event.mimeData().urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop event."""
        for url in event.mimeData().urls():
            if url.isLocalFile():
                file_path = Path(url.toLocalFile())
                if file_path.suffix.lower() == ".pdf":
                    self.combiner.add_pdf(file_path)
        event.acceptProposedAction()

    # Window events

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        if self.settings.minimize_to_tray and self.tray_icon:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Open PDF Creator",
                "Application minimized to tray. Double-click to open.",
                QSystemTrayIcon.Information,
                2000,
            )
        else:
            self._save_geometry()
            event.accept()
