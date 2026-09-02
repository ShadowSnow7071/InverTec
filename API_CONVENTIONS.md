# API_CONVENTIONS.md — InverTec

Todos los endpoints van bajo el prefijo `/api/v1`, usan sustantivos en plural, y el verbo HTTP indica la acción.

## Autenticación
- `POST /api/v1/auth/registro` — crea una cuenta nueva
- `POST /api/v1/auth/login` — valida credenciales y devuelve el token JWT
- `POST /api/v1/auth/refresh` — renueva el token sin pedir credenciales de nuevo

## Usuario
- `GET /api/v1/usuarios/me` — perfil del usuario autenticado
- `PATCH /api/v1/usuarios/me` — actualiza datos del propio perfil
- `GET /api/v1/usuarios` — lista todos los usuarios (solo administrador)

## Portafolio y movimientos
- `GET /api/v1/portafolio` — devuelve el portafolio del usuario autenticado
- `GET /api/v1/portafolio/movimientos` — historial completo de movimientos
- `POST /api/v1/portafolio/movimientos` — registra una compra o venta nueva
- `GET /api/v1/portafolio/movimientos/{id}` — detalle de un movimiento específico
- `POST /api/v1/portafolio/movimientos/riesgo` — evalúa el riesgo de un movimiento hipotético antes de confirmarlo (solo lectura, no guarda nada)

## Acciones (catálogo de mercado)
- `GET /api/v1/acciones` — catálogo de acciones disponibles para simular
- `GET /api/v1/acciones/{ticker}/precio` — precio actual de una acción vía la API externa

## Reglas generales
- Rutas bajo `/api/*` devuelven JSON. Rutas fuera de `/api/*` (login, registro, simulador) devuelven HTML vía Jinja2.
- Todas las rutas protegidas requieren `Authorization: Bearer <token>`.
- Respuestas de error usan el formato `{"error": "mensaje"}` con el código HTTP correspondiente (400, 401, 403, 404).
