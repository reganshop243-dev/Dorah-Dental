@echo off
echo ============================================================
echo   Creating Dora's Dental Gem Installer
echo ============================================================
echo.

REM Create the application folder
if exist DoraDentalGem_Setup rmdir /s /q DoraDentalGem_Setup
mkdir DoraDentalGem_Setup

REM Copy the executable
copy dist\DoraDentalGem.exe DoraDentalGem_Setup\

REM Copy start script
copy DoraDentalGem_App\start.bat DoraDentalGem_Setup\

REM Copy README
copy DoraDentalGem_App\README.txt DoraDentalGem_Setup\

echo.
echo ============================================================
echo   ✅ Installer folder created: DoraDentalGem_Setup
echo   📁 Location: DoraDentalGem_Setup\
echo   📦 Size: ~50-80MB
echo ============================================================
echo.
echo   To distribute:
echo   1. Zip the DoraDentalGem_Setup folder
echo   2. Share the zip file
echo   3. Or copy the folder to a USB drive
echo ============================================================
pause