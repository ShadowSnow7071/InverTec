from datetime import datetime, timezone

from backend.modelos import Usuario


def usuario_publico(usuario: Usuario) -> dict:
    fecha = usuario.fecha_registro
    if fecha is not None and fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    return {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "correo": usuario.correo,
        "rol": usuario.rol.value,
        "fecha_registro": fecha.isoformat() if isinstance(fecha, datetime) else None,
    }
