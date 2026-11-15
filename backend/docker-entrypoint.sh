#!/bin/sh
# Arranque del contenedor del backend: migraciones, seed opcional y la API.
set -e

alembic upgrade head

if [ "${CARGAR_SEED:-0}" = "1" ]; then
    python -m app.db.seed
fi

exec "$@"
