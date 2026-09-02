# InverTec

Simulador de inversión (Tecmilenio) para practicar compras y ventas de acciones con saldo virtual, cálculo de riesgo y roles de inversionista y administrador.

## Carpetas

```
backend/     Flask: config, modelos, rutas, arranque
frontend/    plantillas Jinja2 y estáticos (CSS/JS más adelante)
database/    esquema SQL de referencia + migraciones Alembic
tests/       pytest
instance/    local, no se sube a Git (Flask la crea al correr)
```

`instance/` no va dentro de `database/`. Ahí Flask guarda archivos de runtime (por ejemplo un SQLite de prueba). El esquema versionado vive en `database/`.

## Flujo

```
backend/wsgi.py
  └── create_app()           backend/__init__.py
        ├── config           backend/config.py
        ├── db               backend/conexion.py
        ├── tablas           backend/modelos.py      → MySQL
        └── rutas            backend/rutas.py        → frontend/templates/
```

Migraciones: `database/migrations/` (Alembic). DDL de consulta: `database/esquema.sql`. En local se aplica con `flask db upgrade`, no hace falta ejecutar el `.sql` a mano.

Las capas `services` y `repositories` se agregan cuando haya lógica de negocio.

## Requisitos

- Python 3.12+
- MySQL 8.x (desarrollo y producción)

## Arranque local

```bash
python -m venv .venv
```

En Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edita `.env` (en la raíz del repo, no dentro de `backend/`) con tu `DATABASE_URL`.

```powershell
$env:FLASK_APP = "backend.wsgi"
flask db upgrade
flask run
```

Para probar sin MySQL:

```powershell
$env:FLASK_APP = "backend.wsgi"
$env:APP_CONFIG = "testing"
flask run
```

- Sitio: http://127.0.0.1:5000/
- Salud: http://127.0.0.1:5000/health

## Pruebas

```powershell
pytest --cov=backend --cov-report=term-missing
```

## Documentación técnica

- [TECH_STACK.md](TECH_STACK.md)
- [DB_SCHEMA.md](DB_SCHEMA.md)
- [API_CONVENTIONS.md](API_CONVENTIONS.md)
