def test_index_devuelve_html(client):
    respuesta = client.get("/")
    assert respuesta.status_code == 200
    assert b"InverTec" in respuesta.data


def test_health_devuelve_ok(client):
    respuesta = client.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"status": "ok"}
