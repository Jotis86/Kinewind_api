# Kinewind

Plataforma para una clínica de fisioterapia: **panel web** (Django Templates) + **API REST** (DRF) para pacientes, citas (agenda) y tratamientos con plan de sesiones.

## Stack

- Python 3.14 / [uv](https://docs.astral.sh/uv/)
- Django 6 + Django REST Framework
- PostgreSQL 16 (Docker Compose)
- Panel web server-rendered con Django Templates + Bootstrap 5 (vendored en `static/`)
- Autenticación: sesión (panel web) y JWT (`djangorestframework-simplejwt`) para la API
- Docs OpenAPI (`drf-spectacular`)

## Puesta en marcha

1. Instalar dependencias:
   ```bash
   uv sync
   ```

2. Levantar PostgreSQL:
   ```bash
   docker compose up -d
   ```

3. Configurar entorno (**obligatorio para `docker compose`**, opcional para runserver local):
   ```bash
   cp .env.example .env
   ```

4. Migrar y cargar datos de ejemplo:
   ```bash
   uv run python manage.py migrate
   uv run python manage.py seed
   ```
   El seed crea únicamente el usuario `admin` / `admin123` (el fisioterapeuta), sin datos de ejemplo.

5. Correr el servidor:
   ```bash
   uv run python manage.py runserver
   ```

## Panel web

Entra en `http://127.0.0.1:8000/` con `admin` / `admin123`.

- **Dashboard** (`/`): KPIs de pacientes, tratamientos, citas de hoy y total de citas confirmadas, más agenda de hoy, próximas citas y accesos rápidos.
- **Pacientes** (`/pacientes/`): listado con búsqueda y filtro, alta con ficha clínica completa (trabajo, antecedentes, medicación, hábitos deportivos, nivel de cansancio, intolerancias, observaciones), edición, tratamientos y citas, **baja lógica** y **reactivación**.
- **Tratamientos** (`/tratamientos/`): planes con barra de progreso, alta/edición/eliminación, **plan de sesiones** (agregar, marcar realizada, editar, eliminar) y **exportar PDF** del tratamiento para enviarlo por otros medios.
- **Citas** (`/citas/`): listado con filtros, alta con **selector de huecos** (día + horarios de 10:00 a 22:00 cada 30 min, duración 20/50/80 min), edición/eliminación y acciones rápidas de **confirmar / completar / cancelar / reprogramar** con validación de solapamiento.
- **Agenda del día** (`/agenda/?date=`): citas del día ordenadas por hora.

El panel reutiliza las mismas validaciones que la API (solapamiento de citas, nº de sesión único). Bootstrap, iconos y fuentes están guardados localmente en `apps/web/static/web/vendor/` (sin CDN).

### Docker (stack completo)

```bash
docker compose up -d --build
```

El contenedor `web` espera la BD, aplica migraciones, ejecuta el seed y sirve con gunicorn en el puerto 8000. La configuración (BD, `DEBUG`, `SECRET_KEY`, workers) se interpola desde `.env`.

Para desarrollo con recarga en vivo, el `docker-compose.override.yml` monta el código fuente y usa `runserver` (se aplica automáticamente con `docker compose up -d`).

## Endpoints

Base: `http://127.0.0.1:8000/api`

| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/api/health/` | Healthcheck (sin DB) |

### Autenticación
| Método | URL | Descripción |
|--------|-----|-------------|
| POST | `/api/auth/register/` | Crea el admin (solo primer arranque) |
| POST | `/api/auth/login/` | Obtiene tokens `access` y `refresh` |
| POST | `/api/auth/refresh/` | Renueva el token con `refresh` |
| GET | `/api/auth/me/` | Datos del usuario autenticado |

### Pacientes
| Método | URL | Descripción |
|--------|-----|-------------|
| GET/POST | `/api/patients/` | Listar (filtro `?active=`, búsqueda `?search=`) / crear |
| GET/PUT/PATCH | `/api/patients/{id}/` | Ver / modificar |
| DELETE | `/api/patients/{id}/` | Baja lógica (marca `active=False`) |
| GET | `/api/patients/{id}/treatments/` | Tratamientos del paciente |
| GET | `/api/patients/{id}/appointments/` | Citas del paciente |

### Tratamientos
| Método | URL | Descripción |
|--------|-----|-------------|
| GET/POST | `/api/treatments/` | Listar / crear (filtros `?patient=`, `?status=`) |
| GET/PUT/PATCH/DELETE | `/api/treatments/{id}/` | Ver / modificar / eliminar |
| GET | `/api/treatments/{id}/sessions/` | Sesiones del tratamiento (filtro `?status=`) |
| POST | `/api/treatments/{id}/sessions/` | Crear sesión del tratamiento |

### Sesiones
| Método | URL | Descripción |
|--------|-----|-------------|
| GET/POST | `/api/sessions/` | Listar / crear (filtros `?treatment=`, `?status=`, `?date=`) |
| GET/PUT/PATCH/DELETE | `/api/sessions/{id}/` | Ver / modificar / eliminar |

### Citas (agenda)
| Método | URL | Descripción |
|--------|-----|-------------|
| GET/POST | `/api/appointments/` | Listar / crear (filtros `?patient=`, `?status=`) |
| GET/PUT/PATCH/DELETE | `/api/appointments/{id}/` | Ver / modificar / eliminar |
| GET | `/api/appointments/agenda/?date=YYYY-MM-DD` | Agenda del día ordenada por hora (por defecto hoy) |

La creación de citas valida solapamientos: no permite dos citas en el mismo horario.

### Documentación
- Swagger UI: `http://127.0.0.1:8000/api/docs/`
- OpenAPI schema: `http://127.0.0.1:8000/api/schema/`
- Redoc: `http://127.0.0.1:8000/api/docs/redoc/`

## Modelo de datos

- **User**: usuario Django (auth JWT). Un único fisioterapeuta/admin.
- **Patient**: datos personales (nombre, apellidos, DNI, trabajo, teléfono, email), motivo de consulta, antecedentes, medicación, hábitos deportivos, nivel de cansancio, intolerancias/digestión, observaciones y `active` para bajas lógicas.
- **Treatment** → Patient: diagnóstico, cantidad de sesiones, frecuencia, estado (activo/finalizado/cancelado). Expone `sessions_done`.
- **Session** → Treatment: número de sesión (único por tratamiento), fecha, estado, notas clínicas y evolución.
- **Appointment** → Patient: fecha/hora, duración, estado (programada/confirmada/cancelada/completada).

## Tests

```bash
uv run python manage.py test
```

## Notas

- El endpoint `POST /api/auth/register/` solo funciona en el primer arranque (sin usuarios registrados). Luego de crear el admin queda deshabilitado (403).
- La API exige autenticación JWT en todos los endpoints salvo `register`, `login` y `health`.
- El panel web usa sesión de Django; la API sigue con JWT (conviven sin conflicto).
- Los estáticos se sirven con whitenoise; el contenedor web ejecuta `collectstatic` al arrancar.
- La config llega por variables de entorno. El contenedor web interpola `.env` (compose), pero Django local **no** lee `.env` automáticamente: los defaults de `config/settings.py` coinciden con docker-compose.
