"""Settings management for Open PDF Creator."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir, user_documents_dir


class OutputFormat(str, Enum):
    """Supported output formats."""
    PDF = "pdf"
    PNG = "png"
    JPEG = "jpeg"
    TIFF = "tiff"


class ImageQuality(str, Enum):
    """Image quality presets."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"

    @property
    def dpi(self) -> int:
        """Return DPI for quality level."""
        return {
            ImageQuality.LOW: 72,
            ImageQuality.MEDIUM: 150,
            ImageQuality.HIGH: 300,
            ImageQuality.MAXIMUM: 600,
        }[self]

    @property
    def jpeg_quality(self) -> int:
        """Return JPEG quality (0-100) for quality level."""
        return {
            ImageQuality.LOW: 60,
            ImageQuality.MEDIUM: 80,
            ImageQuality.HIGH: 90,
            ImageQuality.MAXIMUM: 95,
        }[self]


@dataclass
class Settings:
    """Application settings."""

    # Output settings
    default_output_dir: str = ""
    default_format: OutputFormat = OutputFormat.PDF
    filename_template: str = "{title}_{date}"

    # Image settings
    image_quality: ImageQuality = ImageQuality.HIGH

    # Behavior settings
    auto_save: bool = False
    show_preview: bool = True
    remember_last_dir: bool = True
    last_used_dir: str = ""

    # Recent directories
    recent_directories: list[str] = field(default_factory=list)
    max_recent_dirs: int = 10

    # Printer settings
    printer_name: str = "Open PDF Creator"

    # Window settings
    window_geometry: dict[str, int] = field(default_factory=lambda: {
        "x": 100, "y": 100, "width": 900, "height": 700
    })
    start_minimized: bool = False
    minimize_to_tray: bool = True

    _config_path: Path = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Initialize config path and default output directory."""
        if self._config_path is None:
            config_dir = Path(user_config_dir("open-pdf-creator", "OpenAEC"))
            config_dir.mkdir(parents=True, exist_ok=True)
            self._config_path = config_dir / "settings.json"

        if not self.default_output_dir:
            self.default_output_dir = str(Path(user_documents_dir()) / "PDFs")

        # Ensure output directory exists
        Path(self.default_output_dir).mkdir(parents=True, exist_ok=True)

    @classmethod
    def load(cls, config_path: Path | None = None) -> Settings:
        """Load settings from JSON file."""
        settings = cls(_config_path=config_path)

        if settings._config_path.exists():
            try:
                with open(settings._config_path, encoding="utf-8") as f:
                    data = json.load(f)

                # Handle enum fields
                if "default_format" in data:
                    data["default_format"] = OutputFormat(data["default_format"])
                if "image_quality" in data:
                    data["image_quality"] = ImageQuality(data["image_quality"])

                # Update settings with loaded values
                for key, value in data.items():
                    if hasattr(settings, key) and not key.startswith("_"):
                        setattr(settings, key, value)
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                print(f"Warning: Could not load settings: {e}")

        return settings

    def save(self) -> None:
        """Save settings to JSON file."""
        data = {}
        for key, value in asdict(self).items():
            if key.startswith("_"):
                continue
            if isinstance(value, Enum):
                data[key] = value.value
            else:
                data[key] = value

        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_recent_directory(self, directory: str) -> None:
        """Add a directory to recent directories list."""
        dir_path = str(Path(directory).resolve())

        # Remove if already exists
        if dir_path in self.recent_directories:
            self.recent_directories.remove(dir_path)

        # Add to front
        self.recent_directories.insert(0, dir_path)

        # Trim to max size
        self.recent_directories = self.recent_directories[:self.max_recent_dirs]

        # Update last used directory
        if self.remember_last_dir:
            self.last_used_dir = dir_path

    def get_output_directory(self) -> Path:
        """Get the output directory to use."""
        if self.remember_last_dir and self.last_used_dir:
            path = Path(self.last_used_dir)
            if path.exists():
                return path
        return Path(self.default_output_dir)

    def to_dict(self) -> dict[str, Any]:
        """Convert settings to dictionary."""
        result = {}
        for key, value in asdict(self).items():
            if key.startswith("_"):
                continue
            if isinstance(value, Enum):
                result[key] = value.value
            else:
                result[key] = value
        return result
