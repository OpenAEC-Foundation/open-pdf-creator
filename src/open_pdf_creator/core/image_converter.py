"""Image conversion functionality for PDF to image export."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pdf2image import convert_from_path
from PIL import Image

from open_pdf_creator.core.settings import ImageQuality

ImageFormat = Literal["png", "jpeg", "tiff"]


class ImageConverter:
    """Convert PDF pages to images."""

    @staticmethod
    def pdf_to_images(
        pdf_path: Path,
        output_dir: Path,
        format: ImageFormat = "png",
        quality: ImageQuality = ImageQuality.HIGH,
        page_numbers: list[int] | None = None,
    ) -> list[Path]:
        """Convert PDF pages to images.

        Args:
            pdf_path: Path to source PDF
            output_dir: Directory for output images
            format: Output image format (png, jpeg, tiff)
            quality: Image quality preset
            page_numbers: Specific pages to convert (None = all)

        Returns:
            List of paths to created images
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        dpi = quality.dpi
        stem = pdf_path.stem

        # Convert PDF to PIL images
        if page_numbers:
            # pdf2image uses 1-indexed pages
            first_page = min(page_numbers) + 1
            last_page = max(page_numbers) + 1
            images = convert_from_path(
                str(pdf_path),
                dpi=dpi,
                first_page=first_page,
                last_page=last_page,
            )
            # Filter to only requested pages
            page_set = set(page_numbers)
            images = [
                img for i, img in enumerate(images, first_page - 1)
                if i in page_set
            ]
        else:
            images = convert_from_path(str(pdf_path), dpi=dpi)

        output_paths = []
        for i, image in enumerate(images):
            page_num = page_numbers[i] + 1 if page_numbers else i + 1
            output_path = output_dir / f"{stem}_page_{page_num:03d}.{format}"

            save_kwargs = ImageConverter._get_save_kwargs(format, quality)
            image.save(output_path, **save_kwargs)
            output_paths.append(output_path)

        return output_paths

    @staticmethod
    def pdf_to_single_image(
        pdf_path: Path,
        output_path: Path,
        format: ImageFormat = "png",
        quality: ImageQuality = ImageQuality.HIGH,
        page_number: int = 0,
    ) -> Path:
        """Convert a single PDF page to an image.

        Args:
            pdf_path: Path to source PDF
            output_path: Path for output image
            format: Output image format
            quality: Image quality preset
            page_number: Page to convert (0-indexed)

        Returns:
            Path to created image
        """
        dpi = quality.dpi

        # Convert specific page
        images = convert_from_path(
            str(pdf_path),
            dpi=dpi,
            first_page=page_number + 1,
            last_page=page_number + 1,
        )

        if not images:
            raise ValueError(f"Could not convert page {page_number}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        save_kwargs = ImageConverter._get_save_kwargs(format, quality)
        images[0].save(output_path, **save_kwargs)

        return output_path

    @staticmethod
    def pdf_to_multipage_tiff(
        pdf_path: Path,
        output_path: Path,
        quality: ImageQuality = ImageQuality.HIGH,
        page_numbers: list[int] | None = None,
    ) -> Path:
        """Convert PDF to multi-page TIFF.

        Args:
            pdf_path: Path to source PDF
            output_path: Path for output TIFF
            quality: Image quality preset
            page_numbers: Specific pages to convert (None = all)

        Returns:
            Path to created TIFF
        """
        dpi = quality.dpi

        if page_numbers:
            first_page = min(page_numbers) + 1
            last_page = max(page_numbers) + 1
            images = convert_from_path(
                str(pdf_path),
                dpi=dpi,
                first_page=first_page,
                last_page=last_page,
            )
            page_set = set(page_numbers)
            images = [
                img for i, img in enumerate(images, first_page - 1)
                if i in page_set
            ]
        else:
            images = convert_from_path(str(pdf_path), dpi=dpi)

        if not images:
            raise ValueError("No pages to convert")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save as multi-page TIFF
        if len(images) == 1:
            images[0].save(output_path, format="TIFF", compression="tiff_lzw")
        else:
            images[0].save(
                output_path,
                format="TIFF",
                compression="tiff_lzw",
                save_all=True,
                append_images=images[1:],
            )

        return output_path

    @staticmethod
    def get_page_thumbnail(
        pdf_path: Path,
        page_number: int = 0,
        max_size: tuple[int, int] = (200, 280),
    ) -> bytes:
        """Get a thumbnail image of a PDF page.

        Args:
            pdf_path: Path to PDF
            page_number: Page number (0-indexed)
            max_size: Maximum thumbnail size

        Returns:
            PNG image bytes
        """
        # Use low DPI for thumbnails
        images = convert_from_path(
            str(pdf_path),
            dpi=72,
            first_page=page_number + 1,
            last_page=page_number + 1,
        )

        if not images:
            raise ValueError(f"Could not get thumbnail for page {page_number}")

        image = images[0]
        image.thumbnail(max_size, Image.Resampling.LANCZOS)

        import io
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    @staticmethod
    def _get_save_kwargs(
        format: ImageFormat,
        quality: ImageQuality,
    ) -> dict:
        """Get PIL save kwargs for format and quality."""
        if format == "png":
            return {
                "format": "PNG",
                "optimize": True,
            }
        elif format == "jpeg":
            return {
                "format": "JPEG",
                "quality": quality.jpeg_quality,
                "optimize": True,
            }
        elif format == "tiff":
            return {
                "format": "TIFF",
                "compression": "tiff_lzw",
            }
        else:
            raise ValueError(f"Unsupported format: {format}")
