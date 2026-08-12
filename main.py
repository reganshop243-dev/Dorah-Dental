"""
Railway Production Entry Point
This runs on Railway, NOT for local desktop use
"""
import os
import sys

if __name__ == "__main__":
    # Get port from Railway
    port = os.environ.get('PORT', 8000)
    
    print("=" * 60)
    print("  🦷 DENTAL CLINIC MANAGEMENT SYSTEM")
    print("  Running on Railway (Production)")
    print("=" * 60)
    print(f"📍 Port: {port}")
    print("=" * 60)
    
    # Run gunicorn (production server)
    os.system(f"gunicorn --bind 0.0.0.0:{port} dental_clinic.wsgi:application")