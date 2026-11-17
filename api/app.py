"""API REST de ordenes de venta - Grupo 5 (Arquitectura de Computadoras).

Este es el unico servicio que se conecta a SQL Server. La conexion usa el
nombre del servicio "db", que Docker resuelve mediante su DNS interno dentro
de la red bridge del proyecto. Los datos de conexion llegan por variables de
entorno, nunca estan escritos en el codigo.
"""

import os
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pymssql
from flask import Flask, jsonify, request

app = Flask(__name__)

# ------------------------------------------------------- configuracion
DB_SERVER = os.getenv("DB_SERVER", "db")
DB_PORT = os.getenv("DB_PORT", "1433")
DB_USER = os.getenv("DB_USER", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "OrdenesDB")

ESTADOS = ("Pendiente", "Pagada", "Anulada")


# ------------------------------------------------------------- conexion
@contextmanager
def conexion():
    """Abre una conexion a SQL Server y la cierra siempre."""
    conn = pymssql.connect(
        server=DB_SERVER,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        tds_version="7.4",
        login_timeout=30,
        timeout=30,
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def consultar(conn, sql, params=()):
    """Ejecuta una consulta y devuelve una lista de diccionarios."""
    cur = conn.cursor()
    cur.execute(sql, params)
    columnas = [c[0] for c in cur.description]
    return [dict(zip(columnas, fila)) for fila in cur.fetchall()]


def a_json(valor):
    """Convierte tipos de SQL Server a tipos que JSON puede representar."""
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, dict):
        return {k: a_json(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [a_json(v) for v in valor]
    return valor


def recalcular_total(conn, orden_id):
    """Vuelve a calcular el total de la orden a partir de sus detalles."""
    cur = conn.cursor()
    cur.execute(
        "UPDATE dbo.ordenes SET total = "
        "(SELECT ISNULL(SUM(subtotal), 0) FROM dbo.orden_detalle WHERE orden_id = %s) "
        "WHERE id = %s",
        (orden_id, orden_id),
    )


def obtener_orden(conn, orden_id):
    """Devuelve la orden o None si no existe."""
    filas = consultar(
        conn,
        "SELECT id, cliente, fecha, estado, total FROM dbo.ordenes WHERE id = %s",
        (orden_id,),
    )
    return filas[0] if filas else None


def obtener_detalles(conn, orden_id):
    return consultar(
        conn,
        "SELECT id, orden_id, producto, cantidad, precio_unitario, subtotal "
        "FROM dbo.orden_detalle WHERE orden_id = %s ORDER BY id",
        (orden_id,),
    )


def leer_linea(datos):
    """Valida los campos de una linea de detalle. Devuelve (linea, error)."""
    producto = str(datos.get("producto") or "").strip()
    if not producto:
        return None, "El campo 'producto' es obligatorio"

    try:
        cantidad = int(datos.get("cantidad"))
    except (TypeError, ValueError):
        return None, "El campo 'cantidad' debe ser un numero entero"
    if cantidad <= 0:
        return None, "La cantidad debe ser mayor que cero"

    try:
        precio = Decimal(str(datos.get("precio_unitario")))
    except (TypeError, ValueError, InvalidOperation):
        return None, "El campo 'precio_unitario' debe ser un numero"
    if precio < 0:
        return None, "El precio unitario no puede ser negativo"

    return (producto, cantidad, precio), None


def leer_fecha(valor):
    if valor in (None, ""):
        return date.today(), None
    try:
        return date.fromisoformat(str(valor)[:10]), None
    except ValueError:
        return None, "La fecha debe tener el formato AAAA-MM-DD"


# --------------------------------------------------------------- health
@app.get("/health")
def health():
    """Estado de la API. Lo usa el healthcheck de Docker Compose."""
    try:
        with conexion() as conn:
            ordenes = consultar(conn, "SELECT COUNT(*) AS n FROM dbo.ordenes")[0]["n"]
            detalles = consultar(conn, "SELECT COUNT(*) AS n FROM dbo.orden_detalle")[0]["n"]
        return jsonify({
            "status": "ok",
            "base": DB_NAME,
            "servidor": DB_SERVER,
            "ordenes": ordenes,
            "detalles": detalles,
        }), 200
    except Exception as exc:
        return jsonify({"status": "error", "detalle": str(exc)}), 503


# ------------------------------------------------------------- ordenes
@app.get("/api/ordenes")
def listar_ordenes():
    with conexion() as conn:
        ordenes = consultar(
            conn,
            "SELECT id, cliente, fecha, estado, total FROM dbo.ordenes ORDER BY id ASC",
        )
    return jsonify(a_json(ordenes)), 200


@app.get("/api/ordenes/<int:orden_id>")
def ver_orden(orden_id):
    with conexion() as conn:
        orden = obtener_orden(conn, orden_id)
        if orden is None:
            return jsonify({"error": "La orden no existe"}), 404
        orden["detalles"] = obtener_detalles(conn, orden_id)
    return jsonify(a_json(orden)), 200


@app.post("/api/ordenes")
def crear_orden():
    datos = request.get_json(silent=True) or {}

    cliente = str(datos.get("cliente") or "").strip()
    if not cliente:
        return jsonify({"error": "El campo 'cliente' es obligatorio"}), 400

    estado = str(datos.get("estado") or "Pendiente").strip()
    if estado not in ESTADOS:
        return jsonify({
            "error": "Estado invalido",
            "permitidos": list(ESTADOS),
        }), 400

    fecha, error = leer_fecha(datos.get("fecha"))
    if error:
        return jsonify({"error": error}), 400

    lineas = []
    for item in datos.get("detalles") or []:
        linea, error = leer_linea(item)
        if error:
            return jsonify({"error": error}), 400
        lineas.append(linea)

    with conexion() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO dbo.ordenes (cliente, fecha, estado, total) VALUES (%s, %s, %s, 0)",
            (cliente, fecha, estado),
        )
        orden_id = cur.lastrowid
        for producto, cantidad, precio in lineas:
            cur.execute(
                "INSERT INTO dbo.orden_detalle (orden_id, producto, cantidad, "
                "precio_unitario, subtotal) VALUES (%s, %s, %s, %s, %s)",
                (orden_id, producto, cantidad, precio, cantidad * precio),
            )
        recalcular_total(conn, orden_id)
        orden = obtener_orden(conn, orden_id)
        orden["detalles"] = obtener_detalles(conn, orden_id)

    return jsonify(a_json(orden)), 201


@app.put("/api/ordenes/<int:orden_id>")
def actualizar_orden(orden_id):
    datos = request.get_json(silent=True) or {}

    with conexion() as conn:
        orden = obtener_orden(conn, orden_id)
        if orden is None:
            return jsonify({"error": "La orden no existe"}), 404

        cliente = str(datos.get("cliente") or orden["cliente"]).strip()
        if not cliente:
            return jsonify({"error": "El campo 'cliente' es obligatorio"}), 400

        estado = str(datos.get("estado") or orden["estado"]).strip()
        if estado not in ESTADOS:
            return jsonify({
                "error": "Estado invalido",
                "permitidos": list(ESTADOS),
            }), 400

        fecha, error = leer_fecha(datos.get("fecha") or orden["fecha"])
        if error:
            return jsonify({"error": error}), 400

        cur = conn.cursor()
        cur.execute(
            "UPDATE dbo.ordenes SET cliente = %s, fecha = %s, estado = %s WHERE id = %s",
            (cliente, fecha, estado, orden_id),
        )
        recalcular_total(conn, orden_id)
        orden = obtener_orden(conn, orden_id)
        orden["detalles"] = obtener_detalles(conn, orden_id)

    return jsonify(a_json(orden)), 200


@app.delete("/api/ordenes/<int:orden_id>")
def eliminar_orden(orden_id):
    with conexion() as conn:
        if obtener_orden(conn, orden_id) is None:
            return jsonify({"error": "La orden no existe"}), 404
        cur = conn.cursor()
        # Los detalles se borran en cascada por la llave foranea.
        cur.execute("DELETE FROM dbo.ordenes WHERE id = %s", (orden_id,))
    return jsonify({"mensaje": "Orden eliminada", "id": orden_id}), 200


# ------------------------------------------------------------ detalles
@app.get("/api/ordenes/<int:orden_id>/detalles")
def listar_detalles(orden_id):
    with conexion() as conn:
        if obtener_orden(conn, orden_id) is None:
            return jsonify({"error": "La orden no existe"}), 404
        detalles = obtener_detalles(conn, orden_id)
    return jsonify(a_json(detalles)), 200


@app.post("/api/ordenes/<int:orden_id>/detalles")
def crear_detalle(orden_id):
    datos = request.get_json(silent=True) or {}

    linea, error = leer_linea(datos)
    if error:
        return jsonify({"error": error}), 400

    producto, cantidad, precio = linea

    with conexion() as conn:
        if obtener_orden(conn, orden_id) is None:
            return jsonify({"error": "La orden no existe"}), 404

        cur = conn.cursor()
        cur.execute(
            "INSERT INTO dbo.orden_detalle (orden_id, producto, cantidad, "
            "precio_unitario, subtotal) VALUES (%s, %s, %s, %s, %s)",
            (orden_id, producto, cantidad, precio, cantidad * precio),
        )
        detalle_id = cur.lastrowid
        recalcular_total(conn, orden_id)

        detalle = consultar(
            conn,
            "SELECT id, orden_id, producto, cantidad, precio_unitario, subtotal "
            "FROM dbo.orden_detalle WHERE id = %s",
            (detalle_id,),
        )[0]
        total = consultar(
            conn, "SELECT total FROM dbo.ordenes WHERE id = %s", (orden_id,)
        )[0]["total"]

    respuesta = a_json(detalle)
    respuesta["total_orden"] = a_json(total)
    return jsonify(respuesta), 201


@app.put("/api/detalles/<int:detalle_id>")
def actualizar_detalle(detalle_id):
    datos = request.get_json(silent=True) or {}

    linea, error = leer_linea(datos)
    if error:
        return jsonify({"error": error}), 400

    producto, cantidad, precio = linea

    with conexion() as conn:
        filas = consultar(
            conn,
            "SELECT id, orden_id FROM dbo.orden_detalle WHERE id = %s",
            (detalle_id,),
        )
        if not filas:
            return jsonify({"error": "El detalle no existe"}), 404
        orden_id = filas[0]["orden_id"]

        cur = conn.cursor()
        cur.execute(
            "UPDATE dbo.orden_detalle SET producto = %s, cantidad = %s, "
            "precio_unitario = %s, subtotal = %s WHERE id = %s",
            (producto, cantidad, precio, cantidad * precio, detalle_id),
        )
        recalcular_total(conn, orden_id)

        detalle = consultar(
            conn,
            "SELECT id, orden_id, producto, cantidad, precio_unitario, subtotal "
            "FROM dbo.orden_detalle WHERE id = %s",
            (detalle_id,),
        )[0]
        total = consultar(
            conn, "SELECT total FROM dbo.ordenes WHERE id = %s", (orden_id,)
        )[0]["total"]

    respuesta = a_json(detalle)
    respuesta["total_orden"] = a_json(total)
    return jsonify(respuesta), 200


@app.delete("/api/detalles/<int:detalle_id>")
def eliminar_detalle(detalle_id):
    with conexion() as conn:
        filas = consultar(
            conn,
            "SELECT id, orden_id FROM dbo.orden_detalle WHERE id = %s",
            (detalle_id,),
        )
        if not filas:
            return jsonify({"error": "El detalle no existe"}), 404
        orden_id = filas[0]["orden_id"]

        cur = conn.cursor()
        cur.execute("DELETE FROM dbo.orden_detalle WHERE id = %s", (detalle_id,))
        recalcular_total(conn, orden_id)

        total = consultar(
            conn, "SELECT total FROM dbo.ordenes WHERE id = %s", (orden_id,)
        )[0]["total"]

    return jsonify({
        "mensaje": "Detalle eliminado",
        "id": detalle_id,
        "total_orden": a_json(total),
    }), 200


# --------------------------------------------------------------- extras
@app.errorhandler(404)
def ruta_no_encontrada(_):
    return jsonify({"error": "El recurso solicitado no existe"}), 404


@app.errorhandler(500)
def error_interno(exc):
    return jsonify({"error": "Error interno del servidor", "detalle": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
