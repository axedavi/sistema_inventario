#!/usr/bin/env bash
# Script de build para Render (Vista Física de la tesis, sección 10.2.3/10.3.1).
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
