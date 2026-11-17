"""Configuracion del proyecto Django del frontend de ordenes (Grupo 5).

El frontend nunca se conecta a SQL Server: todas sus operaciones pasan por
la API REST, cuya direccion se recibe en la variable de entorno API_URL.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Clave secreta: en produccion debe venir del entorno (archivo .env).
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "clave-de-desarrollo-cambiar-en-produccion"
)

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"

# Lista de hosts permitidos separada por comas.
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")
    if h.strip()
]

# Direccion de la API REST. Dentro de la red de Docker el servicio se llama "api".
API_URL = os.environ.get("API_URL", "http://api:5000")

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "ordenes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# El frontend no usa el ORM: solo habla con la API. Por eso se deja una
# base sqlite en memoria, suficiente para que Django arranque sin instalar
# un servidor de base de datos adicional.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

LANGUAGE_CODE = "es-es"
TIME_ZONE = "America/Tegucigalpa"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
