"""Carga reutilizable del modelo B en CPU, sin entrenamiento ni etiquetas."""
import argparse
import hashlib
import json
import math
from numbers import Real
from pathlib import Path
from pickle import UnpicklingError

import numpy as np
import torch

from src.config import CANALES, CIUDADES, K, RUBROS
from src.modelos import ModeloSecuencial
from src.ventanas import VERSION_PREPROCESAMIENTO, preparar_inferencia

BUNDLE_PREDETERMINADO = Path(__file__).resolve().parents[1] / 'artefactos' / VERSION_PREPROCESAMIENTO


class ErrorArtefactos(ValueError):
    """Bundle incompleto, alterado o incompatible con la preparacion disponible."""


def _leer_json(ruta):
    try:
        contenido = json.loads(ruta.read_text())
    except (OSError, ValueError) as exc:
        raise ErrorArtefactos(f'No se pudo leer {ruta.name}: {exc}') from exc
    if not isinstance(contenido, dict):
        raise ErrorArtefactos(f'{ruta.name} debe contener un objeto JSON')
    return contenido


class PredictorFraudeCPU:
    """Crear una instancia al arrancar y reutilizar `predecir` por solicitud.

    No configura el numero global de hilos de PyTorch. El proceso que lo use
    puede fijarlo al iniciar. El umbral sugerido es una politica independiente.
    """

    def __init__(self, ruta=BUNDLE_PREDETERMINADO):
        ruta = Path(ruta)
        meta = _leer_json(ruta / 'metadatos.json')
        if meta.get('version_preprocesamiento') != VERSION_PREPROCESAMIENTO:
            raise ErrorArtefactos('Version de preprocesamiento incompatible')
        if meta.get('ventana') != K:
            raise ErrorArtefactos(f'El modelo requiere ventanas de {K}')
        # Solo se necesitan estos tres archivos para servir B; los resultados,
        # modelos A/C y figuras no se cargan ni deserializan.
        hashes = meta.get('sha256', {})
        if not isinstance(hashes, dict):
            raise ErrorArtefactos('Falta el manifiesto SHA-256')
        for nombre in ['modelo_b_gru.pt', 'escaladores.json', 'vocabularios.json']:
            try:
                obtenido = hashlib.sha256((ruta / nombre).read_bytes()).hexdigest()
            except OSError as exc:
                raise ErrorArtefactos(f'No se pudo leer {nombre}') from exc
            if obtenido != hashes.get(nombre):
                raise ErrorArtefactos(f'Integridad SHA-256 incorrecta: {nombre}')
        vocab = _leer_json(ruta / 'vocabularios.json')
        for campo, esperado in [('rubros', RUBROS), ('canales', CANALES), ('ciudades', CIUDADES)]:
            if vocab.get(campo) != esperado:
                raise ErrorArtefactos(f'Vocabulario incompatible (incluido orden): {campo}')
        try:
            arquitectura = meta['arquitecturas']['B']
            esperado = dict(n_rubros=len(RUBROS) + 1, n_canales=len(CANALES) + 1,
                            n_ciudades=len(CIUDADES) + 1, n_agregados=0,
                            dim_emb=8, oculto=64, capas=1)
            if arquitectura != esperado or any(type(v) is not int for v in arquitectura.values()):
                raise ErrorArtefactos('Arquitectura de B incompatible con causal_v2')
            umbral = meta['umbrales']['B']
            if isinstance(umbral, bool) or not isinstance(umbral, Real) or not 0 <= umbral <= 1:
                raise ErrorArtefactos('Umbral sugerido de B invalido')
            esc = _leer_json(ruta / 'escaladores.json')['secuencia']
            medias = np.asarray(esc['medias'], dtype=float)
            desv = np.asarray(esc['desviaciones'], dtype=float)
            if (medias.shape != (7,) or desv.shape != (7,) or
                    not np.isfinite(medias).all() or not np.isfinite(desv).all() or (desv <= 0).any()):
                raise ErrorArtefactos('Escaladores de secuencia invalidos')
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, ErrorArtefactos):
                raise
            raise ErrorArtefactos('Metadatos o escaladores de B incompletos/invalidos') from exc
        try:
            modelo = ModeloSecuencial(**arquitectura).to('cpu')
            pesos = torch.load(ruta / 'modelo_b_gru.pt', map_location='cpu', weights_only=True)
            modelo.load_state_dict(pesos, strict=True)
            if not all(torch.isfinite(p).all().item() for p in modelo.parameters()):
                raise ErrorArtefactos('Los pesos contienen valores no finitos')
        except (OSError, RuntimeError, ValueError, TypeError, EOFError, UnpicklingError) as exc:
            raise ErrorArtefactos(f'No se pudieron cargar los pesos de B: {exc}') from exc
        self._modelo = modelo.eval().requires_grad_(False)
        self._escaladores = {'medias': medias, 'desviaciones': desv}
        self._umbral = float(umbral)
        self._version = f'B-{VERSION_PREPROCESAMIENTO}-{hashes["modelo_b_gru.pt"][:12]}'

    @property
    def umbral_sugerido(self):
        return self._umbral

    @property
    def version_modelo(self):
        return self._version

    def _preparar(self, transacciones):
        if not isinstance(transacciones, list) or not 1 <= len(transacciones) <= K:
            raise ValueError(f'transacciones debe ser una lista de 1 a {K} eventos')
        for evento in transacciones:
            if not isinstance(evento, dict):
                raise ValueError('Cada transaccion debe ser un objeto')
            for campo in ['marca_tiempo', 'monto']:
                valor = evento.get(campo)
                try:
                    valido = (not isinstance(valor, bool) and isinstance(valor, Real)
                              and math.isfinite(valor))
                except OverflowError:
                    valido = False
                if not valido:
                    raise ValueError(f'{campo} debe ser un numero finito')
        preparados = preparar_inferencia(transacciones, self._escaladores)
        if not np.isfinite(preparados['num']).all():
            raise ValueError('Las transacciones exceden el rango numerico admitido')
        return {'cat': torch.from_numpy(preparados['cat']).long(),
                'num': torch.from_numpy(preparados['num']).float(),
                'mascara': torch.from_numpy(preparados['mascara']).bool()}

    @torch.inference_mode()
    def _puntuar(self, tensores):
        logits = self._modelo(tensores['cat'], tensores['num'], tensores['mascara'])
        puntaje = float(torch.sigmoid(logits)[0])
        if not math.isfinite(puntaje):
            raise RuntimeError('El modelo produjo un puntaje no finito')
        return puntaje

    def predecir(self, transacciones):
        """Devuelve un puntaje y version; la decision por umbral queda al consumidor."""
        puntaje = self._puntuar(self._preparar(transacciones))
        return {'puntaje_riesgo': puntaje, 'version_modelo': self.version_modelo}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=BUNDLE_PREDETERMINADO)
    parser.add_argument('--entrada', type=Path, required=True,
                        help='JSON con {"transacciones": [...]}')
    args = parser.parse_args()
    try:
        solicitud = json.loads(args.entrada.read_text())
        if not isinstance(solicitud, dict) or 'transacciones' not in solicitud:
            raise ValueError('La entrada debe contener transacciones')
        resultado = PredictorFraudeCPU(args.bundle).predecir(solicitud['transacciones'])
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(2, f'Error: {exc}\n')
    print(json.dumps(resultado, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
