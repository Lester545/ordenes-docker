"""Vistas del frontend de ordenes.

Todas las operaciones se hacen llamando a la API REST con la libreria
requests. El frontend nunca abre una conexion a SQL Server.
"""

import os
from datetime import date
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.shortcuts import redirect, render

API_URL = os.environ.get("API_URL", "http://api:5000")
TIMEOUT = 20

ESTADOS = ("Pendiente", "Pagada", "Anulada")


def llamar_api(metodo, ruta, **opciones):
    """Llama a la API y devuelve (datos, error).

    Si la API responde con codigo de error, el mensaje que devuelve se
    muestra en la interfaz para que el usuario sepa que fallo y por que.
    """
    url = f"{API_URL}{ruta}"
    try:
        respuesta = requests.request(metodo, url, timeout=TIMEOUT, **opciones)
    except requests.ConnectionError:
        return None, (
            f"No se pudo comunicar con la API en {API_URL}. "
            "Verifique que el servicio 'api' este encendido."
        )
    except requests.Timeout:
        return None, "La API no respondio a tiempo. Intente de nuevo."
    except requests.RequestException as exc:
        return None, f"Error al llamar a la API: {exc}"

    cuerpo = {}
    if respuesta.content:
        try:
            cuerpo = respuesta.json()
        except ValueError:
            cuerpo = {}

    if respuesta.status_code >= 400:
        mensaje = cuerpo.get("error")
        if not mensaje:
            mensaje = f"La API respondio con el codigo {respuesta.status_code}."
        detalle = cuerpo.get("detalle")
        if detalle:
            mensaje = f"{mensaje} ({detalle})"
        return None, mensaje

    return cuerpo, None


def numero(valor, campo, minimo=0):
    """Convierte un valor del formulario en numero, o devuelve un error."""
    try:
        resultado = Decimal(str(valor))
    except (TypeError, ValueError, InvalidOperation):
        return None, f"El campo '{campo}' debe ser un numero."
    if resultado < minimo:
        return None, f"El campo '{campo}' no puede ser menor que {minimo}."
    return resultado, None


# ------------------------------------------------------------- ordenes
def lista_ordenes(request):
    ordenes, error = llamar_api("GET", "/api/ordenes")
    return render(
        request,
        "ordenes/lista.html",
        {
            "ordenes": ordenes or [],
            "error": error,
            "total_general": sum(Decimal(str(o.get("total", 0))) for o in (ordenes or [])),
            "estados": ESTADOS,
        },
    )


def nueva_orden(request):
    error = None
    if request.method == "POST":
        datos = {
            "cliente": request.POST.get("cliente", "").strip(),
            "fecha": request.POST.get("fecha", "").strip(),
            "estado": request.POST.get("estado", "Pendiente").strip(),
        }
        if not datos["cliente"]:
            error = "El campo 'cliente' es obligatorio."
        elif datos["estado"] not in ESTADOS:
            error = "El estado seleccionado no es valido."
        else:
            orden, error = llamar_api("POST", "/api/ordenes", json=datos)
            if error is None:
                return redirect("detalle_orden", orden_id=orden["id"])

    return render(
        request,
        "ordenes/form_orden.html",
        {
            "error": error,
            "estados": ESTADOS,
            "titulo": "Nueva orden",
            "accion": request.path,
            "boton": "Crear orden",
            "valores": request.POST if request.method == "POST" else None,
            "hoy": date.today().isoformat(),
        },
    )


def editar_orden(request, orden_id):
    error = None
    orden, error = llamar_api("GET", f"/api/ordenes/{orden_id}")
    if orden is None:
        return render(
            request,
            "ordenes/lista.html",
            {"ordenes": [], "error": error, "total_general": 0, "estados": ESTADOS},
        )

    if request.method == "POST":
        datos = {
            "cliente": request.POST.get("cliente", "").strip(),
            "fecha": request.POST.get("fecha", "").strip(),
            "estado": request.POST.get("estado", "Pendiente").strip(),
        }
        if not datos["cliente"]:
            error = "El campo 'cliente' es obligatorio."
        elif datos["estado"] not in ESTADOS:
            error = "El estado seleccionado no es valido."
        else:
            actualizado, error = llamar_api("PUT", f"/api/ordenes/{orden_id}", json=datos)
            if error is None:
                return redirect("detalle_orden", orden_id=orden_id)

    return render(
        request,
        "ordenes/form_orden.html",
        {
            "error": error,
            "estados": ESTADOS,
            "titulo": f"Editar orden #{orden_id}",
            "accion": request.path,
            "boton": "Guardar cambios",
            "valores": request.POST if request.method == "POST" else orden,
        },
    )


def eliminar_orden(request, orden_id):
    orden, error = llamar_api("GET", f"/api/ordenes/{orden_id}")
    if orden is None:
        return render(
            request,
            "ordenes/lista.html",
            {"ordenes": [], "error": error, "total_general": 0, "estados": ESTADOS},
        )

    if request.method == "POST":
        _, error = llamar_api("DELETE", f"/api/ordenes/{orden_id}")
        if error is None:
            return redirect("lista_ordenes")

    return render(
        request,
        "ordenes/confirmar.html",
        {
            "error": error,
            "titulo": "Eliminar orden",
            "mensaje": f"Se eliminara la orden #{orden_id} de {orden['cliente']} "
                       "y todas sus lineas de detalle.",
            "accion": request.path,
            "cancelar": f"/ordenes/{orden_id}/",
            "boton": "Eliminar definitivamente",
        },
    )


