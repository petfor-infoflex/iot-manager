@echo off
echo ============================================
echo   IoT Device Manager - Build Script
echo ============================================
echo.

:: Change to script directory
cd /d "%~dp0"

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Install/upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

:: Install requirements
echo Installing requirements...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install requirements
    pause
    exit /b 1
)

:: Install PyInstaller if not present
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

:: Generate icon if it doesn't exist
if not exist "assets\icon.ico" (
    echo Generating icon...
    python create_icon.py
)

:: Create dist folder if it doesn't exist
if not exist "dist" mkdir dist

:: Build the executable
echo.
echo ============================================
echo   Building executable...
echo ============================================
echo.

pyinstaller --noconfirm ^
    --onefile ^
    --windowed ^
    --name "IoTDeviceManager" ^
    --icon "assets\icon.ico" ^
    --add-data "assets;assets" ^
    --hidden-import "pystray._win32" ^
    --hidden-import "PIL._tkinter_finder" ^
    --hidden-import "zeroconf._utils.ipaddress" ^
    --hidden-import "zeroconf._handlers.answers" ^
    src\iot_manager\__main__.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Build complete!
echo ============================================
echo.
echo Executable created: dist\IoTDeviceManager.exe
echo.

:: Deactivate virtual environment
deactivate

pause
