# MONITOREO.md — InverTec

Estrategia de monitoreo, logging y manejo de errores en producción. Documenta honestamente qué está implementado hoy y qué queda como mejora propuesta, en vez de simular una madurez operativa que el alcance de esta materia no requería.

## Qué existe hoy

- **Logs de aplicación**: Gunicorn corre con `--access-logfile -` y `--error-logfile -` (ver `Docker/entrypoint.sh`), es decir, tanto el log de acceso (cada petición HTTP) como el de error van a stdout/stderr del contenedor. Railway los captura solos y los muestra en la pestaña **Deployments** del servicio, sin configuración adicional.
- **Healthcheck**: `GET /health` (`backend/rutas.py`), usado por dos consumidores distintos: el `HEALTHCHECK` de Docker (reinicia el contenedor si falla 3 veces seguidas) y `healthcheckPath` en `railway.json` (Railway lo usa para decidir si el deployment nuevo está listo antes de enrutarle tráfico).
- **Manejo de errores de negocio**: la clase `ErrorNegocio` (`backend/servicios/auth.py`) centraliza los errores esperables (credenciales inválidas, cuenta bloqueada, rol inválido, etc.), cada uno con su código HTTP, y se traduce a JSON consistente vía `json_error()` en `backend/seguridad.py`. No son errores no controlados, son parte del flujo normal de la API.
- **Un solo logger explícito**: `backend/servicios/auth.py` usa `logging.getLogger(__name__)` para registrar como *warning* cuando Resend rechaza el envío de un correo (por ejemplo, al remitente sandbox no poder mandar a un correo fuera de la cuenta registrada). Es el único punto del código que loggea algo más allá de lo que Gunicorn ya captura por defecto.
- **Reinicio automático**: `restartPolicyType: ON_FAILURE` con `restartPolicyMaxRetries: 3` en `railway.json`, Railway reinicia el servicio solo si el proceso truena.

## Limitaciones conocidas (documentadas a propósito, no descubiertas después)

- El healthcheck no verifica la conexión a MySQL, solo que el proceso Flask responde. Un servicio con la base de datos caída seguiría reportándose "sano".
- No hay logging estructurado (JSON): los logs son texto plano, suficientes para leer manualmente en la pestaña de Railway, pero no pensados para buscarse o agregarse con una herramienta externa.
- No hay un servicio de *error tracking* (tipo Sentry) ni alertas automáticas (correo/Slack) si la tasa de errores 5xx sube; enterarse de un problema depende de entrar a revisar los logs manualmente.
- Railway retiene los logs por un tiempo limitado según el plan; no hay una retención propia ni un log persistente fuera de la plataforma.
- El único logger explícito de la aplicación es el de fallos de Resend; el resto del código no distingue entre "error esperado" y "error inesperado" más allá de lo que ya captura Gunicorn en su log de errores.

## Mejoras propuestas (no implementadas, quedan como trabajo futuro)

1. **Healthcheck que valide la base de datos**: un `SELECT 1` simple contra MySQL dentro de `/health`, para que un fallo de conexión sí se refleje como servicio no sano.
2. **Logging estructurado**: cambiar los loggers propios (y agregar más en puntos clave como `comprar()`/`vender()`) a formato JSON, para poder filtrarlos si algún día se integra una herramienta de agregación de logs.
3. **Error tracking**: integrar algo como Sentry (tiene un plan gratuito suficiente para un proyecto de este tamaño) para recibir una alerta cuando ocurra una excepción no controlada, en vez de depender de revisar logs manualmente.
4. **Métricas básicas**: contar operaciones por minuto, tiempo de respuesta promedio y tasa de error, aunque sea con algo ligero (Railway ya expone métricas de CPU/memoria del servicio, pero no de la aplicación en sí).

Estas cuatro mejoras se dejaron fuera del alcance de esta entrega por la ventana de tiempo disponible, no porque no se identificara la necesidad; se documentan aquí explícitamente para que quede claro que es una decisión consciente y no un vacío no detectado.
