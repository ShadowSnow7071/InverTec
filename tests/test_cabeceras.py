import re
from pathlib import Path

from backend.conexion import db
from backend.modelos import Usuario

PLANTILLAS = Path(__file__).resolve().parent.parent / "frontend" / "templates"

# <script> que se ejecuta desde el propio HTML: sin src y que no sea un bloque de datos JSON.
SCRIPT_INLINE = re.compile(
    r'<script(?![^>]*\bsrc=)(?![^>]*type="application/json")[^>]*>'
)


def registrar_y_obtener_token(client, correo):
    respuesta = client.post(
        "/api/auth/registro",
        json={
            "nombre": correo.split("@")[0],
            "correo": correo,
            "password": "Secreto12!",
        },
    )
    return respuesta.get_json()["access_token"]


def nonce_de_csp(respuesta):
    csp = respuesta.headers["Content-Security-Policy"]
    coincidencia = re.search(r"'nonce-([^']+)'", csp)
    assert coincidencia is not None, "La CSP no trae un nonce para scripts"
    return coincidencia.group(1)


def test_todas_las_plantillas_ponen_nonce_a_sus_scripts_inline():
    # Sin nonce, la CSP bloquearía ese script y la pantalla quedaría sin JavaScript.
    sin_nonce = []
    for plantilla in sorted(PLANTILLAS.glob("*.html")):
        contenido = plantilla.read_text(encoding="utf-8")
        for etiqueta in SCRIPT_INLINE.findall(contenido):
            if 'nonce="{{ csp_nonce }}"' not in etiqueta:
                sin_nonce.append(f"{plantilla.name}: {etiqueta.strip()}")
    assert sin_nonce == []


def test_pagina_html_trae_cabeceras_de_seguridad(client):
    respuesta = client.get("/login")

    assert respuesta.status_code == 200
    assert respuesta.headers["X-Content-Type-Options"] == "nosniff"
    assert respuesta.headers["X-Frame-Options"] == "DENY"
    assert respuesta.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in respuesta.headers["Permissions-Policy"]
    assert respuesta.headers["Cache-Control"] == "no-store"
    csp = respuesta.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp
    assert "'unsafe-inline'" not in csp.split("style-src-attr")[0]


def test_scripts_inline_renderizados_llevan_el_nonce_de_la_respuesta(client):
    token = registrar_y_obtener_token(client, "nonce@example.com")
    cabecera_auth = {"Authorization": f"Bearer {token}"}

    for ruta, headers in [
        ("/login", {}),
        ("/registro", {}),
        ("/simular", cabecera_auth),
        ("/configuracion", cabecera_auth),
    ]:
        respuesta = client.get(ruta, headers=headers)
        assert respuesta.status_code == 200, ruta
        nonce = nonce_de_csp(respuesta)
        html = respuesta.get_data(as_text=True)
        etiquetas = SCRIPT_INLINE.findall(html)
        assert etiquetas, f"{ruta} debería traer al menos un script inline"
        for etiqueta in etiquetas:
            assert f'nonce="{nonce}"' in etiqueta, f"{ruta}: {etiqueta}"


def test_el_nonce_cambia_en_cada_peticion(client):
    primero = nonce_de_csp(client.get("/login"))
    segundo = nonce_de_csp(client.get("/login"))

    assert primero != segundo


def test_hsts_solo_se_envia_cuando_la_peticion_llego_por_https(client):
    sin_https = client.get("/health")
    con_https = client.get("/health", headers={"X-Forwarded-Proto": "https"})

    assert "Strict-Transport-Security" not in sin_https.headers
    assert "max-age=31536000" in con_https.headers["Strict-Transport-Security"]


def test_respuesta_json_de_la_api_no_se_cachea(client):
    respuesta = client.get("/health")

    assert respuesta.headers["Cache-Control"] == "no-store"
    assert respuesta.headers["X-Content-Type-Options"] == "nosniff"


def test_archivos_estaticos_llevan_cabeceras_pero_no_no_store(client):
    respuesta = client.get("/static/styles.css")

    assert respuesta.status_code == 200
    assert respuesta.headers["X-Content-Type-Options"] == "nosniff"
    assert respuesta.headers.get("Cache-Control") != "no-store"


def test_pagina_de_admin_tambien_lleva_nonce(client, app):
    token = registrar_y_obtener_token(client, "admin_nonce@example.com")
    with app.app_context():
        usuario = db.session.query(Usuario).filter_by(correo="admin_nonce@example.com").one()
        usuario.rol = "administrador"
        db.session.commit()

    respuesta = client.get(
        "/admin/usuarios", headers={"Authorization": f"Bearer {token}"}
    )

    assert respuesta.status_code == 200
    nonce = nonce_de_csp(respuesta)
    for etiqueta in SCRIPT_INLINE.findall(respuesta.get_data(as_text=True)):
        assert f'nonce="{nonce}"' in etiqueta
