# Imagen del backend (FastAPI). Al arrancar aplica las migraciones y, si CARGAR_SEED=1, carga
# los datos de demostración (solo con ENTORNO=desarrollo o test).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencias primero, para aprovechar la caché de capas cuando solo cambia el código.
COPY pyproject.toml README.md ./
RUN mkdir app && touch app/__init__.py && pip install . && rm -rf app build *.egg-info

COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
RUN pip install --no-deps . && rm -rf build *.egg-info

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh \
    && useradd --create-home --uid 1000 app
USER app

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/version')"

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
