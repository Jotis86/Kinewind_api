# AGENTS.md

Django 6 + DRF API para clínica de fisioterapia, con panel web server-rendered (Django Templates). Corre con `uv` (Python 3.14) y PostgreSQL 16 vía Docker.

## Comandos (siempre con `uv run`)

- Instalar deps: `uv sync`
- Levantar la BD: `docker compose up -d db` (PostgreSQL obligatorio para todo, incluidos los tests; no hay SQLite)
- Stack completo (web + db): `docker compose up -d --build` — el contenedor web ejecuta `migrate` + `seed` + `collectstatic` al arrancar
- Dev local: `uv run python manage.py runserver` (sirve el panel en `/` y la API en `/api/`)
- Migraciones: `uv run python manage.py makemigrations <app>` y `uv run python manage.py migrate`
- Seed (idempotente, crea `admin`/`admin123`): `uv run python manage.py seed`
- Tests: `uv run python manage.py test` (crean y destruyen la test DB `test_kinewind` en Postgres real; la BD debe estar arriba)
- Validar docs OpenAPI: `uv run python manage.py spectacular --validate --file /dev/null`

## Gotchas

- **`.env` NO se carga**: no hay python-dotenv. `config/settings.py` lee `os.environ.get("POSTGRES_*")` con defaults `kinewind`/`kinewind`/`localhost`. La config en contenedores llega vía el `environment:` del compose.
- **docker-compose usa interpolación estricta (`${VAR}` sin defaults)**: todas las variables de entorno del compose (DB, DEBUG, SECRET_KEY, ALLOWED_HOSTS, workers…) se leen de `.env`; si falta `.env`, `docker compose` falla. Siempre `cp .env.example .env` antes de levantar el stack. Django local (runserver) sí funciona con los defaults de settings sin `.env`.
- **El contenedor web corre como usuario no-root (`appuser`, uid 10001) sin `uv` en runtime** (multi-stage: builder con uv, runtime `python:3.14-slim`). Los comandos del contenedor usan `/app/.venv/bin/python` y `/app/.venv/bin/gunicorn` directo (healthcheck incluido). Con `docker-compose.override.yml` (dev) el código se monta por bind mount; el `.venv` NO se monta.
- **Apps en `apps/`**: labels cortos (`patients`, no `apps.patients`) para `manage.py`/filters; los `AppConfig.name` sí usan el prefijo `apps.`.
- **No hay linter/formatter** configurado (sin ruff/black). La verificación estándar es la suite de tests + validación del schema.
- Los tests asumen que un fisioterapeuta único es el admin; la API no tiene roles.
- Baja de pacientes es lógica: `DELETE /patients/{id}/` marca `active=False` (retorna 200, no 204). En el panel, `/pacientes/<id>/baja/`.
- `register` solo funciona en el primer arranque (si ya existe un usuario retorna 403). Crea un superusuario.
- `GET /api/health/` es un endpoint Django plano (sin DRF/DB) usado por el healthcheck del web.
- El panel (`apps/web`) usa sesión de Django; la API usa JWT.
- **Django prohíbe atributos que empiecen con `_` en templates.** Las anotaciones de queryset usadas en templates deben llamarse sin guion bajo (ej: `sessions_done_count`, no `_sessions_done`).
- **Bootstrap/Iconos/Fuentes vendored** en `apps/web/static/web/vendor/` (sin CDN). El form de citas usa un **selector de huecos**: día + cuadrícula de 30 min de **10:00 a 22:00** y duraciones **20/50/80 min** (`slot_times()`, `SLOT_START/END/STEP`, `DURATION_CHOICES` en `apps/appointments/services.py`) + endpoint web `GET /citas/slots/` para los ocupados. Los tests deben crear citas con `timezone.make_aware` local (Europe/Madrid).
- **El DNI se normaliza a mayúsculas** en `Patient.save()`, el form del panel y el serializer API; la unicidad es case-insensitive (`iexact`). El serializer de pacientes **no** usa el `UniqueValidator` automático de DRF (valida en `validate_dni`).
- **Estados de cita en el panel**: 4 transiciones rápidas (`programar`/`confirmar`/`cancelar`/`completar`) vía `POST /citas/<pk>/<action>/`, con validación de solapamiento al pasar a un estado activo (`AppointmentStatusView`).
- **PDF del tratamiento** se genera con `reportlab` (`apps/web/pdf.py`, función `build_treatment_pdf`) — pura Python, sin librerías de sistema. El body del PDF va comprimido: para validarlo en tests usar el prefijo `%PDF`, no el texto. `Appointment` no tiene relación con sesiones.
- **Descarga de copia de la BD** (`GET /dump/`, botón en el dashboard): llama `pg_dump` vía `subprocess` con las credenciales de `settings.DATABASES`; el nombre del archivo es `%Y-%m-%d.sql` (solo fecha, hora local). El Dockerfile instala `postgresql-client-16` desde el repo PGDG de apt (el `postgresql-client` de bookworm es v15 y **se niega** a dumpear un server 16). En local/host sin `pg_dump` devuelve 503; los tests mockean `shutil.which`/`subprocess.run`.
- **Validación de formato DNI/teléfono** en `apps/patients/validators.py` (`validate_dni_format`/`validate_phone_format`), usada por form del panel y serializer API. `Patient` tiene campos clínicos (`history`, `medications`, `sport_habits`, `fatigue_level` con choices, `gluten_intolerance`, `gut_issues`); `birth_date`/`address` existen en el modelo/API pero **no** en el form del panel. La unicidad de citas por horario la garantiza una **constraint condicional en `start`** (`unique_appointment_start`, excluye `cancelada`) + el chequeo de solapamiento `appointments_overlap`, que **excluye canceladas** (se puede re-reservar un hueco cancelado). El admin de Django valida solapamiento con su propio ModelForm.
- **Mensajes en español de España** (sin voseo rioplatense: "Elige", no "Elegí"). El serializer de citas **quita el UniqueValidator automático** que DRF agrega por la constraint de `start` (su mensaje "Ya existe appointment con este fecha y hora." es confuso); la unicidad la maneja `appointments_overlap` vía `OVERLAP_ERROR`. Los forms del panel anulan `validate_unique` para que no filtre el mensaje crudo de la BD (el DNI lo valida `clean_dni`).
- Validaciones compartidas entre API y panel viven en `apps/appointments/services.py` (`appointments_overlap`).
- `STORAGES["staticfiles"]` usa manifest (whitenoise) solo con `DEBUG=False`; con DEBUG el runserver sirve estáticos directo.
