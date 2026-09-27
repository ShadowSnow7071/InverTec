# TECH_STACK.md — InverTec

Referencia técnica del stack usado en el proyecto, con versión y justificación de cada pieza. Mantener actualizado conforme se agreguen dependencias nuevas.

## Backend

| Herramienta | Versión objetivo | Justificación |
|---|---|---|
| Python | 3.12+ | Base del backend. |
| Flask | 3.x | Da control explícito sobre rutas, servicios y repositorios, sin la capa de "magia" de un framework más grande. |
| SQLAlchemy | 2.x | ORM para MySQL, permite aplicar el patrón Repository. |
| Flask-SQLAlchemy | 3.x | Integra SQLAlchemy con el ciclo de vida de Flask. |
| Flask-JWT-Extended | última estable | Autenticación con JWT y soporte de roles (inversionista/administrador). |
| Flask-Migrate / Alembic | última estable | Migraciones de esquema controladas por versión. |
| PyMySQL | última estable | Driver MySQL para SQLAlchemy (`mysql+pymysql://`). |
| python-dotenv | última estable | Carga de variables desde `.env` en desarrollo local. |

## Base de datos

| Herramienta | Versión objetivo | Justificación |
|---|---|---|
| MySQL | 8.x | Continuidad con lo aprendido en materias anteriores; compatible con el hosting elegido. |

## Frontend

| Herramienta | Versión objetivo | Justificación |
|---|---|---|
| Jinja2 | incluido en Flask | Plantillas del sitio, organizadas en partials reutilizables. |
| Bootstrap | 5.x (CDN) | Biblioteca de componentes UI, resuelve responsividad sin CSS desde cero. |
| JavaScript vanilla | ES6+ | Se evaluó Vue 3 por CDN para el simulador de riesgo/recompensa, pero no aportaba beneficio real a ese tamaño de componente, mismo resultado con menos dependencias y sin el riesgo de una integración por CDN sin build. |

## Pruebas y calidad

| Herramienta | Versión objetivo | Justificación |
|---|---|---|
| pytest | última estable | Framework estándar de pruebas en Python. |
| pytest-cov | última estable | Medición de cobertura, meta: 80%+. |
| SonarQube | Cloud/Community | Análisis estático, deuda técnica y code smells. |
| OWASP ZAP | última estable | Escaneo de vulnerabilidades (XSS, inyección SQL). |

## Infraestructura

| Herramienta | Notas |
|---|---|
| GitHub | Repositorio: https://github.com/ShadowSnow7071/InverTec |
| GitHub Projects | Gestión Kanban del backlog. |
| GitHub Actions | CI: pruebas automáticas en cada push/PR. |
| Railway | Hosting de la app Flask + base de datos MySQL administrada. Activar el trial solo en la semana de despliegue (ver matriz de riesgos). |

## Patrones de diseño aplicados

- **Repository**: separa la lógica de negocio del acceso a datos (capa de repositorios sobre SQLAlchemy).
- **Application Factory**: creación de la app Flask mediante una función factory, para facilitar configuración por entorno (desarrollo/pruebas/producción).