def detalle_orden(request, orden_id):
    orden, error = llamar_api("GET", f"/api/ordenes/{orden_id}")
    if orden is None:
        return render(
            request,
            "ordenes/lista.html",
            {"ordenes": [], "error": error, "total_general": 0, "estados": ESTADOS},
        )

    return render(
        request,
        "ordenes/detalle.html",
        {
            "orden": orden,
            "detalles": orden.get("detalles", []),
            "error": error,
            "estados": ESTADOS,
        },
    )


# ------------------------------------------------------------ detalles
def nuevo_detalle(request, orden_id):
    error = None
    orden, error_orden = llamar_api("GET", f"/api/ordenes/{orden_id}")
    if orden is None:
        return render(
            request,
            "ordenes/lista.html",
            {"ordenes": [], "error": error_orden, "total_general": 0, "estados": ESTADOS},
        )

    if request.method == "POST":
        producto = request.POST.get("producto", "").strip()
        cantidad, error_cantidad = numero(request.POST.get("cantidad"), "cantidad", 1)
        precio, error_precio = numero(request.POST.get("precio_unitario"), "precio_unitario", 0)

        if not producto:
            error = "El campo 'producto' es obligatorio."
        elif error_cantidad:
            error = error_cantidad
        elif error_precio:
            error = error_precio
        else:
            _, error = llamar_api(
                "POST",
                f"/api/ordenes/{orden_id}/detalles",
                json={
                    "producto": producto,
                    "cantidad": int(cantidad),
                    "precio_unitario": float(precio),
                },
            )
            if error is None:
                return redirect("detalle_orden", orden_id=orden_id)

    return render(
        request,
        "ordenes/form_detalle.html",
        {
            "error": error,
            "orden": orden,
            "titulo": "Agregar linea de detalle",
            "accion": request.path,
            "boton": "Agregar detalle",
            "valores": request.POST if request.method == "POST" else None,
        },
    )


def editar_detalle(request, detalle_id):
    error = None
    detalle = None
    orden = None

    # El API expone PUT/DELETE sobre /api/detalles/<id>, por lo que el
    # frontend localiza la linea recorriendo las ordenes conocidas.
    ordenes, error = llamar_api("GET", "/api/ordenes")
    if ordenes is None:
        return render(
            request,
            "ordenes/lista.html",
            {"ordenes": [], "error": error, "total_general": 0, "estados": ESTADOS},
        )

    for item in ordenes:
        completa, _ = llamar_api("GET", f"/api/ordenes/{item['id']}")
        for linea in (completa or {}).get("detalles", []):
            if linea["id"] == detalle_id:
                detalle = linea
                orden = completa
                break
        if detalle:
            break

    if detalle is None:
        return render(
            request,
            "ordenes/lista.html",
            {
                "ordenes": ordenes,
                "error": "No se encontro la linea de detalle solicitada.",
                "total_general": 0,
                "estados": ESTADOS,
            },
        )

    if request.method == "POST":
        producto = request.POST.get("producto", "").strip()
        cantidad, error_cantidad = numero(request.POST.get("cantidad"), "cantidad", 1)
        precio, error_precio = numero(request.POST.get("precio_unitario"), "precio_unitario", 0)

        if not producto:
            error = "El campo 'producto' es obligatorio."
        elif error_cantidad:
            error = error_cantidad
        elif error_precio:
            error = error_precio
        else:
            _, error = llamar_api(
                "PUT",
                f"/api/detalles/{detalle_id}",
                json={
                    "producto": producto,
                    "cantidad": int(cantidad),
                    "precio_unitario": float(precio),
                },
            )
            if error is None:
                return redirect("detalle_orden", orden_id=orden["id"])

    return render(
        request,
        "ordenes/form_detalle.html",
        {
            "error": error,
            "orden": orden,
            "titulo": f"Editar detalle #{detalle_id}",
            "accion": request.path,
            "boton": "Guardar cambios",
            "valores": request.POST if request.method == "POST" else detalle,
        },
    )


def eliminar_detalle(request, detalle_id):
    orden = None
    detalle = None
    ordenes, error = llamar_api("GET", "/api/ordenes")
    if ordenes is None:
        return render(
            request,
            "ordenes/lista.html",
            {"ordenes": [], "error": error, "total_general": 0, "estados": ESTADOS},
        )

    for item in ordenes:
        completa, _ = llamar_api("GET", f"/api/ordenes/{item['id']}")
        for linea in (completa or {}).get("detalles", []):
            if linea["id"] == detalle_id:
                detalle = linea
                orden = completa
                break
        if detalle:
            break

    if detalle is None:
        return render(
            request,
            "ordenes/lista.html",
            {
                "ordenes": ordenes,
                "error": "No se encontro la linea de detalle solicitada.",
                "total_general": 0,
                "estados": ESTADOS,
            },
        )

    if request.method == "POST":
        _, error = llamar_api("DELETE", f"/api/detalles/{detalle_id}")
        if error is None:
            return redirect("detalle_orden", orden_id=orden["id"])

    return render(
        request,
        "ordenes/confirmar.html",
        {
            "error": error,
            "titulo": "Eliminar linea de detalle",
            "mensaje": f"Se eliminara la linea '{detalle['producto']}' de la "
                       f"orden #{orden['id']}. El total de la orden se recalculara.",
            "accion": request.path,
            "cancelar": f"/ordenes/{orden['id']}/",
            "boton": "Eliminar linea",
        },
    )
