#!/usr/bin/env bash
# =====================================================================
#  Inicializacion de la base de datos de ordenes (Grupo 5).
#
#  Espera a que SQL Server acepte conexiones y luego aplica db/init.sql.
#  Lo ejecuta el servicio "db-init" definido en compose.yaml.
# =====================================================================

set -uo pipefail

SQLCMD="/opt/mssql-tools18/bin/sqlcmd"
SERVER="db"
USER="sa"
PASSWORD="${SA_PASSWORD:-}"
INTENTOS=40

echo "[db-init] Esperando a que SQL Server acepte conexiones..."
conectado=0
for i in $(seq 1 "$INTENTOS"); do
    if "$SQLCMD" -S "$SERVER" -U "$USER" -P "$PASSWORD" -C -Q "SELECT 1" > /dev/null 2>&1; then
        echo "[db-init] SQL Server responde. Aplicando init.sql..."
        conectado=1
        break
    fi
    echo "[db-init]   intento $i de $INTENTOS: todavia no responde"
    sleep 2
done

if [ "$conectado" -ne 1 ]; then
    echo "[db-init] ERROR: SQL Server no respondio en $INTENTOS intentos."
    exit 1
fi

if ! "$SQLCMD" -S "$SERVER" -U "$USER" -P "$PASSWORD" -C -i /init/init.sql; then
    echo "[db-init] ERROR: no se pudo aplicar init.sql."
    exit 1
fi

# Verificacion: si las tablas no quedaron creadas, el servicio debe fallar.
if ! "$SQLCMD" -S "$SERVER" -U "$USER" -P "$PASSWORD" -C -d OrdenesDB \
     -Q "IF OBJECT_ID('dbo.ordenes','U') IS NULL OR OBJECT_ID('dbo.orden_detalle','U') IS NULL RAISERROR('faltan tablas',16,1);" > /dev/null; then
    echo "[db-init] ERROR: las tablas ordenes / orden_detalle no existen."
    exit 1
fi

echo "[db-init] Listo. Base de datos OrdenesDB inicializada."
exit 0
