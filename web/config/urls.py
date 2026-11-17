"""Rutas URL del proyecto Django."""

from django.urls import include, path

urlpatterns = [
    path("", include("ordenes.urls")),
]
