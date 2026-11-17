"""URLs de la aplicacion de ordenes."""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista_ordenes, name="lista_ordenes"),
    path("ordenes/nueva/", views.nueva_orden, name="nueva_orden"),
    path("ordenes/<int:orden_id>/", views.detalle_orden, name="detalle_orden"),
    path("ordenes/<int:orden_id>/editar/", views.editar_orden, name="editar_orden"),
    path("ordenes/<int:orden_id>/eliminar/", views.eliminar_orden, name="eliminar_orden"),
    path("ordenes/<int:orden_id>/detalles/nuevo/", views.nuevo_detalle, name="nuevo_detalle"),
    path("detalles/<int:detalle_id>/editar/", views.editar_detalle, name="editar_detalle"),
    path("detalles/<int:detalle_id>/eliminar/", views.eliminar_detalle, name="eliminar_detalle"),
]
