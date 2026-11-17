# Imagen de produccion de la API REST de ordenes (Grupo 5).
# El orden de las instrucciones esta pensado para aprovechar la cache
# de capas: primero se copia requirements.txt para que la instalacion
# de dependencias solo se repita si ese archivo cambia.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DB_SERVER=db \
    DB_PORT=1433 \
    DB_USER=sa \
    DB_NAME=OrdenesDB

WORKDIR /app

# 1) Dependencias primero: se cachean de forma independiente del codigo.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Usuario sin privilegios y carpeta de trabajo con permisos para el.
RUN useradd --system --uid 10001 api \
    && mkdir -p /app/datos \
    && chown -R api:api /app

# 3) Codigo de la aplicacion.
COPY --chown=api:api app.py .

USER api

EXPOSE 5000

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=10 \
    CMD python -c "import urllib.request as u; u.urlopen('http://localhost:5000/health', timeout=3)" || exit 1

CMD ["gunicorn", "--workers", "2", "--threads", "4", "--bind", "0.0.0.0:5000", "app:app"]
