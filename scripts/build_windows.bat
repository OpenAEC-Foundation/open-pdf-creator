@echo off
REM Build standalone Windows executable for Open PDF Creator
REM
REM This creates a fully isolated application with its own Python runtime.
REM No system Python required to run the application.
REM
REM Requirements:
REM   - Python 3.11+
REM   - pip install pyinstaller
REM
REM Output: dist/OpenPDFCreator/

echo ============================================
echo Open PDF Creator - Windows Build
echo ============================================

cd /d "%~dp0\.."

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found
    exit /b 1
)

REM Create/activate virtual environment
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -e ".[dev]" pyinstaller

REM Build with PyInstaller
echo Building standalone application...
pyinstaller open_pdf_creator.spec --clean

echo.
echo ============================================
echo Build complete!
echo Output: dist\OpenPDFCreator\
echo ============================================

REM Create installer (optional, requires Inno Setup)
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    echo Creating installer...
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\windows\setup.iss
    echo Installer created: dist\OpenPDFCreator-Setup.exe
)
