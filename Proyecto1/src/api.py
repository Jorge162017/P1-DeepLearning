"""API de riesgo e interfaz web: python -m uvicorn src.api:app --host 127.0.0.1 --port 8000."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from time import perf_counter
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
import torch

from src.config import K
from src.inferencia import BUNDLE_PREDETERMINADO, PredictorFraudeCPU

logger = logging.getLogger('uvicorn.error')
CARPETA_WEB = Path(__file__).resolve().parents[1] / 'web'
Texto = Annotated[str, StringConstraints(min_length=1, pattern=r'\S')]


class Transaccion(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)
    marca_tiempo: float = Field(description='Dias desde el origen fijo de la simulacion')
    monto: float = Field(gt=0, description='Monto en quetzales')
    rubro: Texto
    canal: Texto
    ciudad: Texto


class SolicitudPrediccion(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    transacciones: list[Transaccion] = Field(min_length=1, max_length=K)


class RespuestaPrediccion(BaseModel):
    puntaje_riesgo: float = Field(ge=0, le=1)
    version_modelo: str


class RespuestaSalud(BaseModel):
    estado: str
    dispositivo: str
    version_modelo: str


def crear_app(ruta_bundle=None, hilos=None):
    """Cada proceso/worker mantiene una instancia durante su ciclo de vida."""
    ruta = Path(ruta_bundle or os.environ.get('RIESGO_BUNDLE', BUNDLE_PREDETERMINADO))
    numero_hilos = int(hilos if hilos is not None else os.environ.get('RIESGO_HILOS', '4'))
    if numero_hilos < 1:
        raise ValueError('RIESGO_HILOS debe ser positivo')

    @asynccontextmanager
    async def lifespan(aplicacion):
        torch.set_num_threads(numero_hilos)
        # Si falta o es incompatible un artefacto, el arranque falla; no se sirve
        # un modelo alternativo ni se entrena durante una solicitud.
        aplicacion.state.predictor = PredictorFraudeCPU(ruta)
        try:
            yield
        finally:
            aplicacion.state.predictor = None

    aplicacion = FastAPI(title='Riesgo transaccional', version='0.1.0', lifespan=lifespan,
                        description='Demo con datos sinteticos. Puntaje de riesgo no calibrado.')
    aplicacion.state.predictor = None

    @aplicacion.middleware('http')
    async def registrar_uso(request: Request, call_next):
        identificador = uuid4().hex
        inicio, estado = perf_counter(), 500
        try:
            respuesta = await call_next(request)
            estado = respuesta.status_code
            respuesta.headers['X-Request-ID'] = identificador
            return respuesta
        finally:
            predictor = aplicacion.state.predictor
            logger.info(json.dumps({
                'evento': 'solicitud_http', 'id_solicitud': identificador,
                'fecha_utc': datetime.now(timezone.utc).isoformat(),
                'metodo': request.method, 'ruta': request.url.path,
                'estado_http': estado, 'duracion_ms': round((perf_counter() - inicio) * 1000, 3),
                'version_modelo': predictor.version_modelo if predictor else None,
            }))

    @aplicacion.exception_handler(RequestValidationError)
    async def error_validacion(request: Request, exc: RequestValidationError):
        # No devolver ni registrar cuerpos, valores financieros o etiquetas.
        detalles = [{'campo': list(e['loc']), 'mensaje': e['msg'], 'tipo': e['type']}
                    for e in exc.errors()]
        return JSONResponse(status_code=422, content={'detail': detalles})

    def obtener_predictor():
        predictor = aplicacion.state.predictor
        if predictor is None:
            raise HTTPException(status_code=503, detail='Modelo no disponible')
        return predictor

    @aplicacion.get('/health', response_model=RespuestaSalud)
    def health():
        predictor = obtener_predictor()
        return {'estado': 'ok', 'dispositivo': 'cpu', 'version_modelo': predictor.version_modelo}

    @aplicacion.post('/predict', response_model=RespuestaPrediccion)
    def predict(solicitud: SolicitudPrediccion):
        predictor = obtener_predictor()
        try:
            return predictor.predecir([e.model_dump() for e in solicitud.transacciones])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError:
            logger.error('Fallo de inferencia del modelo B')
            raise HTTPException(status_code=500, detail='No se pudo calcular el puntaje') from None

    # Interfaz de demostracion en el mismo origen: sin CORS y con un solo enlace.
    # Se monta al final para que /health, /predict y /docs tengan prioridad.
    if CARPETA_WEB.is_dir():
        aplicacion.mount('/', StaticFiles(directory=CARPETA_WEB, html=True), name='web')

    return aplicacion


app = crear_app()
