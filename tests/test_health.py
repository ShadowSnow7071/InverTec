def test_index_devuelve_html(client):
    respuesta = client.get("/")
    assert respuesta.status_code == 200
    assert b"InverTec" in respuesta.data


def test_index_ignora_cookie_jwt_invalida(client):
    client.set_cookie("access_token_cookie", "token-invalido")

    respuesta = client.get("/")

    assert respuesta.status_code == 200
    assert b"InverTec" in respuesta.data
    assert any(
        "access_token_cookie=;" in encabezado
        for encabezado in respuesta.headers.getlist("Set-Cookie")
    )


def test_health_devuelve_ok(client):
    respuesta = client.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"status": "ok"}
