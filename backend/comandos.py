import os

import click

from backend.servicios.acciones import AccionServicio


def registrar_comandos(app):
    @app.cli.command("actualizar-cotizaciones")
    @click.option(
        "--forzar",
        is_flag=True,
        help="Actualiza todo el catálogo aunque las cotizaciones aún estén vigentes.",
    )
    def actualizar_cotizaciones(forzar):
        """Descarga de Alpha Vantage las cotizaciones y las guarda en la base de datos."""
        if not os.environ.get("MARKET_DATA_API_KEY"):
            click.echo("Falta MARKET_DATA_API_KEY: no hay de dónde descargar cotizaciones.")
            raise SystemExit(1)

        resumen = AccionServicio.refrescar_cotizaciones(forzar=forzar)
        click.echo(f"Actualizadas: {', '.join(resumen['actualizadas']) or 'ninguna'}")
        if resumen["fallidas"]:
            click.echo(
                f"Falló: {', '.join(resumen['fallidas'])} "
                "(posible límite diario de Alpha Vantage; se conserva el dato anterior)."
            )
        if resumen["sin_intentar"]:
            click.echo(f"Sin intentar por el fallo anterior: {', '.join(resumen['sin_intentar'])}")
        if resumen["fallidas"]:
            raise SystemExit(1)
