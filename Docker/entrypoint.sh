#!/bin/bash
set -e

echo "Aplicando migraciones de base de datos..."
flask db upgrade

echo "Iniciando Gunicorn en el puerto ${PORT:-8000}..."
exec gunicorn backend.wsgi:app \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --threads 4 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
