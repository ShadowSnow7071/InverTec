import secrets

from flask import g, request

CDN = "https://cdn.jsdelivr.net"

CABECERAS_FIJAS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=(), payment=()",
}


def construir_csp(nonce: str) -> str:

    directivas = [
        "default-src 'self'",
        f"script-src 'self' 'nonce-{nonce}' {CDN}",
        f"style-src 'self' {CDN}",
        "style-src-attr 'unsafe-inline'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
    return "; ".join(directivas)


def _es_https(peticion) -> bool:
    # Railway termina TLS en su proxy y avisa con X-Forwarded-Proto.
    return peticion.is_secure or peticion.headers.get("X-Forwarded-Proto") == "https"


def registrar_cabeceras_seguridad(app):
    @app.before_request
    def generar_nonce_csp():
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.context_processor
    def inyectar_nonce_csp():
        return {"csp_nonce": getattr(g, "csp_nonce", "")}

    @app.after_request
    def agregar_cabeceras(respuesta):
        for nombre, valor in CABECERAS_FIJAS.items():
            respuesta.headers.setdefault(nombre, valor)

        respuesta.headers.setdefault("Content-Security-Policy", construir_csp(getattr(g, "csp_nonce", "")))

        if _es_https(request):
            respuesta.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )

        if request.endpoint != "static":
            respuesta.headers.setdefault("Cache-Control", "no-store")

        return respuesta
