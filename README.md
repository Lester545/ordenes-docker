# Ordenes de venta en tres contenedores — Docker Compose

**Arquitectura de Computadoras · Examen práctico del II parcial**  
**Grupo 5 — Tarjetas de venta (API REST + frontend Django + SQL Server)**

Aplicación web distribuida en tres contenedores: una base de datos **SQL Server 2022**,
una **API REST en Flask** y un **frontend en Django** con todas las operaciones CRUD.
Los tres servicios se levantan con un solo comando de Docker Compose.

---

## 1. Integrantes del grupo

| # | Nombre completo                       | Número de cuenta |
|---|---------------------------------------|------------------|
| 1 | DOLORES GABRIELA HERNANDEZ ARGUETA    |   201510011174   |
| 2 | JOEL ALEXANDER BANEGAS                |   202510010424   |
| 3 | JOSEPH AHUDIZALAN GALDAMEZ ALVAREZ    |   202020010040   |
| 4 | JUNIOR ALEXANDER ORTIZ                |   201730010212   |
| 5 | JUNIOR GEOVANY ROSALES PEREZ          |   202320010336   |
| 6 | LESTER GERARDO AGUIRRE MACHADO        |   202510010721   |
| 7 | VICTOR BERNARDO DUBON                 |   201210011528   |
| 8 | VICTOR MANUEL ESTRADA DEL CID         |   202120010333   |

---

## 2. Arquitectura

```
                            Navegador
                                |
                     http://localhost:8085
                                |
                +---------------+----------------+
                |        web  (Django)           |  imagen propia
                |   gunicorn 2 workers :8000     |  usuario "web" (uid 10002)
                |   solo publica el puerto       |  limite: 0.50 CPU / 384 MB
                +---------------+----------------+
                                |
                                |  HTTP por nombre de servicio
                                |  API_URL = http://api:5000
                                v
                +---------------+----------------+
                |        api  (Flask)            |  imagen propia
                |   gunicorn 2 workers :5000     |  usuario "api" (uid 10001)
                |   NO publica puerto            |  limite: 0.75 CPU / 512 MB
                +---------------+----------------+
                                |
                                |  TDS 1433 por nombre de servicio
                                |  DB_SERVER = db
                                v
                +---------------+----------------+
                |     db  (SQL Server 2022)      |  imagen oficial de Microsoft
                |        :1433                   |  limite: 1.50 CPU / 2 GB
                +---------------+----------------+
                                |
                    volumen con nombre
                     "db-datos"  ->  /var/opt/mssql

            todos en la red bridge propia  "red-ordenes"
```

**Datos y servicios:**

- `db` guarda la base `OrdenesDB` con las tablas `ordenes` (llave primaria `id`) y
  `orden_detalle` (llave foránea `orden_id` → `ordenes.id`, con borrado en cascada).
- `api` es el **único** servicio que se conecta a SQL Server.
- `web` consume la API por el nombre del servicio y nunca abre una conexión a la base.
- `db-init` es un servicio auxiliar de un solo uso que aplica `db/init.sql` y termina.

---

## 3. Estructura del repositorio

```
EXAMEN_GRUPO5/
├─ compose.yaml            # los tres servicios, red, volumen, límites y healthchecks
├─ .env.example            # plantilla de variables de entorno (sin contraseñas reales)
├─ .env                    # variables locales (NO se sube al repositorio)
├─ .gitignore
├─ README.md
├─ db/
│  ├─ init.sql             # crea OrdenesDB, ordenes, orden_detalle y carga datos de prueba
│  └─ init.sh              # espera a SQL Server y aplica init.sql
├─ api/
│  ├─ app.py               # API REST Flask: CRUD de ordenes y detalles + /health
│  ├─ requirements.txt     # Flask, gunicorn, pymssql
│  ├─ Dockerfile           # imagen propia (usuario sin privilegios, gunicorn, HEALTHCHECK)
│  └─ .dockerignore
├─ web/
│  ├─ manage.py
│  ├─ requirements.txt     # Django, requests, gunicorn
│  ├─ Dockerfile
│  ├─ .dockerignore
│  ├─ config/              # settings.py, urls.py, wsgi.py
│  └─ ordenes/             # vistas, urls y plantillas HTML
└─ evidencias/             # capturas de pantalla
```

---

## 4. Requisitos

- Docker Desktop con WSL 2 (Windows o macOS) o Docker Engine (Linux).
- Al menos **4 GB de RAM** libres: SQL Server reserva 2 GB y la imagen ocupa más de 2 GB en disco.
- PowerShell (Windows), bash (Linux/macOS) o Docker Desktop.

---

## 5. Cómo ejecutarlo desde cero

### 5.1 Preparar el archivo de entorno

```powershell
copy .env.example .env          # Windows PowerShell
cp .env.example .env            # Linux / macOS
```

Edite `.env` y ponga sus valores reales:

```ini
MSSQL_SA_PASSWORD=SuClave_Fuerte_2026!     # 8+ caracteres, mayusculas, minusculas, numeros y simbolos
DOCKERHUB_USER=su_usuario_de_docker_hub   # solo para publicar las imagenes
DJANGO_SECRET_KEY=una_clave_aleatoria_larga
```

### 5.2 Levantar todo

```powershell
docker compose up -d --build
```

Espere a que los tres servicios queden **healthy**:

```powershell
docker compose ps
```

| Servicio | Estado esperado | Puerto |
|----------|------------------|--------|
| `db` | Up (healthy) | 1433/tcp (no publicado) |
| `api` | Up (healthy) | 5000/tcp (no publicado) |
| `web` | Up (healthy) | 0.0.0.0:8085→8000/tcp |

