"""PDF Combiner widget with drag and drop support."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from open_pdf_creator.core.image_converter import ImageConverter
from open_pdf_creator.core.pdf_processor import PageSelection, PDFInfo, PDFProcessor
from open_pdf_creator.core.settings import Settings


@dataclass
class PDFEntry:
    """Represents a PDF file in the combiner."""
    info: PDFInfo
    selected_pages: list[int]  # Empty means all pages
    rotation: int = 0

    @property
    def effective_pages(self) -> list[int]:
        """Get effective page list."""
        if self.selected_pages:
            return self.selected_pages
        return list(range(self.info.num_pages))

    @property
    def page_count(self) -> int:
        """Get number of pages to include."""
        return len(self.effective_pages)


class PDFListItem(QWidget):
    """Custom widget for PDF list items."""

    removed = Signal(object)  # Emits the PDFEntry
    rotation_changed = Signal(object, int)  # Emits (PDFEntry, new_rotation)

    def __init__(self, entry: PDFEntry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.entry = entry
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the widget UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # Thumbnail placeholder
        self.thumbnail = QLabel()
        self.thumbnail.setFixedSize(60, 80)
        self.thumbnail.setStyleSheet(
            "background-color: #f0f0f0; border: 1px solid #ccc;"
        )
        self.thumbnail.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.thumbnail)

        # Info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # Filename
        name_label = QLabel(self.entry.info.filename)
        name_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(name_label)

        # Page info
        pages_text = f"{self.entry.page_count} pages"
        if self.entry.selected_pages:
            pages_text += " (selected)"
        self.pages_label = QLabel(pages_text)
        self.pages_label.setStyleSheet("color: #666;")
        info_layout.addWidget(self.pages_label)

        # Size info
        if self.entry.info.page_sizes:
            w, h = self.entry.info.page_sizes[0]
            # Convert points to mm
            w_mm = w * 25.4 / 72
            h_mm = h * 25.4 / 72
            size_label = QLabel(f"{w_mm:.0f} x {h_mm:.0f} mm")
            size_label.setStyleSheet("color: #888; font-size: 11px;")
            info_layout.addWidget(size_label)

        info_layout.addStretch()
        layout.addLayout(info_layout, stretch=1)

        # Rotation control
        rotation_layout = QVBoxLayout()
        rotation_layout.setSpacing(2)

        rotation_label = QLabel("Rotate:")
        rotation_label.setStyleSheet("font-size: 11px;")
        rotation_layout.addWidget(rotation_label)

        rotation_btns = QHBoxLayout()
        btn_ccw = QPushButton("↶")
        btn_ccw.setFixedSize(28, 28)
        btn_ccw.setToolTip("Rotate counter-clockwise")
        btn_ccw.clicked.connect(lambda: self._rotate(-90))
        rotation_btns.addWidget(btn_ccw)

        btn_cw = QPushButton("↷")
        btn_cw.setFixedSize(28, 28)
        btn_cw.setToolTip("Rotate clockwise")
        btn_cw.clicked.connect(lambda: self._rotate(90))
        rotation_btns.addWidget(btn_cw)

        rotation_layout.addLayout(rotation_btns)
        rotation_layout.addStretch()
        layout.addLayout(rotation_layout)

        # Remove button
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(28, 28)
        remove_btn.setStyleSheet(
            "QPushButton { color: #c00; font-size: 18px; font-weight: bold; }"
            "QPushButton:hover { background-color: #fdd; }"
        )
        remove_btn.setToolTip("Remove")
        remove_btn.clicked.connect(lambda: self.removed.emit(self.entry))
        layout.addWidget(remove_btn)

        # Load thumbnail asynchronously (simplified for now)
        self._load_thumbnail()

    def _load_thumbnail(self) -> None:
        """Load thumbnail for first page."""
        try:
            thumb_bytes = ImageConverter.get_page_thumbnail(
                self.entry.info.path,
                page_number=0,
                max_size=(60, 80),
            )
            pixmap = QPixmap()
            pixmap.loadFromData(thumb_bytes)
            self.thumbnail.setPixmap(pixmap.scaled(
                60, 80,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            ))
        except Exception:
            self.thumbnail.setText("PDF")

    def _rotate(self, angle: int) -> None:
        """Rotate the PDF."""
        self.entry.rotation = (self.entry.rotation + angle) % 360
        self.rotation_changed.emit(self.entry, self.entry.rotation)

    def update_pages_label(self) -> None:
        """Update the pages label."""
        pages_text = f"{self.entry.page_count} pages"
        if self.entry.selected_pages:
            pages_text += " (selected)"
        self.pages_label.setText(pages_text)


class PDFCombinerWidget(QWidget):
    """Widget for combining PDF files."""

    files_changed = Signal()

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.entries: list[PDFEntry] = []
        self._setup_ui()

        # Enable drag & drop from file manager
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter event for external files."""
        if event.mimeData().hasUrls():
            # Check if any URL is a PDF
            for url in event.mimeData().urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop event for external files."""
        for url in event.mimeData().urls():
            if url.isLocalFile():
                file_path = Path(url.toLocalFile())
                if file_path.suffix.lower() == ".pdf":
                    self.add_pdf(file_path)
        event.acceptProposedAction()

    def _setup_ui(self) -> None:
        """Set up the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header with title
        header = QLabel("PDF Combiner - Drag & Drop to Reorder")
        header.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #2563eb; padding: 4px;"
        )
        layout.addWidget(header)

        # Drop zone / list
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_widget.setDefaultDropAction(Qt.MoveAction)
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget.setSpacing(4)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.list_widget.model().rowsMoved.connect(self._on_rows_moved)
        self.list_widget.setAcceptDrops(True)
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: 2px dashed #ccc;
                border-radius: 8px;
                background-color: #fafafa;
            }
            QListWidget:hover {
                border-color: #2563eb;
            }
        """)
        layout.addWidget(self.list_widget)

        # Empty state
        self.empty_label = QLabel(
            "Drop PDF files here to combine them\n\n"
            "You can:\n"
            "- Drag files from your file manager\n"
            "- Use 'Add Files' button below\n"
            "- Reorder by dragging items up/down\n"
            "- Rotate pages with the buttons"
        )
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(
            "color: #666; font-size: 14px; padding: 40px; line-height: 1.6;"
        )
        layout.addWidget(self.empty_label)

        # Button bar
        self._setup_button_bar(layout)

        self._update_empty_state()

    def _setup_button_bar(self, parent_layout: QVBoxLayout) -> None:
        """Set up the button bar at the bottom."""
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #ddd;")
        parent_layout.addWidget(separator)

        # Button bar
        button_bar = QHBoxLayout()
        button_bar.setSpacing(8)

        # Add Files button
        self.btn_add = QPushButton("+ Add PDF Files")
        self.btn_add.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        self.btn_add.clicked.connect(self._on_add_files_clicked)
        button_bar.addWidget(self.btn_add)

        button_bar.addStretch()

        # Move buttons
        self.btn_up = QPushButton("Move Up")
        self.btn_up.clicked.connect(self._move_selected_up)
        button_bar.addWidget(self.btn_up)

        self.btn_down = QPushButton("Move Down")
        self.btn_down.clicked.connect(self._move_selected_down)
        button_bar.addWidget(self.btn_down)

        # Remove button
        self.btn_remove = QPushButton("Remove Selected")
        self.btn_remove.setStyleSheet("""
            QPushButton {
                color: #dc2626;
            }
            QPushButton:hover {
                background-color: #fee2e2;
            }
        """)
        self.btn_remove.clicked.connect(self._remove_selected)
        button_bar.addWidget(self.btn_remove)

        button_bar.addStretch()

        # Merge button (prominent)
        self.btn_merge = QPushButton("Merge to PDF")
        self.btn_merge.setStyleSheet("""
            QPushButton {
                background-color: #16a34a;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #15803d;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        self.btn_merge.clicked.connect(self._on_merge_clicked)
        button_bar.addWidget(self.btn_merge)

        parent_layout.addLayout(button_bar)

    @property
    def file_count(self) -> int:
        """Get number of files."""
        return len(self.entries)

    @property
    def total_pages(self) -> int:
        """Get total page count."""
        return sum(e.page_count for e in self.entries)

    def add_pdf(self, pdf_path: Path) -> bool:
        """Add a PDF file to the list.

        Returns:
            True if successful, False otherwise
        """
        try:
            info = PDFProcessor.get_info(pdf_path)
            entry = PDFEntry(info=info, selected_pages=[])

            # Create list item
            item_widget = PDFListItem(entry)
            item_widget.removed.connect(self._on_item_removed)
            item_widget.rotation_changed.connect(self._on_rotation_changed)

            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint())
            list_item.setData(Qt.UserRole, entry)

            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, item_widget)

            self.entries.append(entry)
            self._update_empty_state()
            self.files_changed.emit()
            return True

        except Exception as e:
            print(f"Error adding PDF: {e}")
            return False

    def remove_entry(self, entry: PDFEntry) -> None:
        """Remove an entry from the list."""
        if entry in self.entries:
            self.entries.remove(entry)

            # Find and remove list item
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item.data(Qt.UserRole) is entry:
                    self.list_widget.takeItem(i)
                    break

            self._update_empty_state()
            self.files_changed.emit()

    def clear(self) -> None:
        """Clear all entries."""
        self.entries.clear()
        self.list_widget.clear()
        self._update_empty_state()
        self.files_changed.emit()

    def get_selections(self) -> list[PageSelection]:
        """Get page selections for all entries in order."""
        selections = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            entry = item.data(Qt.UserRole)
            selections.append(PageSelection(
                pdf_path=entry.info.path,
                pages=entry.effective_pages,
                rotation=entry.rotation,
            ))
        return selections

    def export_pdf(self, output_path: Path) -> Path:
        """Export combined PDF."""
        selections = self.get_selections()
        if not selections:
            raise ValueError("No files to export")

        return PDFProcessor.merge_pdfs(
            selections=selections,
            output_path=output_path,
            metadata={
                "/Creator": "Open PDF Creator",
                "/Producer": "Open PDF Creator",
            },
        )

    def export_images(
        self,
        output_dir: Path,
        format: Literal["png", "jpeg", "tiff"] = "png",
    ) -> list[Path]:
        """Export as images."""
        # First create combined PDF in temp location
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            self.export_pdf(tmp_path)

            if format == "tiff":
                # Multi-page TIFF
                output_path = output_dir / f"combined.{format}"
                ImageConverter.pdf_to_multipage_tiff(
                    tmp_path,
                    output_path,
                    quality=self.settings.image_quality,
                )
                return [output_path]
            else:
                return ImageConverter.pdf_to_images(
                    tmp_path,
                    output_dir,
                    format=format,
                    quality=self.settings.image_quality,
                )
        finally:
            tmp_path.unlink(missing_ok=True)

    def _on_item_removed(self, entry: PDFEntry) -> None:
        """Handle item removal."""
        self.remove_entry(entry)

    def _on_rotation_changed(self, entry: PDFEntry, rotation: int) -> None:
        """Handle rotation change."""
        self.files_changed.emit()

    def _on_rows_moved(self) -> None:
        """Handle row reordering."""
        # Update entries order to match list
        self.entries = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            self.entries.append(item.data(Qt.UserRole))
        self.files_changed.emit()

    def _show_context_menu(self, position: QPoint) -> None:
        """Show context menu for list items."""
        item = self.list_widget.itemAt(position)
        if not item:
            return

        entry = item.data(Qt.UserRole)
        menu = QMenu(self)

        # Move actions
        move_up = menu.addAction("Move Up")
        move_up.setEnabled(self.list_widget.row(item) > 0)
        move_down = menu.addAction("Move Down")
        move_down.setEnabled(
            self.list_widget.row(item) < self.list_widget.count() - 1
        )

        menu.addSeparator()

        # Rotation actions
        rotate_menu = menu.addMenu("Rotate")
        rotate_90 = rotate_menu.addAction("90° Clockwise")
        rotate_180 = rotate_menu.addAction("180°")
        rotate_270 = rotate_menu.addAction("90° Counter-clockwise")

        menu.addSeparator()

        # Remove action
        remove = menu.addAction("Remove")

        # Execute menu
        action = menu.exec_(self.list_widget.mapToGlobal(position))

        if action == move_up:
            self._move_item(item, -1)
        elif action == move_down:
            self._move_item(item, 1)
        elif action == rotate_90:
            entry.rotation = (entry.rotation + 90) % 360
            self.files_changed.emit()
        elif action == rotate_180:
            entry.rotation = (entry.rotation + 180) % 360
            self.files_changed.emit()
        elif action == rotate_270:
            entry.rotation = (entry.rotation + 270) % 360
            self.files_changed.emit()
        elif action == remove:
            self.remove_entry(entry)

    def _move_item(self, item: QListWidgetItem, direction: int) -> None:
        """Move item up or down."""
        row = self.list_widget.row(item)
        new_row = row + direction

        if 0 <= new_row < self.list_widget.count():
            # Get widget and entry
            entry = item.data(Qt.UserRole)
            widget = self.list_widget.itemWidget(item)

            # Remove and reinsert
            self.list_widget.takeItem(row)

            new_item = QListWidgetItem()
            new_item.setSizeHint(widget.sizeHint())
            new_item.setData(Qt.UserRole, entry)

            self.list_widget.insertItem(new_row, new_item)
            self.list_widget.setItemWidget(new_item, widget)
            self.list_widget.setCurrentItem(new_item)

            self._on_rows_moved()

    def _on_add_files_clicked(self) -> None:
        """Handle Add Files button click."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select PDF Files to Combine",
            "",
            "PDF Files (*.pdf);;All Files (*)",
        )
        for file_path in files:
            self.add_pdf(Path(file_path))

    def _move_selected_up(self) -> None:
        """Move selected items up."""
        items = self.list_widget.selectedItems()
        if items:
            self._move_item(items[0], -1)

    def _move_selected_down(self) -> None:
        """Move selected items down."""
        items = self.list_widget.selectedItems()
        if items:
            self._move_item(items[0], 1)

    def _remove_selected(self) -> None:
        """Remove selected items."""
        items = self.list_widget.selectedItems()
        for item in items:
            entry = item.data(Qt.UserRole)
            self.remove_entry(entry)

    def _on_merge_clicked(self) -> None:
        """Handle Merge button click."""
        if not self.entries:
            QMessageBox.information(
                self,
                "No Files",
                "Please add PDF files first before merging.",
            )
            return

        # Ask for save location
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Merged PDF As",
            "merged.pdf",
            "PDF Files (*.pdf)",
        )

        if save_path:
            try:
                output_path = self.export_pdf(Path(save_path))
                QMessageBox.information(
                    self,
                    "Merge Complete",
                    f"PDF files successfully merged!\n\nSaved to:\n{output_path}",
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Merge Error",
                    f"Failed to merge PDF files:\n{e}",
                )

    def _update_empty_state(self) -> None:
        """Update visibility of empty state and button states."""
        has_files = len(self.entries) > 0
        self.list_widget.setVisible(has_files)
        self.empty_label.setVisible(not has_files)

        # Update button states
        self.btn_merge.setEnabled(has_files)
        self.btn_up.setEnabled(has_files)
        self.btn_down.setEnabled(has_files)
        self.btn_remove.setEnabled(has_files)
