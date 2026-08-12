@echo off
chcp 65001 > nul
title Dora's Dental Gem - Clinic Management System

echo ============================================================
echo   🦷 DORA'S DENTAL GEM - Clinic Management System
echo ============================================================
echo.

REM Check if Python is installed
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed!
    echo.
    echo Please install Python from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

REM Check if Django is installed
python -c "import django" > nul 2>&1
if errorlevel 1 (
    echo 📦 Installing Django and dependencies...
    pip install django django-crispy-forms crispy-bootstrap5 Pillow requests
    echo ✅ Dependencies installed
)

REM Run migrations if needed
if not exist "data\dental_clinic.db" (
    echo 📊 Setting up database...
    python manage.py makemigrations
    python manage.py migrate
    echo ✅ Database setup complete
)

echo.
echo ============================================================
echo   🚀 Starting Dora's Dental Gem...
echo ============================================================
echo.
echo   📱 Access at: http://localhost:8000
echo   ❌ Press Ctrl+C to stop the server
echo ============================================================
echo.

python manage.py runserver

pause