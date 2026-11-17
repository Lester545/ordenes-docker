# Imagen de produccion del frontend Django (Grupo 5).
# Primero requirements.txt para aprovechar la cache de capas.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    API_URL=http://api:5000 \
    DJANGO_SECRET_KEY=clave-de-desarrollo-cambiar-en-produccion \
    DJANGO_ALLOWED_HOSTS=* \
    DJANGO_DEBUG=0

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Usuario sin privilegios para el proceso del servidor web.
RUN useradd --system --uid 10002 web \
    && mkdir -p /app/staticfiles \
    && chown -R web:web /app

COPY --chown=web:web . .

USER web

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=10 \
    CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8000/', timeout=3)" || exit 1

CMD ["gunicorn", "--workers", "2", "--threads", "4", "--bind", "0.0.0.0:8000", "config.wsgi:application"]
