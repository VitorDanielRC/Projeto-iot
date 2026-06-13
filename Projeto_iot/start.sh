#!/usr/bin/env bash
set -o errexit

python manage.py migrate --fake-initial --no-input
python manage.py create_admin_from_env
python -m gunicorn Projeto_iot.wsgi:application
