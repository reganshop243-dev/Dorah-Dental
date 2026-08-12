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

REM Check if virtual environment exists, if not create it
if not exist "venv\Scripts\python.exe" (
    echo 📦 Creating virtual environment...
    python -m venv venv
    echo ✅ Virtual environment created
)

REM Activate virtual environment
echo 🔄 Activating virtual environment...
call venv\Scripts\activate

REM Check if dependencies are installed
echo 🔍 Checking dependencies...
python -c "import django" > nul 2>&1
if errorlevel 1 (
    echo 📦 Installing dependencies...
    pip install -r requirements.txt
    echo ✅ Dependencies installed
)

REM Check if database exists, if not run migrations
if not exist "data\dental_clinic.db" (
    echo 📊 Setting up database...
    python manage.py makemigrations
    python manage.py migrate
    echo ✅ Database setup complete
)

REM Check if superuser exists
echo 🔑 Checking for admin user...
python manage.py shell -c "from django.contrib.auth.models import User; exit(0) if User.objects.filter(is_superuser=True).exists() else exit(1)" > nul 2>&1
if errorlevel 1 (
    echo.
    echo ⚠️  No admin user found!
    echo Please create an admin user:
    python manage.py createsuperuser
)

echo.
echo ============================================================
echo   🚀 Starting Dora's Dental Gem Server...
echo ============================================================
echo.
echo   📱 Access at: http://localhost:8000
echo   🔑 Login with your admin credentials
echo   ❌ Press Ctrl+C to stop the server
echo ============================================================
echo.

REM Start the server
python manage.py runserver

pause