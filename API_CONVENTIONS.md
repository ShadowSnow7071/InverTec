# API_CONVENTIONS.md — InverTec

Todos los endpoints van bajo el prefijo `/api`, usan sustantivos en plural, y el verbo HTTP indica la acción.

## Autenticación
- `POST /api/auth/registro` — crea una cuenta nueva
- `POST /api/auth/login` — valida credenciales y devuelve el token JWT
- `POST /api/auth/refresh` — renueva el token sin pedir credenciales de nuevo

## Usuario
- `GET /api/usuarios/me` — perfil del usuario autenticado
- `PATCH /api/usuarios/me` — actualiza datos del propio perfil
- `GET /api/usuarios` — lista todos los usuarios (solo administrador)
- `GET /api/usuarios/estadisticas` — estadísticas del sistema para el dashboard admin: usuarios totales, usuarios activos, operaciones totales, saldo total sumado de todos los portafolios (solo administrador)
- `GET /api/usuarios/auditoria` — últimas 100 operaciones (compras/ventas) de todos los usuarios, con nombre y correo del dueño de cada movimiento (solo administrador)
- `PATCH /api/usuarios/{id}/estado` — bloquea o desbloquea una cuenta (requiere `activo: bool`); una cuenta bloqueada no puede iniciar sesión hasta ser desbloqueada. Un administrador no puede bloquear su propia cuenta (solo administrador)
- `PATCH /api/usuarios/{id}/rol` — cambia el rol de un usuario (requiere `rol: "inversionista" | "administrador"`). Un administrador no puede cambiar su propio rol, para evitar quedarse sin acceso al panel (solo administrador)
- `DELETE /api/usuarios/{id}` — elimina la cuenta de forma permanente, junto con su portafolio e historial de movimientos (cascada). Un administrador no puede eliminar su propia cuenta (solo administrador)

## Portafolio y movimientos
- `GET /api/portafolio` — devuelve el portafolio del usuario autenticado
- `GET /api/portafolio/movimientos` — historial completo de movimientos
- `GET /api/portafolio/movimientos/{id}` — detalle de un movimiento específico
- `POST /api/portafolio/movimientos/riesgo` — evalúa el riesgo de un movimiento hipotético antes de confirmarlo (solo lectura, no guarda nada)
- `POST /api/portafolio/comprar` — registra una compra (requiere `ticker`, `cantidad` y `riesgo_calculado`, revalidado contra el riesgo recalculado en servidor). Si `cantidad` supera 20 acciones, también requiere `password` (la contraseña de la cuenta, para confirmar compras grandes); si falta o no coincide, responde 400/401 y no ejecuta la compra
- `POST /api/portafolio/vender` — registra una venta (mismo contrato que comprar, sin el requisito de `password`)
- `GET /api/portafolio/analisis` — estadísticas del portafolio: saldo disponible, valor total en posiciones, capital invertido (costo promedio ponderado), ganancia/pérdida absoluta y porcentual, distribución de activos, volatilidad por posición y detalle por posición (`precio_promedio`, `precio_actual`, `valor`, `ganancia_perdida`)

## Acciones (catálogo de mercado)
- `GET /api/acciones` — catálogo de acciones disponibles para simular
- `GET /api/acciones/{ticker}` — detalle de una acción: nombre, precio actual, cambio porcentual y volatilidad
- `GET /api/acciones/{ticker}/precio` — precio actual de una acción vía la API externa

El proveedor externo se configura con `MARKET_DATA_API_KEY`. Sin esa variable, o si la
llamada externa falla (por ejemplo, por el límite de peticiones gratuitas), la aplicación
usa precio y cambio porcentual demo para permitir pruebas locales sin depender de Internet;
en ese caso el catálogo de `/api/acciones` marca cada acción con `cambio_real: false`.

## Reglas generales
- Rutas bajo `/api/*` devuelven JSON. Rutas fuera de `/api/*` (login, registro, simulador) devuelven HTML vía Jinja2.
- Todas las rutas protegidas requieren `Authorization: Bearer <token>`.
- Respuestas de error usan el formato `{"error": "mensaje"}` con el código HTTP correspondiente (400, 401, 403, 404).