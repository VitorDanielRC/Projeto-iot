#!/usr/bin/env bash
set -o errexit

python manage.py migrate --no-input
python -m gunicorn Projeto_iot.wsgi:application
