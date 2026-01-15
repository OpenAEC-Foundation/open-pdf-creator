"""Settings dialog for Open PDF Creator."""

from __future__ import annotations

from copy import deepcopy

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from open_pdf_creator.core.settings import ImageQuality, OutputFormat, Settings


class SettingsDialog(QDialog):
    """Dialog for application settings."""

    def __init__(self, settings: Settings, parent=None) -> None:
        super().__init__(parent)
        self._settings = deepcopy(settings)
        self._original_settings = settings

        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), "General")
        tabs.addTab(self._create_output_tab(), "Output")
        tabs.addTab(self._create_behavior_tab(), "Behavior")
        layout.addWidget(tabs)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.RestoreDefaults).clicked.connect(
            self._restore_defaults
        )
        layout.addWidget(button_box)

    def _create_general_tab(self) -> QWidget:
        """Create the general settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Default directory
        dir_group = QGroupBox("Default Save Location")
        dir_layout = QVBoxLayout(dir_group)

        dir_row = QHBoxLayout()
        self.default_dir_edit = QLineEdit()
        self.default_dir_edit.setText(self._settings.default_output_dir)
        dir_row.addWidget(self.default_dir_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_default_dir)
        dir_row.addWidget(browse_btn)

        dir_layout.addLayout(dir_row)
        layout.addWidget(dir_group)

        # Filename template
        template_group = QGroupBox("Filename Template")
        template_layout = QFormLayout(template_group)

        self.template_edit = QLineEdit()
        self.template_edit.setText(self._settings.filename_template)
        template_layout.addRow("Template:", self.template_edit)

        help_label = QLabel(
            "Available placeholders: {title}, {date}, {time}, {datetime}"
        )
        help_label.setStyleSheet("color: #666; font-size: 11px;")
        template_layout.addRow("", help_label)

        layout.addWidget(template_group)

        # Printer settings
        printer_group = QGroupBox("Printer")
        printer_layout = QFormLayout(printer_group)

        self.printer_name_edit = QLineEdit()
        self.printer_name_edit.setText(self._settings.printer_name)
        printer_layout.addRow("Printer name:", self.printer_name_edit)

        layout.addWidget(printer_group)

        layout.addStretch()
        return tab

    def _create_output_tab(self) -> QWidget:
        """Create the output settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Default format
        format_group = QGroupBox("Default Output Format")
        format_layout = QFormLayout(format_group)

        self.format_combo = QComboBox()
        for fmt in OutputFormat:
            self.format_combo.addItem(fmt.value.upper(), fmt)

        current_idx = list(OutputFormat).index(self._settings.default_format)
        self.format_combo.setCurrentIndex(current_idx)
        format_layout.addRow("Format:", self.format_combo)

        layout.addWidget(format_group)

        # Image quality
        quality_group = QGroupBox("Image Export Quality")
        quality_layout = QFormLayout(quality_group)

        self.quality_combo = QComboBox()
        for quality in ImageQuality:
            label = f"{quality.value.title()} ({quality.dpi} DPI)"
            self.quality_combo.addItem(label, quality)

        current_idx = list(ImageQuality).index(self._settings.image_quality)
        self.quality_combo.setCurrentIndex(current_idx)
        quality_layout.addRow("Quality:", self.quality_combo)

        quality_help = QLabel(
            "Higher quality produces larger files"
        )
        quality_help.setStyleSheet("color: #666; font-size: 11px;")
        quality_layout.addRow("", quality_help)

        layout.addWidget(quality_group)

        layout.addStretch()
        return tab

    def _create_behavior_tab(self) -> QWidget:
        """Create the behavior settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Save behavior
        save_group = QGroupBox("Save Behavior")
        save_layout = QVBoxLayout(save_group)

        self.auto_save_check = QCheckBox("Auto-save without showing dialog")
        self.auto_save_check.setChecked(self._settings.auto_save)
        save_layout.addWidget(self.auto_save_check)

        self.remember_dir_check = QCheckBox("Remember last used directory")
        self.remember_dir_check.setChecked(self._settings.remember_last_dir)
        save_layout.addWidget(self.remember_dir_check)

        self.show_preview_check = QCheckBox("Show page preview in combiner")
        self.show_preview_check.setChecked(self._settings.show_preview)
        save_layout.addWidget(self.show_preview_check)

        layout.addWidget(save_group)

        # Window behavior
        window_group = QGroupBox("Window Behavior")
        window_layout = QVBoxLayout(window_group)

        self.start_minimized_check = QCheckBox("Start minimized")
        self.start_minimized_check.setChecked(self._settings.start_minimized)
        window_layout.addWidget(self.start_minimized_check)

        self.minimize_to_tray_check = QCheckBox("Minimize to system tray")
        self.minimize_to_tray_check.setChecked(self._settings.minimize_to_tray)
        window_layout.addWidget(self.minimize_to_tray_check)

        layout.addWidget(window_group)

        # Recent directories
        recent_group = QGroupBox("Recent Directories")
        recent_layout = QFormLayout(recent_group)

        self.max_recent_spin = QSpinBox()
        self.max_recent_spin.setRange(1, 20)
        self.max_recent_spin.setValue(self._settings.max_recent_dirs)
        recent_layout.addRow("Maximum entries:", self.max_recent_spin)

        clear_recent_btn = QPushButton("Clear Recent Directories")
        clear_recent_btn.clicked.connect(self._clear_recent)
        recent_layout.addRow("", clear_recent_btn)

        layout.addWidget(recent_group)

        layout.addStretch()
        return tab

    def _browse_default_dir(self) -> None:
        """Browse for default directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Default Save Directory",
            self.default_dir_edit.text(),
        )
        if directory:
            self.default_dir_edit.setText(directory)

    def _clear_recent(self) -> None:
        """Clear recent directories."""
        self._settings.recent_directories = []

    def _restore_defaults(self) -> None:
        """Restore default settings."""
        defaults = Settings()

        self.default_dir_edit.setText(defaults.default_output_dir)
        self.template_edit.setText(defaults.filename_template)
        self.printer_name_edit.setText(defaults.printer_name)

        self.format_combo.setCurrentIndex(
            list(OutputFormat).index(defaults.default_format)
        )
        self.quality_combo.setCurrentIndex(
            list(ImageQuality).index(defaults.image_quality)
        )

        self.auto_save_check.setChecked(defaults.auto_save)
        self.remember_dir_check.setChecked(defaults.remember_last_dir)
        self.show_preview_check.setChecked(defaults.show_preview)
        self.start_minimized_check.setChecked(defaults.start_minimized)
        self.minimize_to_tray_check.setChecked(defaults.minimize_to_tray)
        self.max_recent_spin.setValue(defaults.max_recent_dirs)

    def get_settings(self) -> Settings:
        """Get the modified settings."""
        self._settings.default_output_dir = self.default_dir_edit.text()
        self._settings.filename_template = self.template_edit.text()
        self._settings.printer_name = self.printer_name_edit.text()

        self._settings.default_format = self.format_combo.currentData()
        self._settings.image_quality = self.quality_combo.currentData()

        self._settings.auto_save = self.auto_save_check.isChecked()
        self._settings.remember_last_dir = self.remember_dir_check.isChecked()
        self._settings.show_preview = self.show_preview_check.isChecked()
        self._settings.start_minimized = self.start_minimized_check.isChecked()
        self._settings.minimize_to_tray = self.minimize_to_tray_check.isChecked()
        self._settings.max_recent_dirs = self.max_recent_spin.value()

        return self._settings
