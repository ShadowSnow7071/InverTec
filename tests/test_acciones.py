import os

import pytest

from backend.servicios.acciones import AccionServicio


@pytest.fixture(autouse=True)
def _limpiar_cache_y_api_key(monkeypatch):
    # Cada prueba de este archivo simula tener MARKET_DATA_API_KEY configurada,
    # así se ejercita la ruta de caché real en vez del atajo de "sin API key"
    # (ese atajo ya está cubierto indirectamente por el resto del suite).
    monkeypatch.setenv("MARKET_DATA_API_KEY", "clave-de-prueba")
    AccionServicio.limpiar_cache()
    yield
    AccionServicio.limpiar_cache()


def test_ttl_de_cache_es_12_horas_por_defecto():
    assert AccionServicio._cache_segundos() == 60 * 60 * 12


def test_ttl_de_cache_es_configurable_por_variable_de_entorno(monkeypatch):
    monkeypatch.setenv("MARKET_DATA_CACHE_SEGUNDOS", "300")
    assert AccionServicio._cache_segundos() == 300


def test_fallback_se_cachea_y_no_reintenta_la_api_en_cada_llamada(monkeypatch):
    llamadas = []

    def externa_falla(ticker):
        llamadas.append(ticker)
        return None  # simula rate-limit / error de Alpha Vantage

    monkeypatch.setattr(AccionServicio, "_cotizacion_externa", staticmethod(externa_falla))

    primera = AccionServicio._cotizacion("TSLA")
    segunda = AccionServicio._cotizacion("TSLA")

    assert primera["real"] is False
    assert primera == segunda  # mismo precio demo en ambas llamadas
    assert llamadas == ["TSLA"]  # la API externa solo se golpeó una vez, no dos


def test_fallback_de_dos_tickers_distintos_no_se_mezcla(monkeypatch):
    monkeypatch.setattr(AccionServicio, "_cotizacion_externa", staticmethod(lambda ticker: None))

    tesla = AccionServicio._cotizacion("TSLA")
    apple = AccionServicio._cotizacion("AAPL")

    assert tesla["precio"] != apple["precio"]


def test_cotizacion_real_se_cachea_y_no_reintenta_la_api(monkeypatch):
    llamadas = []

    def externa_ok(ticker):
        llamadas.append(ticker)
        return {"precio": "305.50", "cambio_porcentaje": "1.20"}

    monkeypatch.setattr(AccionServicio, "_cotizacion_externa", staticmethod(externa_ok))

    primera = AccionServicio._cotizacion("TSLA")
    segunda = AccionServicio._cotizacion("TSLA")

    assert primera["real"] is True
    assert primera["precio"] == "305.50"
    assert primera == segunda
    assert llamadas == ["TSLA"]
