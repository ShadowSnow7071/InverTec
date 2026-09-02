# InverTec

Simulador de inversión (Tecmilenio) para practicar compras y ventas de acciones con saldo virtual, cálculo de riesgo y roles de inversionista y administrador.

## Flujo de la app

```
wsgi.py
  └── create_app()          app/__init__.py
        ├── config          app/config.py
        ├── db / migrate     app/extensions.py
        ├── modelos         app/models.py      → MySQL (tablas del esquema)
        └── rutas HTML      app/views.py        → templates/
```

Las capas `services` y `repositories` se agregan cuando haya lógica de negocio (auth, portafolio, simulador). Ahora no existen para no simular un flujo que todavía no corre.

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

Edita `.env` con tu `DATABASE_URL` de MySQL, por ejemplo:

```
DATABASE_URL=mysql+pymysql://usuario:password@localhost:3306/invertec
```

Crea la base `invertec` en MySQL y aplica migraciones:

```powershell
$env:FLASK_APP = "wsgi.py"
flask db upgrade
flask run
```

- Sitio: http://127.0.0.1:5000/
- Salud del proceso: http://127.0.0.1:5000/health

## Pruebas

```powershell
pytest --cov=app --cov-report=term-missing
```

Las pruebas usan SQLite en memoria. El entorno real sigue siendo MySQL.

## Documentación técnica

- [TECH_STACK.md](TECH_STACK.md)
- [DB_SCHEMA.md](DB_SCHEMA.md)
- [API_CONVENTIONS.md](API_CONVENTIONS.md)
