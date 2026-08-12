#!/bin/sh
set -eu

echo "Inicializando Rescue Backend..."
echo "Base de datos: ${DATABASE_NAME:-rescue}"

wait_for_mongo() {
    max_attempts="${MONGO_CONNECT_ATTEMPTS:-60}"
    attempt=1

    echo "Esperando a MongoDB..."
    while [ "$attempt" -le "$max_attempts" ]; do
        if python -c '
import os
import sys
from pymongo import MongoClient

try:
    uri = os.environ.get("MONGO_URI", "mongodb://mongodb:27017/rescue_db")
    client = MongoClient(uri, serverSelectionTimeoutMS=2000)
    client.admin.command("ping")
    client.close()
except Exception:
    sys.exit(1)
'; then
            echo "MongoDB disponible."
            return 0
        fi

        echo "MongoDB no disponible (intento ${attempt}/${max_attempts})."
        attempt=$((attempt + 1))
        sleep 2
    done

    echo "MongoDB no respondio despues de ${max_attempts} intentos." >&2
    return 1
}

wait_for_mongo

echo "Verificando administrador inicial..."
if ! python -c '
from scripts.init_admin import init_admin
init_admin()
'; then
    echo "No se pudo inicializar el administrador; el backend continuara." >&2
fi

workers="${GUNICORN_WORKERS:-3}"
timeout="${GUNICORN_TIMEOUT:-60}"

echo "Iniciando Gunicorn en 0.0.0.0:5002 con ${workers} workers."
exec gunicorn \
    --bind 0.0.0.0:5002 \
    --workers "$workers" \
    --worker-class sync \
    --timeout "$timeout" \
    --keep-alive 2 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    --log-level "${GUNICORN_LOG_LEVEL:-info}" \
    "app:create_app()"
