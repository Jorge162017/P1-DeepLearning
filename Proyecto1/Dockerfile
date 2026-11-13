# Imagen de servicio: API de riesgo + interfaz web, modelo B causal_v2 en CPU.
# Construir desde Proyecto1/:  docker build -t riesgo-api .
# Ejecutar:                     docker run --rm -p 8000:8000 riesgo-api
FROM python:3.13.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    RIESGO_HILOS=1 \
    OMP_NUM_THREADS=1 \
    PORT=8000

WORKDIR /app

# PyTorch desde el indice oficial de CPU: evita descargar dependencias de GPU.
# Se mantiene la misma version usada para entrenar (2.13.0).
COPY requirements-reentrenamiento.txt requirements-api.txt ./
RUN python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.13.0 \
 && python -m pip install -r requirements-api.txt

# Solo lo necesario para servir: codigo, artefactos causal_v2 e interfaz.
COPY src/ src/
COPY artefactos/causal_v2/ artefactos/causal_v2/
COPY web/ web/

# Usuario sin privilegios (uid 1000 tambien es el que exige Hugging Face Spaces).
RUN useradd --create-home --uid 1000 servicio
USER servicio

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD python -c "import os,urllib.request;urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/health',timeout=4)"
CMD ["sh", "-c", "exec python -m uvicorn src.api:app --host 0.0.0.0 --port ${PORT}"]
