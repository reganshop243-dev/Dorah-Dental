import os

if __name__ == "__main__":
    port = os.environ.get('PORT', 8000)
    os.system(f"gunicorn --bind 0.0.0.0:{port} dental_clinic.wsgi:application")