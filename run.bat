@echo off
echo ============================================================
echo   🦷 DORA'S DENTAL GEM - Clinic Management System
echo ============================================================
echo.
echo Starting application...
echo.

REM Set the data directory
set DENTAL_CLINIC_DATA_DIR=%CD%\data

REM Run the launcher
python launcher.py

pause