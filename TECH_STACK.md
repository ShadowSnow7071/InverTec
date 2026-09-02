# TECH_STACK.md — InverTec

Referencia técnica del stack usado en el proyecto, con versión y justificación de cada pieza. Mantener actualizado conforme se agreguen dependencias nuevas.

## Backend

| Herramienta | Versión objetivo | Justificación |
|---|---|---|
| Python | 3.12+ | Base del backend. |
| Flask | 3.x | Da control explícito sobre rutas, servicios y repositorios, sin la capa de "magia" de un framework más grande. |
| SQLAlchemy | 2.x | ORM para MySQL, permite aplicar el patrón Repository. |
| Flask-JWT-Extended | última estable | Autenticación con JWT y soporte de roles (inversionista/administrador). |
| Flask-Migrate / Alembic | última estable | Migraciones de esquema controladas por versión. |

## Base de datos

| Herramienta | Versión objetivo | Justificación |
|---|---|---|
| MySQL | 8.x | Continuidad con lo aprendido en materias anteriores; compatible con el hosting elegido. |

## Frontend

| Herramienta | Versión objetivo | Justificación |
|---|---|---|
| Jinja2 | incluido en Flask | Plantillas del sitio, organizadas en partials reutilizables. |
| Bootstrap | 5.x (CDN) | Biblioteca de componentes UI, resuelve responsividad sin CSS desde cero. |
| Vue | 3.x (CDN, sin build) | Solo en la vista del simulador de riesgo/recompensa, donde sí aporta reactividad. |

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
