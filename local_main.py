"""
Dental Clinic Management System - Standalone EXE Entry Point
Run: python main.py
"""

import os
import sys
import webbrowser
import time
import socket
import threading
from pathlib import Path

# Determine if running as EXE or script
if getattr(sys, 'frozen', False):
    # Running as EXE
    BASE_DIR = Path(sys._MEIPASS)
    APP_DIR = Path(os.path.dirname(sys.executable))
    DATA_DIR = APP_DIR / "data"
else:
    # Running as script
    BASE_DIR = Path(__file__).parent
    APP_DIR = BASE_DIR
    DATA_DIR = BASE_DIR / "data"

# Create data directory for database and settings
DATA_DIR.mkdir(exist_ok=True)

# Set environment variables
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dental_clinic.settings')
os.environ['DENTAL_CLINIC_DATA_DIR'] = str(DATA_DIR)

# Add base directory to path
sys.path.insert(0, str(BASE_DIR))

def is_port_in_use(port):
    """Check if port is already in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return False
        except socket.error:
            return True

def start_server():
    """Start Django server"""
    os.chdir(BASE_DIR)
    
    if is_port_in_use(8000):
        print("⚠️ Server already running on port 8000")
        webbrowser.open('http://127.0.0.1:8000')
        return False
    
    print("🚀 Starting Dental Clinic Management System...")
    
    # Start Django server
    from django.core.management import execute_from_command_line
    sys.argv = ['manage.py', 'runserver', '127.0.0.1:8000', '--noreload']
    execute_from_command_line(sys.argv)
    
    return True

def open_browser():
    """Open browser after server starts"""
    time.sleep(3)
    webbrowser.open('http://127.0.0.1:8000')

def main():
    print("=" * 60)
    print("  🦷 DENTAL CLINIC MANAGEMENT SYSTEM")
    print("  Version 1.0")
    print("=" * 60)
    print(f"📁 Data Directory: {DATA_DIR}")
    print(f"📁 Application Directory: {APP_DIR}")
    print("=" * 60)
    
    # Run migrations if needed
    try:
        from django.core.management import execute_from_command_line
        sys.argv = ['manage.py', 'migrate', '--noinput']
        execute_from_command_line(sys.argv)
    except:
        pass
    
    # Start server in a thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Open browser
    time.sleep(2)
    webbrowser.open('http://127.0.0.1:8000')
    
    print("\n✅ Server is running!")
    print("📍 Access at: http://127.0.0.1:8000")
    print("❌ Close this window to stop the server")
    
    try:
        # Keep the program running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")

if __name__ == "__main__":
    main()