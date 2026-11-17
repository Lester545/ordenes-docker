-- =====================================================================
--  Base de datos de ordenes de venta  -  Grupo 5
--  Arquitectura de Computadoras / Examen practico del II parcial
--
--  Crea la base OrdenesDB con las tablas ordenes y orden_detalle
--  (llave primaria y llave foranea), y carga datos de prueba.
--
--  El script es idempotente: se puede ejecutar mas de una vez sin
--  duplicar datos ni fallar.
--
--  Como se ejecuta (tambien documentado en el README):
--    docker compose exec -T db /opt/mssql-tools18/bin/sqlcmd \
--        -S localhost -U sa -P "<CLAVE>" -C -i /init/init.sql
--
--  O automaticamente al levantar el stack, mediante el servicio
--  "db-init" definido en compose.yaml.
-- =====================================================================

SET NOCOUNT ON;
GO

-- ---------------------------------------------------------------- base
IF DB_ID('OrdenesDB') IS NULL
BEGIN
    CREATE DATABASE OrdenesDB;
END
GO

USE OrdenesDB;
GO

-- ------------------------------------------------------------ ordenes
IF OBJECT_ID('dbo.ordenes', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.ordenes (
        id      INT IDENTITY(1,1) NOT NULL,
        cliente NVARCHAR(120)     NOT NULL,
        fecha   DATE              NOT NULL DEFAULT (CAST(GETDATE() AS DATE)),
        estado  NVARCHAR(20)      NOT NULL DEFAULT ('Pendiente'),
        total   DECIMAL(12,2)     NOT NULL DEFAULT (0),
        CONSTRAINT PK_ordenes PRIMARY KEY (id),
        CONSTRAINT CK_ordenes_estado CHECK (estado IN ('Pendiente','Pagada','Anulada'))
    );
END
GO

-- ------------------------------------------------------- orden_detalle
IF OBJECT_ID('dbo.orden_detalle', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.orden_detalle (
        id              INT IDENTITY(1,1) NOT NULL,
        orden_id        INT           NOT NULL,
        producto        NVARCHAR(120) NOT NULL,
        cantidad        INT           NOT NULL,
        precio_unitario DECIMAL(12,2) NOT NULL,
        subtotal        DECIMAL(12,2) NOT NULL,
        CONSTRAINT PK_orden_detalle PRIMARY KEY (id),
        CONSTRAINT FK_orden_detalle_ordenes FOREIGN KEY (orden_id)
            REFERENCES dbo.ordenes (id) ON DELETE CASCADE,
        CONSTRAINT CK_orden_detalle_cantidad CHECK (cantidad > 0),
        CONSTRAINT CK_orden_detalle_precio  CHECK (precio_unitario >= 0)
    );
END
GO

-- --------------------------------------------------------- datos prueba
IF NOT EXISTS (SELECT 1 FROM dbo.ordenes)
BEGIN
    INSERT INTO dbo.ordenes (cliente, fecha, estado, total) VALUES
        (N'Distribuidora del Norte',   '2026-10-02', 'Pagada',    0),
        (N'Ferreteria El Tornillo',     '2026-10-09', 'Pendiente', 0),
        (N'Farmacia Vida',              '2026-10-15', 'Pagada',    0),
        (N'Panificadora La Espiga',     '2026-10-21', 'Pendiente', 0),
        (N'TecnoSistemas del Sur',      '2026-10-28', 'Anulada',   0);
END
GO

IF NOT EXISTS (SELECT 1 FROM dbo.orden_detalle)
BEGIN
    INSERT INTO dbo.orden_detalle (orden_id, producto, cantidad, precio_unitario, subtotal) VALUES
        (1, N'Teclado mecanico',    4,  85.00,  340.00),
        (1, N'Monitor 24 pulgadas', 2, 210.50,  421.00),
        (1, N'Cable HDMI',         10,  12.75,  127.50),
        (2, N'Cemento 50kg',        20,   9.90,  198.00),
        (2, N'Arena 1m3',            3,  32.00,   96.00),
        (3, N'Vitamina C 1000',      6,  45.80,  274.80),
        (3, N'Algodon',             12,   8.25,   99.00),
        (4, N'Harina 1kg',          30,   3.40,  102.00),
        (4, N'Azucar 1kg',          25,   4.10,  102.50),
        (4, N'Levadura 500g',       10,  11.30,  113.00),
        (5, N'Laptop 15"',           1, 749.00,  749.00),
        (5, N'SSD 1TB',              2,  89.90,  179.80);
END
GO

-- -------------------------------------------- recalcular los totales
UPDATE o
SET o.total = d.suma
FROM dbo.ordenes o
JOIN (
    SELECT orden_id, SUM(subtotal) AS suma
    FROM dbo.orden_detalle
    GROUP BY orden_id
) d ON d.orden_id = o.id
WHERE o.total <> d.suma;
GO

SELECT 'Listo' AS estado,
       (SELECT COUNT(*) FROM dbo.ordenes)      AS ordenes,
       (SELECT COUNT(*) FROM dbo.orden_detalle) AS detalles,
       (SELECT SUM(total) FROM dbo.ordenes)     AS total_facturado;
GO
