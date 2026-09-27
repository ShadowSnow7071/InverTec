# DEPLOY.md — InverTec

Guía de despliegue en producción. Documenta el proceso real ya ejecutado contra Railway, no un plan teórico: cada paso, variable y advertencia de aquí abajo fue validado en un despliegue funcionando. Mantenerla actualizada si el proceso cambia.

## Arquitectura de despliegue

- **Hosting**: Railway, un servicio (`invertec`) con la aplicación Flask + Gunicorn, más un servicio administrado de **MySQL** dentro del mismo proyecto.
- **Build**: imagen Docker construida a partir de `Docker/Dockerfile`, no del código Python interpretado directamente por Railway.
- **CI/CD**: GitHub Actions. El workflow `CI` (`.github/workflows/ci.yml`) corre `pytest` con cobertura mínima obligatoria (`--cov-fail-under=80`) en cada push/PR. El workflow `CD` (`.github/workflows/cd.yml`) se dispara únicamente cuando `CI` termina exitosamente sobre la rama `main`, y despliega con el Railway CLI.
- **Migraciones**: se aplican solas al arrancar el contenedor (`flask db upgrade`, dentro de `Docker/entrypoint.sh`), no es un paso manual aparte.

## Requisitos previos

- Cuenta de Railway con el proyecto `invertec` creado (MySQL + servicio `invertec` dentro del mismo proyecto, ambiente `production`).
- Railway CLI instalado localmente (`npm i -g @railway/cli`) para el primer despliegue manual.
- Cuenta de Resend, con el remitente sandbox `onboarding@resend.dev` mientras no se verifique un dominio propio (limitación real: solo puede enviar correos a la cuenta de Resend registrada).
- Una API key de Alpha Vantage (opcional; sin ella, el catálogo de Mercado cae a precios simulados pero estables por ticker).

## Variables de entorno del servicio `invertec`

| Variable | Valor / cómo obtenerlo | Notas |
|---|---|---|
| `APP_CONFIG` | `production` | Selecciona la configuración de `backend/config.py`. |
| `SECRET_KEY` | `python3 -c "import secrets; print(secrets.token_hex(32))"` | 32+ caracteres, distinto de `JWT_SECRET_KEY`. |
| `JWT_SECRET_KEY` | Igual que arriba, generado aparte | No reusar el mismo valor que `SECRET_KEY`. |
| `DATABASE_URL` | `mysql+pymysql://${{MySQL.MYSQLUSER}}:${{MySQL.MYSQLPASSWORD}}@${{MySQL.MYSQLHOST}}:${{MySQL.MYSQLPORT}}/${{MySQL.MYSQLDATABASE}}` | Sintaxis de referencia de Railway al servicio MySQL del mismo proyecto. |
| `RESEND_API_KEY` | Generada en el dashboard de Resend | Para el correo de recuperación de contraseña. |
| `RESEND_FROM_EMAIL` | `onboarding@resend.dev` | Remitente sandbox, ver limitación arriba. |
| `APP_BASE_URL` | URL pública generada por Railway (ver siguiente sección) | Se usa para construir los links de recuperación de contraseña. |
| `MARKET_DATA_API_KEY` | API key de Alpha Vantage | Opcional, ver arriba. |
| `MARKET_DATA_CACHE_SEGUNDOS` | Opcional, por defecto `43200` (12h) | Cuánto se cachea cada cotización (real o simulada) antes de volver a consultar la API externa. |
| `WEB_CONCURRENCY` | `2` | Número de workers de Gunicorn. |

## Configuración inicial en Railway

1. Crear un proyecto vacío en Railway, **sin conectar el GitHub App todavía** (evita choques con el despliegue automático antes de probarlo a mano).
2. Agregar la base de datos: `+ New → Database → MySQL`. Railway la aprovisiona sola y expone las variables `MYSQLUSER`, `MYSQLPASSWORD`, `MYSQLHOST`, `MYSQLPORT` y `MYSQLDATABASE`.
3. Agregar un servicio vacío llamado exactamente **`invertec`** (debe coincidir con el `--service invertec` de `cd.yml`, si no coincide el despliegue automático falla en silencio).
4. **Importante — hallazgo real de este despliegue**: aunque el repo trae un `railway.json` en la raíz con `"builder": "DOCKERFILE"` y `"dockerfilePath": "Docker/Dockerfile"`, Railway no lo detectó y usó su detector automático (Railpack), que falló por no encontrar un comando de arranque explícito. La solución fue configurarlo a mano: en el servicio `invertec` → **Settings → Build**, cambiar **Builder** a `Dockerfile` y **Dockerfile Path** a `Docker/Dockerfile`. Confirmar esto ANTES del primer `railway up`, para no perder tiempo en el mismo error.
5. Cargar las variables de entorno de la tabla anterior en el servicio `invertec` (pestaña **Variables**).
6. Generar el dominio público: **Settings → Networking → Generate Domain**, y completar `APP_BASE_URL` con esa URL.

## Primer despliegue (manual)

Desde la raíz del repo, con el Railway CLI ya instalado:

```
railway login
railway link      # elegir el proyecto invertec, servicio invertec
railway up
```

Esto construye la imagen con `Docker/Dockerfile`, corre `flask db upgrade` y levanta Gunicorn. Validar, antes de automatizar nada:

- `GET /health` responde `200`.
- El flujo de registro (`POST /registro`) y login funcionan de punta a punta.
- Los logs del deployment (pestaña **Deployments** del servicio) no muestran errores.

## Despliegue automático (CI/CD)

1. En Railway: **Settings del proyecto → Tokens → New Token**, ambiente `production`. El nombre es libre (ej. `cd-invertec`), solo es para identificarlo en la lista.
2. En GitHub: **Settings → Secrets and variables → Actions → New repository secret**, nombre `RAILWAY_TOKEN`, valor el token generado.
3. De ahí en adelante, cada push a `main` que pase el workflow `CI` dispara automáticamente `CD`, que corre `railway up --service invertec --detach` sin intervención manual.

**Gotcha conocido**: versiones del Railway CLI `>=5.3.0` han tenido reportes de romper la autenticación por project-token dentro de GitHub Actions (`Not signed in.`). Por eso `cd.yml` fija la versión con `npm install -g @railway/cli@5.2.0`, en vez de instalar `latest`.

## Crear el primer usuario administrador

No existe un flujo en la interfaz para autoasignarse el rol de administrador (decisión consciente, para no exponer esa acción sin control adicional). El camino usado en este despliegue:

1. Registrarse normal como usuario desde `/registro`.
2. En Railway, entrar al servicio **MySQL → Data** (o la pestaña de consultas) y correr:

```sql
UPDATE usuario SET rol = 'administrador' WHERE correo = 'correo_del_admin@ejemplo.com';
```

3. Iniciar sesión de nuevo con ese usuario: ya debería aparecer "Administración" en el sidebar, o se puede entrar directo a `/admin/usuarios`.

Queda pendiente, si se retoma el proyecto más adelante, envolver esto en un comando `flask crear-admin` vía CLI de Flask, para no depender de una consulta SQL manual contra producción.
