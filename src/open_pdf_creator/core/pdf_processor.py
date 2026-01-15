"""PDF processing functionality using pypdf and pikepdf."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pikepdf
from pypdf import PdfReader, PdfWriter


@dataclass
class PDFInfo:
    """Information about a PDF file."""
    path: Path
    num_pages: int
    title: str | None
    author: str | None
    creator: str | None
    page_sizes: list[tuple[float, float]]  # (width, height) in points

    @property
    def filename(self) -> str:
        """Get filename without extension."""
        return self.path.stem


@dataclass
class PageSelection:
    """Represents a selection of pages from a PDF."""
    pdf_path: Path
    pages: list[int]  # 0-indexed page numbers
    rotation: int = 0  # Rotation in degrees (0, 90, 180, 270)

    @classmethod
    def all_pages(cls, pdf_path: Path, num_pages: int) -> PageSelection:
        """Create selection for all pages."""
        return cls(pdf_path=pdf_path, pages=list(range(num_pages)))

    @classmethod
    def from_range(cls, pdf_path: Path, page_range: str, num_pages: int) -> PageSelection:
        """Create selection from page range string (e.g., '1-3,5,7-9')."""
        pages = []
        for part in page_range.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-", 1)
                start_idx = int(start) - 1  # Convert to 0-indexed
                end_idx = int(end)  # Exclusive end
                pages.extend(range(max(0, start_idx), min(num_pages, end_idx)))
            else:
                page_idx = int(part) - 1
                if 0 <= page_idx < num_pages:
                    pages.append(page_idx)
        return cls(pdf_path=pdf_path, pages=pages)


class PDFProcessor:
    """PDF processing operations."""

    @staticmethod
    def get_info(pdf_path: Path) -> PDFInfo:
        """Get information about a PDF file."""
        with pikepdf.open(pdf_path) as pdf:
            num_pages = len(pdf.pages)
            metadata = pdf.docinfo or {}

            page_sizes = []
            for page in pdf.pages:
                box = page.mediabox
                width = float(box[2] - box[0])
                height = float(box[3] - box[1])
                page_sizes.append((width, height))

            return PDFInfo(
                path=pdf_path,
                num_pages=num_pages,
                title=str(metadata.get("/Title", "")) or None,
                author=str(metadata.get("/Author", "")) or None,
                creator=str(metadata.get("/Creator", "")) or None,
                page_sizes=page_sizes,
            )

    @staticmethod
    def merge_pdfs(
        selections: list[PageSelection],
        output_path: Path,
        metadata: dict[str, str] | None = None,
    ) -> Path:
        """Merge multiple PDFs or page selections into one PDF.

        Args:
            selections: List of page selections to merge
            output_path: Path for the output PDF
            metadata: Optional metadata to set on output PDF

        Returns:
            Path to the created PDF
        """
        writer = PdfWriter()

        for selection in selections:
            reader = PdfReader(str(selection.pdf_path))

            for page_num in selection.pages:
                if 0 <= page_num < len(reader.pages):
                    page = reader.pages[page_num]

                    # Apply rotation if specified
                    if selection.rotation:
                        page.rotate(selection.rotation)

                    writer.add_page(page)

        # Set metadata
        if metadata:
            writer.add_metadata(metadata)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "wb") as f:
            writer.write(f)

        return output_path

    @staticmethod
    def extract_pages(
        pdf_path: Path,
        page_numbers: list[int],
        output_path: Path,
    ) -> Path:
        """Extract specific pages from a PDF.

        Args:
            pdf_path: Source PDF path
            page_numbers: List of page numbers to extract (0-indexed)
            output_path: Path for the output PDF

        Returns:
            Path to the created PDF
        """
        selection = PageSelection(pdf_path=pdf_path, pages=page_numbers)
        return PDFProcessor.merge_pdfs([selection], output_path)

    @staticmethod
    def rotate_pages(
        pdf_path: Path,
        rotation: int,
        page_numbers: list[int] | None = None,
        output_path: Path | None = None,
    ) -> Path:
        """Rotate pages in a PDF.

        Args:
            pdf_path: Source PDF path
            rotation: Rotation angle (90, 180, 270)
            page_numbers: Pages to rotate (None = all pages)
            output_path: Output path (None = overwrite source)

        Returns:
            Path to the modified PDF
        """
        if output_path is None:
            output_path = pdf_path

        reader = PdfReader(str(pdf_path))
        writer = PdfWriter()

        for i, page in enumerate(reader.pages):
            if page_numbers is None or i in page_numbers:
                page.rotate(rotation)
            writer.add_page(page)

        with open(output_path, "wb") as f:
            writer.write(f)

        return output_path

    @staticmethod
    def split_pdf(pdf_path: Path, output_dir: Path) -> list[Path]:
        """Split PDF into individual pages.

        Args:
            pdf_path: Source PDF path
            output_dir: Directory for output files

        Returns:
            List of paths to created PDFs
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        reader = PdfReader(str(pdf_path))
        stem = pdf_path.stem
        output_paths = []

        for i, page in enumerate(reader.pages, 1):
            writer = PdfWriter()
            writer.add_page(page)

            output_path = output_dir / f"{stem}_page_{i:03d}.pdf"
            with open(output_path, "wb") as f:
                writer.write(f)
            output_paths.append(output_path)

        return output_paths

    @staticmethod
    def compress_pdf(
        pdf_path: Path,
        output_path: Path | None = None,
        image_quality: int = 80,
    ) -> Path:
        """Compress a PDF file.

        Args:
            pdf_path: Source PDF path
            output_path: Output path (None = overwrite source)
            image_quality: JPEG quality for embedded images (0-100)

        Returns:
            Path to compressed PDF
        """
        if output_path is None:
            output_path = pdf_path

        with pikepdf.open(pdf_path) as pdf:
            pdf.save(
                output_path,
                compress_streams=True,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
            )

        return output_path

    @staticmethod
    def get_page_count(pdf_path: Path) -> int:
        """Get number of pages in a PDF."""
        with pikepdf.open(pdf_path) as pdf:
            return len(pdf.pages)

    @staticmethod
    def iter_page_images(
        pdf_path: Path,
        dpi: int = 150,
    ) -> Iterator[tuple[int, bytes]]:
        """Iterate over page images (for preview).

        Yields:
            Tuple of (page_number, png_bytes)
        """
        # This will be implemented with pdf2image
        from pdf2image import convert_from_path

        images = convert_from_path(str(pdf_path), dpi=dpi)
        for i, image in enumerate(images):
            import io
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            yield i, buffer.getvalue()
