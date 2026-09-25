FROM python:3.12-slim

# La app no debe generar .pyc ni bufferear stdout/stderr (logs en tiempo real)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_APP=backend.wsgi

WORKDIR /app

# Instalar dependencias primero (capa cacheable: solo se reinstala si cambia requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del proyecto
COPY . .

# Usuario sin privilegios (no correr la app como root)
# Por si el archivo llega con terminadores de línea de Windows (CRLF)
RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p instance \
    && sed -i 's/\r$//' Docker/entrypoint.sh \
    && chmod +x Docker/entrypoint.sh \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Railway/compose consideran el contenedor sano cuando /health responde 200
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

ENTRYPOINT ["./Docker/entrypoint.sh"]
