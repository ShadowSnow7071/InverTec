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
    def _cotizacion_externa(ticker: str):
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
        cambio_porcentaje = cotizacion.get("10. change percent", "").rstrip("%")
        try:
            precio_decimal = Decimal(str(precio)).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError):
            return None
        try:
            cambio_decimal = Decimal(str(cambio_porcentaje)).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError):
            cambio_decimal = None
        return {"precio": str(precio_decimal), "cambio_porcentaje": str(cambio_decimal) if cambio_decimal is not None else None}

    @staticmethod
    def _cambio_demo(ticker: str):
        # Sin API key: cambio simulado pero estable por ticker (mismo valor en cada carga),
        # NO son datos de mercado reales.
        semilla = sum(ord(caracter) for caracter in ticker)
        return str(Decimal((semilla % 400) - 200) / Decimal("100"))

    @classmethod
    def _cotizacion(cls, ticker: str):
        if not os.environ.get("MARKET_DATA_API_KEY"):
            return {"precio": PRECIOS_BASE[ticker], "cambio_porcentaje": cls._cambio_demo(ticker), "real": False}

        guardado = cls._precios_cache.get(ticker)
        if guardado and time.monotonic() - guardado[0] < cls._cache_segundos:
            return guardado[1]

        cotizacion = cls._cotizacion_externa(ticker)
        if cotizacion is not None:
            resultado = {**cotizacion, "real": True}
            cls._precios_cache[ticker] = (time.monotonic(), resultado)
            return resultado
        return {"precio": PRECIOS_BASE[ticker], "cambio_porcentaje": cls._cambio_demo(ticker), "real": False}

    @classmethod
    def _precio_actual(cls, ticker: str):
        return cls._cotizacion(ticker)["precio"]

    @classmethod
    def listar_catalogo(cls, precios_reales=True):
        resultado = []
        for ticker, datos in sorted(CATALOGO.items()):
            if precios_reales:
                cotizacion = cls._cotizacion(ticker)
            else:
                cotizacion = {"precio": PRECIOS_BASE[ticker], "cambio_porcentaje": cls._cambio_demo(ticker), "real": False}
            resultado.append(
                {
                    "ticker": ticker,
                    "nombre_empresa": datos["nombre_empresa"],
                    "precio_actual": cotizacion["precio"],
                    "cambio_porcentaje": cotizacion["cambio_porcentaje"],
                    "cambio_real": cotizacion["real"],
                }
            )
        return resultado

    @classmethod
    def obtener_por_ticker(cls, ticker: str):
        clave = (ticker or "").strip().upper()
        if clave not in CATALOGO:
            return None
        volatilidad = Decimal(CATALOGO[clave]["volatilidad"]) * Decimal("100")
        cotizacion = cls._cotizacion(clave)
        return {
            "ticker": clave,
            "nombre_empresa": CATALOGO[clave]["nombre_empresa"],
            "precio_actual": cotizacion["precio"],
            "cambio_porcentaje": cotizacion["cambio_porcentaje"],
            "cambio_real": cotizacion["real"],
            "volatilidad": str(volatilidad.quantize(Decimal("0.01"))),
        }

    @classmethod
    def calcular_riesgo(cls, ticker: str, cantidad, saldo_virtual):
        clave = (ticker or "").strip().upper()
        if clave not in CATALOGO:
            raise ErrorNegocio("La acción no existe", 404)

        try:
            cantidad_decimal = Decimal(str(cantidad))
            saldo_decimal = Decimal(str(saldo_virtual))
        except (InvalidOperation, TypeError, ValueError):
            raise ErrorNegocio("La cantidad o el saldo no son válidos")

        precio_decimal = Decimal(cls._precio_actual(clave))

        if cantidad_decimal <= 0 or precio_decimal <= 0:
            raise ErrorNegocio("La cantidad y el precio deben ser mayores a cero")
        if saldo_decimal <= 0:
            raise ErrorNegocio("El saldo virtual no puede ser cero")

        valor_total = cantidad_decimal * precio_decimal
        exposicion = (valor_total / saldo_decimal) * Decimal("100")
        volatilidad = Decimal(CATALOGO[clave]["volatilidad"])
        riesgo = (exposicion * Decimal("0.60")) + (volatilidad * Decimal("100"))
        riesgo = min(max(riesgo, Decimal("0")), Decimal("100"))

        if riesgo < Decimal("35"):
            riesgo_nivel = "bajo"
        elif riesgo < Decimal("70"):
            riesgo_nivel = "medio"
        else:
            riesgo_nivel = "alto"

        return {
            "ticker": clave,
            "nombre_empresa": CATALOGO[clave]["nombre_empresa"],
            "cantidad": str(cantidad_decimal),
            "precio_unitario": str(precio_decimal),
            "valor_total": str(valor_total),
            "saldo_virtual": str(saldo_decimal),
            "exposicion_porcentaje": str(exposicion.quantize(Decimal("0.01"))),
            "volatilidad_porcentaje": str(
                (volatilidad * Decimal("100")).quantize(Decimal("0.01"))
            ),
            "riesgo_calculado": str(riesgo.quantize(Decimal("0.01"))),
            "riesgo_nivel": riesgo_nivel,
        }