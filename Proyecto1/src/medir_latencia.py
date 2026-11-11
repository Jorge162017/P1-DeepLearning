"""Benchmark local en CPU: python -m src.medir_latencia --hilos 4."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
from time import perf_counter_ns

import numpy as np
import torch

from src.inferencia import BUNDLE_PREDETERMINADO, PredictorFraudeCPU


def estadisticas(muestras):
    return {'n': len(muestras), 'mediana_ms': float(np.median(muestras)),
            'p95_ms': float(np.percentile(muestras, 95)),
            'min_ms': float(np.min(muestras)), 'max_ms': float(np.max(muestras))}


def medir(bundle, repeticiones=300, calentamiento=30, cargas=10):
    if repeticiones < 1 or calentamiento < 1 or cargas < 1:
        raise ValueError('Los conteos del benchmark deben ser positivos')
    inicio = perf_counter_ns()
    predictor = PredictorFraudeCPU(bundle)
    carga_inicial = (perf_counter_ns() - inicio) / 1e6
    cargas_ms = []
    for _ in range(cargas):
        inicio = perf_counter_ns()
        PredictorFraudeCPU(bundle)
        cargas_ms.append((perf_counter_ns() - inicio) / 1e6)
    casos = json.loads((bundle / 'casos_inferencia.json').read_text())
    # Ventana minima y maxima, elegidas por longitud; no por latencia o puntaje.
    seleccion = {len(casos[0]['transacciones']): casos[0]}
    for caso in casos:
        seleccion[len(caso['transacciones'])] = caso
    resultados = {}
    for longitud, caso in sorted(seleccion.items()):
        eventos = caso['transacciones']
        for _ in range(calentamiento):
            predictor.predecir(eventos)
        preparacion, inferencia, extremo_a_extremo = [], [], []
        for _ in range(repeticiones):
            inicio = perf_counter_ns()
            tensores = predictor._preparar(eventos)
            preparado = perf_counter_ns()
            predictor._puntuar(tensores)
            fin = perf_counter_ns()
            preparacion.append((preparado - inicio) / 1e6)
            inferencia.append((fin - preparado) / 1e6)
            # Se mide tambien la interfaz publica completa, incluyendo respuesta.
            inicio = perf_counter_ns()
            predictor.predecir(eventos)
            extremo_a_extremo.append((perf_counter_ns() - inicio) / 1e6)
        resultados[str(longitud)] = {'preparacion': estadisticas(preparacion),
                                     'inferencia': estadisticas(inferencia),
                                     'predecir_total': estadisticas(extremo_a_extremo)}
    return {
        'fecha_utc': datetime.now(timezone.utc).isoformat(),
        'version_modelo': predictor.version_modelo,
        'entorno': {'plataforma': platform.platform(), 'python': platform.python_version(),
                    'torch': importlib.metadata.version('torch'), 'dispositivo': 'cpu',
                    'hilos_torch': torch.get_num_threads()},
        'metodo': {'repeticiones_por_longitud': repeticiones,
                   'calentamiento_por_longitud': calentamiento,
                   'repeticiones_carga': cargas,
                   'incluye_importaciones': False,
                   'incluye_red_http': False,
                   'concurrencia': 1,
                   'nota_carga': 'Primera carga en este proceso; cache de disco no vaciada. '
                                 'Cada carga incluye hashes de los tres archivos requeridos.'},
        'carga_primera_ms': carga_inicial,
        'cargas_repetidas': estadisticas(cargas_ms),
        'por_numero_transacciones': resultados,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=BUNDLE_PREDETERMINADO)
    parser.add_argument('--hilos', type=int, default=4)
    parser.add_argument('--repeticiones', type=int, default=300)
    parser.add_argument('--calentamiento', type=int, default=30)
    parser.add_argument('--cargas', type=int, default=10)
    parser.add_argument('--salida', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'docs/latencia_cpu.json')
    args = parser.parse_args()
    if min(args.hilos, args.repeticiones, args.calentamiento, args.cargas) < 1:
        parser.error('Hilos y conteos deben ser positivos')
    torch.set_num_threads(args.hilos)
    resultado = medir(args.bundle, args.repeticiones, args.calentamiento, args.cargas)
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(resultado, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    print(json.dumps(resultado, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
