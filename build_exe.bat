@echo off
echo ============================================================
echo   🦷 Building Dora's Dental Gem - Standalone EXE
echo ============================================================
echo.

REM Step 1: Install Python dependencies
echo Step 1: Installing Python dependencies...
pip install -r requirements.txt
pip install pyinstaller waitress whitenoise

REM Step 2: Download static files
echo.
echo Step 2: Downloading static files for offline use...
python download_all_static.py

REM Step 3: Clean previous builds
echo.
echo Step 3: Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del *.spec

REM Step 4: Build the executable
echo.
echo Step 4: Building executable...
pyinstaller --onefile ^
    --add-data "templates;templates" ^
    --add-data "appointments;appointments" ^
    --add-data "patients;patients" ^
    --add-data "billing;billing" ^
    --add-data "core;core" ^
    --add-data "inventory;inventory" ^
    --add-data "dental_clinic;dental_clinic" ^
    --add-data "data;data" ^
    --add-data "manage.py;." ^
    --add-data "static;static" ^
    --hidden-import "waitress" ^
    --hidden-import "whitenoise" ^
    --hidden-import "crispy_forms" ^
    --hidden-import "crispy_bootstrap5" ^
    --name "DoraDentalGem" ^
    launcher.py

echo.
echo ============================================================
echo   ✅ Build Complete!
echo   📁 Executable: dist\DoraDentalGem.exe
echo   📂 Size: ~50-80MB
echo ============================================================
echo.
echo   To run the application:
echo   1. Copy DoraDentalGem.exe to any folder
echo   2. Double-click to run
echo   3. The data folder will be created automatically
echo ============================================================
pause