### 5.3 Abrir la aplicación

Navegador: **http://localhost:8085**

### 5.4 Detener el proyecto

```powershell
docker compose down          # detiene los contenedores, conserva los datos
docker compose down -v       # detiene y borra tambien el volumen (se pierden los datos)
```

---

## 6. Endpoints de la API

La API **no publica puerto** en el equipo: se consulta desde dentro de la red del proyecto.

| Método | Ruta | Respuesta |
|--------|------|-----------|
| GET | `/health` | 200 — estado de la API (lo usa el healthcheck) |
| GET | `/api/ordenes` | 200 — lista de órdenes |
| GET | `/api/ordenes/<id>` | 200 — una orden con sus detalles / **404** si no existe |
| POST | `/api/ordenes` | **201** — crea una orden / **400** si faltan campos |
| PUT | `/api/ordenes/<id>` | 200 — actualiza / **404** si no existe |
| DELETE | `/api/ordenes/<id>` | 200 — elimina la orden y sus detalles / **404** |
| GET | `/api/ordenes/<id>/detalles` | 200 — líneas de detalle de la orden |
| POST | `/api/ordenes/<id>/detalles` | **201** — agrega una línea / **400** si es inválida |
| PUT | `/api/detalles/<id>` | 200 — actualiza una línea / **404** |
| DELETE | `/api/detalles/<id>` | 200 — elimina una línea / **404** |

El campo `total` de la orden **se recalcula** cada vez que se agrega, modifica o elimina
una línea de detalle.

### Cómo probarla

La API no publica puerto en el equipo: se consulta desde dentro de la red del proyecto.

```powershell
docker compose exec -T web curl -s http://api:5000/api/ordenes
docker compose exec -T web curl -s -X POST http://api:5000/api/ordenes -H "Content-Type: application/json" -d '{"cliente":"Distribuidora Andina","fecha":"2026-11-16","estado":"Pendiente"}'
docker compose exec -T web curl -s http://api:5000/health
```

---

## 7. La base de datos y `init.sql`

El archivo `db/init.sql` crea la base `OrdenesDB`, las dos tablas con sus llaves y
5 órdenes de prueba con 12 líneas de detalle. Es **idempotente**: se puede volver a
aplicar sin duplicar datos.

Se aplica automáticamente al levantar el stack, mediante el servicio `db-init`.
Para aplicarlo a mano:

```powershell
docker compose exec -T db /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "<CLAVE>" -C -i /init/init.sql
```

Estructura resultante:

```
ordenes
  id      INT IDENTITY  PRIMARY KEY
  cliente NVARCHAR(120)
  fecha   DATE
  estado  NVARCHAR(20)   -- Pendiente | Pagada | Anulada
  total   DECIMAL(12,2)

orden_detalle
  id              INT IDENTITY  PRIMARY KEY
  orden_id        INT           FOREIGN KEY -> ordenes(id)  ON DELETE CASCADE
  producto        NVARCHAR(120)
  cantidad        INT
  precio_unitario DECIMAL(12,2)
  subtotal        DECIMAL(12,2)
```

---

## 8. Publicación en Docker Hub

Las imagenes publicadas para este proyecto estan en:

- `lester545/g5-ordenes-api:v1.0`
- `lester545/g5-ordenes-web:v1.0`

Publicacion:

```powershell
docker login
docker compose build
docker push lester545/g5-ordenes-api:v1.0
docker push lester545/g5-ordenes-web:v1.0
```

Ejecucion de la imagen de la API en otro equipo:

```powershell
docker pull lester545/g5-ordenes-api:v1.0
docker run -d --name api-prueba -p 5000:5000 -e DB_SERVER=db -e DB_PASSWORD=<CLAVE> lester545/g5-ordenes-api:v1.0
```

---

## 9. Evidencias

Las capturas de pantalla van en la carpeta `evidencias/`: estado de los servicios,
CRUD en el navegador, respuestas de la API, persistencia de los datos y consumo de
recursos. Todas deben mostrar la ventana completa con la fecha y hora del equipo.

Comandos útiles para las evidencias:

```powershell
docker compose ps                      # los tres servicios sanos
docker compose stats --no-stream       # limites de CPU y memoria
docker compose exec api id             # usuario sin privilegios
docker compose exec web id
docker inspect ordenes-docker-api-1 --format "Memory={{.HostConfig.Memory}} NanoCpus={{.HostConfig.NanoCpus}}"
docker volume ls                       # volumen con nombre
docker network ls                      # red bridge propia
docker compose down && docker compose up -d   # persistencia de los datos
```

---

## 10. Buenas prácticas aplicadas

- **Un solo archivo** `compose.yaml` describe toda la aplicación.
- **Orden de arranque garantizado** con `depends_on` + `condition: service_healthy`:
  la API espera a que la base esté sana y a que `init.sql` haya terminado; el frontend
  espera a que la API esté sana.
- **Usuario sin privilegios** en las imágenes `api` y `web` (`USER api` / `USER web`).
- **Límites de recursos** (`deploy.resources.limits`) en los tres servicios.
- **Volumen con nombre** para que los datos sobrevivan a `docker compose down`.
- **Red bridge propia** para que los servicios se ubiquen por nombre.
- **Contraseñas fuera de las imágenes** y del `compose.yaml`, en el archivo `.env`.
- **`.dockerignore`** en `api` y `web` para no enviar archivos innecesarios al build.
- **Dockerfiles ordenados** para aprovechar la caché: primero `requirements.txt`.
- **`restart: unless-stopped`** para que los servicios se recuperen solos.
