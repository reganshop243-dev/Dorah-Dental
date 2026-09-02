web: python manage.py collectstatic --noinput && python manage.py migrate --noinput && gunicorn --bind 0.0.0.0:$PORT dental_clinic.wsgi:application
