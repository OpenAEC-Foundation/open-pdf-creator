# Open PDF Creator

Cross-platform virtual PDF printer and PDF combiner. Similar to PDFCreator, but open source and available for both Windows and Linux.

## Features

- **Virtual PDF Printer**: Appears as a printer in your system (Windows installer, Linux Snap)
- **PDF Combiner**: Drag and drop multiple PDFs to combine them
- **Multiple Output Formats**: Export as PDF, PNG, JPEG, or TIFF
- **Page Management**: Rotate pages, select page ranges, reorder documents
- **Quality Settings**: Configurable DPI and compression settings
- **System Tray**: Minimize to system tray for quick access

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/OpenAEC-Foundation/open-pdf-creator.git
cd open-pdf-creator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -e .

# Run the application
open-pdf-creator
# or: python -m open_pdf_creator
```

### System Requirements

- Python 3.11 or higher
- Poppler (for PDF to image conversion)

#### Linux (Ubuntu/Debian)
```bash
sudo apt install poppler-utils
```

#### macOS
```bash
brew install poppler
```

#### Windows
Download Poppler from [poppler releases](https://github.com/oschwartz10612/poppler-windows/releases) and add to PATH.

## Usage

### GUI Application

1. **Add Files**: Click "Add Files" or drag and drop PDF files into the window
2. **Arrange**: Drag files to reorder them
3. **Rotate**: Use the rotate buttons on each file or right-click for options
4. **Export**: Click "Export PDF" to save combined PDF, or "Export Images" for image output

### Command Line

```bash
# Open with files
open-pdf-creator file1.pdf file2.pdf

# The application will open with the specified files loaded
```

## Development

### Setup Development Environment

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check src/

# Run type checker
mypy src/
```

### Project Structure

```
open-pdf-creator/
├── src/open_pdf_creator/
│   ├── core/           # Core functionality
│   │   ├── settings.py     # Settings management
│   │   ├── pdf_processor.py # PDF operations
│   │   └── image_converter.py # Image export
│   ├── gui/            # GUI components
│   │   ├── main_window.py   # Main window
│   │   ├── combiner_widget.py # PDF combiner
│   │   ├── save_dialog.py   # Export dialog
│   │   └── settings_dialog.py # Settings dialog
│   ├── printer/        # Printer drivers (planned)
│   │   ├── windows/    # Windows port monitor
│   │   └── linux/      # CUPS backend
│   └── service/        # Background services (planned)
├── tests/              # Test files
└── installer/          # Installer scripts
    ├── windows/        # Inno Setup
    └── linux/snap/     # Snap packaging
```

## Roadmap

- [x] Core PDF processing
- [x] GUI application with drag & drop
- [x] PDF combiner
- [x] Image export (PNG, JPEG, TIFF)
- [x] Settings management
- [ ] Linux CUPS printer backend
- [ ] Snap packaging
- [ ] Windows virtual printer driver
- [ ] Windows installer (Inno Setup)
- [ ] Auto-save print jobs
- [ ] Print job batching

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Credits

Developed by [OpenAEC Foundation](https://openaec.org)
