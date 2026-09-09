from decimal import Decimal, InvalidOperation

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
    @staticmethod
    def listar_catalogo():
        return [
            {
                "ticker": ticker,
                "nombre_empresa": datos["nombre_empresa"],
                "precio_actual": PRECIOS_BASE[ticker],
            }
            for ticker, datos in sorted(CATALOGO.items())
        ]

    @staticmethod
    def obtener_por_ticker(ticker: str):
        clave = (ticker or "").strip().upper()
        if clave not in CATALOGO:
            return None
        return {
            "ticker": clave,
            "nombre_empresa": CATALOGO[clave]["nombre_empresa"],
            "precio_actual": PRECIOS_BASE[clave],
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
