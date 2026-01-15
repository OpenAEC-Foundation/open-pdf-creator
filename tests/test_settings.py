"""Tests for settings module."""

import tempfile
from pathlib import Path

import pytest

from open_pdf_creator.core.settings import Settings, OutputFormat, ImageQuality


class TestSettings:
    """Tests for Settings class."""

    def test_default_settings(self):
        """Test default settings values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.json"
            settings = Settings(_config_path=config_path)

            assert settings.default_format == OutputFormat.PDF
            assert settings.image_quality == ImageQuality.HIGH
            assert settings.auto_save is False
            assert settings.show_preview is True
            assert settings.printer_name == "Open PDF Creator"

    def test_save_and_load(self):
        """Test saving and loading settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.json"

            # Create and save settings
            settings = Settings(_config_path=config_path)
            settings.default_format = OutputFormat.PNG
            settings.image_quality = ImageQuality.MAXIMUM
            settings.printer_name = "Test Printer"
            settings.save()

            # Load settings
            loaded = Settings.load(config_path)

            assert loaded.default_format == OutputFormat.PNG
            assert loaded.image_quality == ImageQuality.MAXIMUM
            assert loaded.printer_name == "Test Printer"

    def test_recent_directories(self):
        """Test recent directories management."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.json"
            settings = Settings(_config_path=config_path)

            # Add directories
            settings.add_recent_directory("/path/one")
            settings.add_recent_directory("/path/two")
            settings.add_recent_directory("/path/three")

            assert len(settings.recent_directories) == 3
            assert settings.recent_directories[0].endswith("three")
            assert settings.recent_directories[1].endswith("two")
            assert settings.recent_directories[2].endswith("one")

    def test_recent_directories_no_duplicates(self):
        """Test that duplicate directories are moved to front."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.json"
            settings = Settings(_config_path=config_path)

            settings.add_recent_directory("/path/one")
            settings.add_recent_directory("/path/two")
            settings.add_recent_directory("/path/one")  # Duplicate

            assert len(settings.recent_directories) == 2
            assert settings.recent_directories[0].endswith("one")

    def test_image_quality_dpi(self):
        """Test image quality DPI values."""
        assert ImageQuality.LOW.dpi == 72
        assert ImageQuality.MEDIUM.dpi == 150
        assert ImageQuality.HIGH.dpi == 300
        assert ImageQuality.MAXIMUM.dpi == 600

    def test_image_quality_jpeg(self):
        """Test image quality JPEG values."""
        assert ImageQuality.LOW.jpeg_quality == 60
        assert ImageQuality.MEDIUM.jpeg_quality == 80
        assert ImageQuality.HIGH.jpeg_quality == 90
        assert ImageQuality.MAXIMUM.jpeg_quality == 95
