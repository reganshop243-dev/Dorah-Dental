#!/bin/bash
gunicorn --bind 0.0.0.0:$PORT dental_clinic.wsgi:application