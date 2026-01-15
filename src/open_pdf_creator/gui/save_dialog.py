"""Save/Export dialog for Open PDF Creator."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from open_pdf_creator.core.settings import ImageQuality, Settings


class SaveDialog(QDialog):
    """Dialog for saving/exporting PDFs and images."""

    def __init__(
        self,
        settings: Settings,
        export_type: Literal["pdf", "image"] = "pdf",
        suggested_name: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.export_type = export_type
        self.suggested_name = suggested_name or self._generate_filename()

        self.setWindowTitle(
            "Export PDF" if export_type == "pdf" else "Export as Images"
        )
        self.setMinimumWidth(500)
        self._setup_ui()

    def _generate_filename(self) -> str:
        """Generate a default filename based on template."""
        template = self.settings.filename_template
        now = datetime.now()

        replacements = {
            "{date}": now.strftime("%Y-%m-%d"),
            "{time}": now.strftime("%H%M%S"),
            "{datetime}": now.strftime("%Y-%m-%d_%H%M%S"),
            "{title}": "combined",
        }

        result = template
        for key, value in replacements.items():
            result = result.replace(key, value)

        return result

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Location section
        location_group = QGroupBox("Save Location")
        location_layout = QVBoxLayout(location_group)

        # Directory selection
        dir_layout = QHBoxLayout()
        self.dir_edit = QLineEdit()
        self.dir_edit.setText(str(self.settings.get_output_directory()))
        self.dir_edit.setReadOnly(True)
        dir_layout.addWidget(self.dir_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_directory)
        dir_layout.addWidget(browse_btn)

        location_layout.addLayout(dir_layout)

        # Recent directories
        if self.settings.recent_directories:
            recent_label = QLabel("Recent:")
            recent_label.setStyleSheet("color: #666; margin-top: 8px;")
            location_layout.addWidget(recent_label)

            self.recent_list = QListWidget()
            self.recent_list.setMaximumHeight(100)
            for dir_path in self.settings.recent_directories[:5]:
                item = QListWidgetItem(dir_path)
                self.recent_list.addItem(item)
            self.recent_list.itemClicked.connect(self._on_recent_clicked)
            location_layout.addWidget(self.recent_list)

        layout.addWidget(location_group)

        # Filename section
        filename_group = QGroupBox("Filename")
        filename_layout = QFormLayout(filename_group)

        self.name_edit = QLineEdit()
        self.name_edit.setText(self.suggested_name)
        filename_layout.addRow("Name:", self.name_edit)

        layout.addWidget(filename_group)

        # Format section (for images)
        if self.export_type == "image":
            format_group = QGroupBox("Image Settings")
            format_layout = QFormLayout(format_group)

            self.format_combo = QComboBox()
            self.format_combo.addItems(["PNG", "JPEG", "TIFF (multi-page)"])
            format_layout.addRow("Format:", self.format_combo)

            self.quality_combo = QComboBox()
            for quality in ImageQuality:
                label = f"{quality.value.title()} ({quality.dpi} DPI)"
                self.quality_combo.addItem(label, quality)

            # Set current quality
            current_idx = list(ImageQuality).index(self.settings.image_quality)
            self.quality_combo.setCurrentIndex(current_idx)

            format_layout.addRow("Quality:", self.quality_combo)

            layout.addWidget(format_group)

        # Preview of full path
        preview_group = QGroupBox("Output")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_label = QLabel()
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("color: #666;")
        preview_layout.addWidget(self.preview_label)

        layout.addWidget(preview_group)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Connect signals for preview update
        self.name_edit.textChanged.connect(self._update_preview)
        if self.export_type == "image":
            self.format_combo.currentIndexChanged.connect(self._update_preview)

        self._update_preview()

    def _browse_directory(self) -> None:
        """Open directory browser."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            self.dir_edit.text(),
        )
        if directory:
            self.dir_edit.setText(directory)
            self._update_preview()

    def _on_recent_clicked(self, item: QListWidgetItem) -> None:
        """Handle click on recent directory."""
        self.dir_edit.setText(item.text())
        self._update_preview()

    def _update_preview(self) -> None:
        """Update the output path preview."""
        path = self.get_output_path()
        self.preview_label.setText(str(path))

    def get_output_path(self) -> Path:
        """Get the full output path."""
        directory = Path(self.dir_edit.text())
        filename = self.name_edit.text()

        # Add extension
        if self.export_type == "pdf":
            if not filename.lower().endswith(".pdf"):
                filename += ".pdf"
        else:
            ext = self.get_image_format()
            if not filename.lower().endswith(f".{ext}"):
                filename += f".{ext}"

        return directory / filename

    def get_image_format(self) -> Literal["png", "jpeg", "tiff"]:
        """Get selected image format."""
        if self.export_type != "image":
            return "png"

        idx = self.format_combo.currentIndex()
        formats: list[Literal["png", "jpeg", "tiff"]] = ["png", "jpeg", "tiff"]
        return formats[idx]

    def get_image_quality(self) -> ImageQuality:
        """Get selected image quality."""
        if self.export_type != "image":
            return self.settings.image_quality
        return self.quality_combo.currentData()
