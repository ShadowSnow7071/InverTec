from decimal import Decimal, InvalidOperation
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend.servicios.auth import ErrorNegocio

CATALOGO = {
    "AAPL": {"nombre_empresa": "Apple Inc.", "volatilidad": "0.20"},
    "MSFT": {"nombre_empresa": "Microsoft", "volatilidad": "0.18"},
    "GOOGL": {"nombre_empresa": "Alphabet", "volatilidad": "0.19"},
    "NVDA": {"nombre_empresa": "NVIDIA", "volatilidad": "0.42"},
    "AMZN": {"nombre_empresa": "Amazon", "volatilidad": "0.24"},
    "META": {"nombre_empresa": "Meta", "volatilidad": "0.28"},
    "TSLA": {"nombre_empresa": "Tesla", "volatilidad": "0.55"},
    "NFLX": {"nombre_empresa": "Netflix", "volatilidad": "0.30"},
    "AMD": {"nombre_empresa": "AMD", "volatilidad": "0.43"},
}

PRECIOS_BASE = {
    "AAPL": "214.20",
    "MSFT": "426.75",
    "GOOGL": "178.90",
    "NVDA": "127.85",
    "AMZN": "192.30",
    "META": "490.50",
    "TSLA": "252.10",
    "NFLX": "643.20",
    "AMD": "165.45",
}


class AccionServicio:
    _precios_cache = {}
    _cache_segundos = 60

    @staticmethod
    def _precio_externo(ticker: str):
        api_key = os.environ.get("MARKET_DATA_API_KEY")
        if not api_key:
            return None

        parametros = urlencode(
            {"function": "GLOBAL_QUOTE", "symbol": ticker, "apikey": api_key}
        )
        solicitud = Request(
            f"https://www.alphavantage.co/query?{parametros}",
            headers={"Accept": "application/json", "User-Agent": "InverTec/1.0"},
        )
        try:
            with urlopen(solicitud, timeout=5) as respuesta:
                datos = json.load(respuesta)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            return None

        cotizacion = datos.get("Global Quote", {})
        precio = cotizacion.get("05. price")
        try:
            return Decimal(str(precio)).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError):
            return None

    @classmethod
    def _precio_actual(cls, ticker: str):
        if not os.environ.get("MARKET_DATA_API_KEY"):
            return PRECIOS_BASE[ticker]

        precio_guardado = cls._precios_cache.get(ticker)
        if precio_guardado and time.monotonic() - precio_guardado[0] < cls._cache_segundos:
            return precio_guardado[1]

        precio_externo = cls._precio_externo(ticker)
        if precio_externo is not None:
            precio = str(precio_externo)
            cls._precios_cache[ticker] = (time.monotonic(), precio)
            return precio
        return PRECIOS_BASE[ticker]

    @classmethod
    def listar_catalogo(cls, precios_reales=True):
        return [
            {
                "ticker": ticker,
                "nombre_empresa": datos["nombre_empresa"],
                "precio_actual": (
                    cls._precio_actual(ticker) if precios_reales else PRECIOS_BASE[ticker]
                ),
            }
            for ticker, datos in sorted(CATALOGO.items())
        ]

    @classmethod
    def obtener_por_ticker(cls, ticker: str):
        clave = (ticker or "").strip().upper()
        if clave not in CATALOGO:
            return None
        return {
            "ticker": clave,
            "nombre_empresa": CATALOGO[clave]["nombre_empresa"],
            "precio_actual": cls._precio_actual(clave),
        }

    @staticmethod
    def calcular_riesgo(ticker: str, cantidad, precio_unitario, saldo_virtual):
        clave = (ticker or "").strip().upper()
        if clave not in CATALOGO:
            raise ErrorNegocio("La acción no existe", 404)

        try:
            cantidad_decimal = Decimal(str(cantidad))
            precio_decimal = Decimal(str(precio_unitario))
            saldo_decimal = Decimal(str(saldo_virtual))
        except (InvalidOperation, TypeError, ValueError):
            raise ErrorNegocio("Los valores de cantidad y precio no son válidos")

        if cantidad_decimal <= 0 or precio_decimal <= 0:
            raise ErrorNegocio("La cantidad y el precio deben ser mayores a cero")
        if saldo_decimal <= 0:
            raise ErrorNegocio("El saldo virtual no puede ser cero")

        valor_total = cantidad_decimal * precio_decimal
        exposicion = (valor_total / saldo_decimal) * Decimal("100")
        volatilidad = Decimal(CATALOGO[clave]["volatilidad"])
        riesgo = (exposicion * Decimal("0.60")) + (volatilidad * Decimal("100"))
        riesgo = min(max(riesgo, Decimal("0")), Decimal("100"))

        return {
            "ticker": clave,
            "nombre_empresa": CATALOGO[clave]["nombre_empresa"],
            "cantidad": str(cantidad_decimal),
            "precio_unitario": str(precio_decimal),
            "valor_total": str(valor_total),
            "saldo_virtual": str(saldo_decimal),
            "riesgo_calculado": str(riesgo.quantize(Decimal("0.01"))),
        }
