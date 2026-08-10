#!/usr/bin/env python
"""
Dora's Dental Gem - Launcher for Standalone EXE
"""
import os
import sys
import subprocess
import webbrowser
import threading
import time
import shutil
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def get_data_dir():
    """Get the data directory"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_dir = os.path.dirname(sys.executable)
    else:
        # Running as script
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

def run_migrations():
    """Run Django migrations"""
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dental_clinic.settings')
        import django
        django.setup()
        from django.core.management import execute_from_command_line
        print("Running database migrations...")
        execute_from_command_line(['manage.py', 'migrate', '--noinput'])
        return True
    except Exception as e:
        print(f"Migration error: {e}")
        return False

def create_superuser():
    """Create superuser if none exists"""
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dental_clinic.settings')
        import django
        django.setup()
        from django.contrib.auth.models import User
        from core.models import UserProfile
        
        if not User.objects.filter(is_superuser=True).exists():
            print("Creating admin user...")
            username = input("Enter admin username: ").strip()
            if not username:
                username = 'admin'
            email = input("Enter admin email: ").strip()
            password = input("Enter admin password: ").strip()
            if not password:
                password = 'admin123'
            
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                first_name='Admin',
                last_name='User'
            )
            # Set role to admin
            profile = user.profile
            profile.role = 'admin'
            profile.save()
            print(f"✅ Admin user '{username}' created successfully!")
        else:
            print("✅ Admin user already exists.")
    except Exception as e:
        print(f"Error creating superuser: {e}")

def main():
    """Main entry point"""
    print("=" * 60)
    print("  🦷 DORA'S DENTAL GEM - Clinic Management System")
    print("=" * 60)
    
    # Set data directory
    data_dir = get_data_dir()
    os.environ['DENTAL_CLINIC_DATA_DIR'] = data_dir
    print(f"📁 Data Directory: {data_dir}")
    
    # Run migrations
    print("📊 Checking database...")
    run_migrations()
    
    # Check if superuser exists
    create_superuser()
    
    # Open browser
    def open_browser():
        time.sleep(2)
        print("🌐 Opening browser...")
        webbrowser.open('http://127.0.0.1:8000')
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Start server
    print("🚀 Starting server...")
    print("   Server: http://127.0.0.1:8000")
    print("   Press Ctrl+C to stop the server")
    print("=" * 60)
    
    # Use waitress to serve
    try:
        from waitress import serve
        from dental_clinic.wsgi import application
        
        serve(application, host='127.0.0.1', port=8000, threads=4)
    except ImportError:
        # Fallback to Django's runserver if waitress not available
        print("Waitress not found, using Django's runserver...")
        from django.core.management import execute_from_command_line
        execute_from_command_line(['manage.py', 'runserver', '127.0.0.1:8000'])

if __name__ == '__main__':
    main()