"""Reentrenamiento causal reproducible: python -m src.reentrenar."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import pickle
import platform
import subprocess
import time

import numpy as np
import torch

from src.config import ConfigGenerador, COSTO_FN, COSTO_FP, K
from src.evaluacion import auc_pr, barrer_umbrales, costo_esperado
from src.experimento import ejecutar_experimento, guardar_artefactos, MARGEN_EXITO_C
from src.modelos import ModeloSecuencial
from src.ventanas import VERSION_PREPROCESAMIENTO, preparar_inferencia

RAIZ = Path(__file__).resolve().parents[1]
PAQUETES = ['torch', 'numpy', 'pandas', 'scikit-learn', 'scipy', 'matplotlib']


def escribir_json(ruta, contenido):
    def convertir(v):
        if isinstance(v, np.ndarray):
            return v.tolist()
        if isinstance(v, np.generic):
            return v.item()
        raise TypeError(type(v).__name__)
    ruta.write_text(json.dumps(contenido, indent=2, ensure_ascii=False,
                               allow_nan=False, default=convertir) + '\n')


def sha256(ruta):
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def resumen(resultados):
    return {
        'auc_pr': resultados.auc_pr,
        'umbrales': resultados.umbrales,
        'metricas_prueba': resultados.metricas_prueba,
        'permutacion': resultados.permutacion,
        'desglose': {m: d.to_dict(orient='index') for m, d in resultados.desglose.items()},
        'desglose_validacion': {m: d.to_dict(orient='index')
                               for m, d in resultados.desglose_validacion.items()},
        'economia': resultados.economia,
        'historial': resultados.historial,
        'veredicto_c': resultados.veredicto_c,
        'senuelo': {'todas_anclas': resultados.go_no_go,
                    'cobro': resultados.go_no_go_cobro},
        'particiones': resultados.particiones,
    }


def validar_resultados(r):
    """Controles del experimento; no exige que gane un modelo particular."""
    for m in ['A', 'B', 'C']:
        y, p = r.puntajes_validacion['y'], r.puntajes_validacion[m]
        assert np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all()
        assert np.isclose(auc_pr(y, p), r.auc_pr[m]['validacion'])
        assert np.isclose(costo_esperado(y, p, r.umbrales[m]),
                          barrer_umbrales(y, p)['costo'].min())
        assert 'F4' not in r.desglose_validacion[m].index
        assert 'F4' in r.desglose[m].index
        for variante in ['P1', 'P2']:
            assert r.permutacion['A'][variante] == r.auc_pr['A']['validacion']
    # Si falla la compuerta, se reporta sin cambiar el generador para forzar un pase.
    return {
        'puntajes_finitos_y_umbral_minimo_validacion': True,
        'control_permutacion_a': True,
        'f4_solo_prueba': True,
        'compuerta_cobro_max_060': bool(r.go_no_go_cobro <= .60),
        'senal_residual_max_070': bool(r.go_no_go <= .70),
    }


def verificar_bundle_cpu(destino):
    """Comprobacion de exportacion; el cargador del servicio se implementa despues."""
    meta = json.loads((destino / 'metadatos.json').read_text())
    for archivo, esperado in meta['sha256'].items():
        assert sha256(destino / archivo) == esperado, archivo
    modelo = ModeloSecuencial(**meta['arquitecturas']['B'])
    modelo.load_state_dict(torch.load(destino / 'modelo_b_gru.pt',
                                      map_location='cpu', weights_only=True))
    modelo.eval()
    esc = json.loads((destino / 'escaladores.json').read_text())['secuencia']
    casos = json.loads((destino / 'casos_inferencia.json').read_text())
    errores = []
    for caso in casos:
        preparado = preparar_inferencia(caso['transacciones'], esc)
        with torch.inference_mode():
            logit = modelo(torch.from_numpy(preparado['cat']).long(),
                           torch.from_numpy(preparado['num']).float(),
                           torch.from_numpy(preparado['mascara']))
            obtenido = float(torch.sigmoid(logit)[0])
        error = abs(obtenido - caso['puntaje_b_esperado'])
        assert error <= 1e-6, (caso['id_tx'], error)
        errores.append(error)
    return {'dispositivo': 'cpu', 'casos': len(casos), 'tolerancia_absoluta': 1e-6,
            'error_maximo': max(errores), 'hashes_verificados': True}


def informe(r, anterior, meta, destino):
    lineas = [
        '# Validación del reentrenamiento causal', '',
        f"Ejecución UTC: {meta['fecha_utc']}. Preprocesamiento: `{VERSION_PREPROCESAMIENTO}`.", '',
        '## Diseño fijado antes de esta ejecución', '',
        'Se conserva el generador original: 6,000 tarjetas, 180 días, semilla 42,',
        'ventanas de 20, 12 épocas, Adam (1e-3), lotes de 256 y entrenamiento en CPU.',
        'Se conserva la mejor época de cada GRU por average precision en validación',
        '(denominada AUC-PR en el Proyecto 1). El umbral minimiza Q4,200 × FN + Q180 × FP',
        'en una rejilla de 200 valores sobre validación. No se optimiza en prueba.', '',
        'Hipótesis original de C: superar al mejor de A y B en al menos 0.02 de',
        'AUC-PR en validación y conservar la exhaustividad de B (tolerancia 0.02)',
        'en al menos dos mecanismos de validación. Este es el criterio ya codificado;',
        'no se modifica para obtener un resultado favorable.', '',
        'La corrección usa la moda de las 19 transacciones anteriores como ciudad base,',
        'con desempate alfabético; sin historia usa la ciudad actual. Todos los eventos',
        'de la ventana se expresan respecto a esa base. Los escaladores se ajustan',
        'exclusivamente en entrenamiento. Los empates temporales conservan el orden recibido.', '',
        '**Limitación:** el conjunto de prueba ya fue observado en Proyecto 1.',
        'Esta ejecución es una reevaluación tras corregir una fuga, no una evaluación',
        'independiente con datos nuevos. No se hicieron búsquedas de hiperparámetros.',
        'Las diferencias también pueden reflejar versiones de librerías distintas.', '',
        '## Datos y particiones', '',
        '| Partición | Transacciones | Fraudes | Tasa |',
        '|---|---:|---:|---:|',
    ]
    for nombre, d in r.particiones.items():
        lineas.append(f"| {nombre} | {d['transacciones']} | {d['fraudes']} | {d['tasa_fraude']:.4%} |")
    lineas += ['', '## Métricas anteriores y corregidas', '',
               'Los valores anteriores corresponden a los artefactos originales con ciudad base',
               'calculada sobre la historia completa; se toman de la tabla del notebook original',
               'con cuatro decimales de precisión publicada.', '',
               '| Modelo | Val. anterior | Val. causal | Prueba anterior | Prueba causal | Umbral causal |',
               '|---|---:|---:|---:|---:|---:|']
    for m in ['A', 'B', 'C']:
        viejo = anterior['auc_pr'][m]
        nuevo = r.auc_pr[m]
        lineas.append(f"| {m} | {viejo['validacion']:.4f} | {nuevo['validacion']:.6f} | "
                      f"{viejo['prueba']:.4f} | {nuevo['prueba']:.6f} | {r.umbrales[m]:.6f} |")
    lineas += ['', '## Permutaciones sobre validación', '',
               '| Modelo | Original | P1: historia barajada | P2: todas las posiciones |',
               '|---|---:|---:|---:|']
    for m in ['A', 'B', 'C']:
        lineas.append(f"| {m} | {r.auc_pr[m]['validacion']:.6f} | "
                      f"{r.permutacion[m]['P1']:.6f} | {r.permutacion[m]['P2']:.6f} |")
    lineas += ['', 'P2 también cambia la posición del ancla, por lo que su caída no aísla',
               'por sí sola el valor del orden histórico; P1 conserva el ancla.', '',
               '## Métricas con umbrales congelados', '',
               '| Modelo | Precisión | Exhaustividad | F1 | VP | FP | VN | FN | Costo bloque (Q) |',
               '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for m in ['A', 'B', 'C']:
        d = r.metricas_prueba[m]
        lineas.append(f"| {m} | {d['precision']:.4f} | {d['exhaustividad']:.4f} | {d['f1']:.4f} | "
                      f"{d['vp']} | {d['fp']} | {d['vn']} | {d['fn']} | {r.economia[m]['costo_bloque']:.0f} |")
    lineas += ['', '## Exhaustividad por mecanismo en prueba', '',
               '| Mecanismo | n | A | B | C |', '|---|---:|---:|---:|---:|']
    for mecanismo in r.desglose['B'].index:
        valores = [r.desglose[m].loc[mecanismo, 'exhaustividad'] for m in ['A', 'B', 'C']]
        lineas.append(f"| {mecanismo} | {int(r.desglose['B'].loc[mecanismo, 'n'])} | " +
                      ' | '.join(f'{v:.4f}' for v in valores) + ' |')
    lineas += ['', '## Compuertas y veredicto', '',
               f'- ROC-AUC señuelo en cobro: **{r.go_no_go_cobro:.6f}** (máximo original: 0.60).',
               f'- ROC-AUC señuelo en todas las anclas: **{r.go_no_go:.6f}** (techo original: 0.70).',
               f"- Margen de C: **{r.veredicto_c['margen']:+.6f}** (exigido: +{MARGEN_EXITO_C:.2f}).",
               f"- Condición por mecanismo: **{r.veredicto_c['sostenido_por_mecanismo']}**.",
               f"- Hipótesis de C cumplida: **{r.veredicto_c['util']}**.", '',
               f"B frente a A en validación: {r.auc_pr['B']['validacion'] - r.auc_pr['A']['validacion']:+.6f}.",
               'La candidatura de B para el demo debe leerse con estas métricas y con los límites',
               'de datos sintéticos. Ni los costos absolutos ni los porcentajes de ahorro',
               'son pronósticos de desempeño bancario real. F4 queda fuera del entrenamiento.', '',
               '## Artefactos para continuar con B en CPU', '',
               f'Carpeta: `{destino.relative_to(RAIZ)}/`. Los artefactos originales no se sobrescriben.', '',
               '- `modelo_b_gru.pt`: state_dict, sin requerir GPU.',
               '- `escaladores.json`: usar la sección `secuencia`.',
               '- `vocabularios.json`: códigos por índice + 1; 0 para desconocidos/relleno.',
               '- `metadatos.json`: arquitectura, versiones, semilla, umbrales y hashes.',
               '- `casos_inferencia.json`: entradas sintéticas y puntajes esperados para comprobar carga.',
               '- `verificacion_cpu.json`: comprobación de exportación y paridad, no un servidor de producción.',
               '- `resumen_metricas.json`, `resultados.pkl` y `puntajes.npz`: resultados auditables.',
               '- `figuras/`: las cinco figuras regeneradas.', '',
               'El contrato usa `marca_tiempo` en días desde un origen fijo: la simulación comienza',
               'en día 0 y el día de semana se calcula como piso(día) módulo 7. La integración',
               'de fechas reales debe fijar y conservar esa convención. El puntaje es una salida',
               'sigmoide de un modelo con ponderación de clases; no se afirma que esté calibrado.', '',
               'Las instrucciones reproducibles y los controles de exportación están en el README.', '']
    return '\n'.join(lineas)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hilos', type=int, default=4)
    args = parser.parse_args()
    if args.hilos < 1:
        parser.error('--hilos debe ser positivo')
    os.chdir(RAIZ)
    torch.set_num_threads(args.hilos)
    torch.use_deterministic_algorithms(True)
    inicio = time.monotonic()
    destino = RAIZ / 'artefactos' / VERSION_PREPROCESAMIENTO
    if destino.exists():
        raise SystemExit(f'{destino} ya existe; conservar o mover esa ejecución antes de repetir.')
    # La tabla publicada evita deserializar el pickle original de otra version.
    notebook = json.loads((RAIZ / 'proyecto1_herrarte_lopez.ipynb').read_text())
    anterior = {'auc_pr': {}, 'umbrales': {},
                'origen': 'proyecto1_herrarte_lopez.ipynb: tabla AUC-PR publicada',
                'decimales_publicados': 4}
    for celda in notebook['cells']:
        for salida in celda.get('outputs', []):
            texto = ''.join(salida.get('data', {}).get('text/plain', []))
            if 'AUC-PR validacion' not in texto or 'AUC-PR prueba' not in texto:
                continue
            for linea in texto.splitlines():
                campos = linea.split()
                if len(campos) == 7 and campos[0] in ['A', 'B', 'C']:
                    m = campos[0]
                    anterior['auc_pr'][m] = {'validacion': float(campos[1]),
                                             'prueba': float(campos[2])}
                    anterior['umbrales'][m] = float(campos[3])
    assert set(anterior['auc_pr']) == {'A', 'B', 'C'}, 'Falta tabla original'

    config = ConfigGenerador()
    r = ejecutar_experimento(config, epocas=12, semilla=42, leer_prueba=True, verbose=True)
    controles = validar_resultados(r)
    destino.mkdir(parents=True)
    guardar_artefactos(r, config, ruta=destino)
    escribir_json(destino / 'resumen_anterior.json', anterior)
    escribir_json(destino / 'resumen_metricas.json', resumen(r))
    escribir_json(destino / 'casos_inferencia.json', r.casos_inferencia)
    # Evitar duplicar los modelos dentro del pickle de resultados.
    del r._modelos, r._escaladores
    with (destino / 'resultados.pkl').open('wb') as f:
        pickle.dump(r, f)
    np.savez_compressed(destino / 'puntajes.npz',
                        **{f'validacion_{k}': v for k, v in r.puntajes_validacion.items()},
                        **{f'prueba_{k}': v for k, v in r.puntajes_prueba.items()})
    from src import figuras
    figuras.RUTA = destino / 'figuras'
    figuras.fig_particion(config)
    figuras.fig_curvas_pr(r.puntajes_prueba['y'],
                         {m: r.puntajes_prueba[m] for m in ['A', 'B', 'C']},
                         {m: r.auc_pr[m]['prueba'] for m in ['A', 'B', 'C']},
                         'Prueba — preprocesamiento causal v2')
    figuras.fig_permutacion({m: r.auc_pr[m]['validacion'] for m in ['A', 'B', 'C']}, r.permutacion)
    figuras.fig_desglose(r.desglose)
    figuras.fig_costo(r.puntajes_validacion['y'],
                      {m: r.puntajes_validacion[m] for m in ['A', 'B', 'C']}, r.umbrales)
    arquitecturas = {m: dict(n_rubros=11, n_canales=5, n_ciudades=11,
                             n_agregados=0 if m == 'B' else 15,
                             dim_emb=8, oculto=64, capas=1) for m in ['B', 'C']}
    meta = {
        'version_preprocesamiento': VERSION_PREPROCESAMIENTO,
        'fecha_utc': datetime.now(timezone.utc).isoformat(),
        'git_head_base': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'codigo_sha256': {str(p.relative_to(RAIZ)): sha256(p)
                           for p in sorted((RAIZ / 'src').glob('*.py'))},
        'python': platform.python_version(), 'plataforma': platform.platform(),
        'versiones': {p: importlib.metadata.version(p) for p in PAQUETES},
        'entrenamiento': {'semilla': 42, 'epocas': 12, 'lote': 256, 'lr': .001,
                          'dispositivo': 'cpu', 'hilos': args.hilos,
                          'algoritmos_deterministas': True,
                          'seleccion_epoca': 'max_average_precision_validacion'},
        'config_generador': asdict(config), 'ventana': K,
        'arquitecturas': arquitecturas, 'umbrales': r.umbrales,
        'costos': {'fn': COSTO_FN, 'fp': COSTO_FP},
        'criterio_c': {'margen_minimo': MARGEN_EXITO_C,
                       'tolerancia_exhaustividad': .02, 'min_mecanismos': 2},
        'controles': controles,
        'duracion_segundos': time.monotonic() - inicio,
        'sha256': {str(p.relative_to(destino)): sha256(p)
                   for p in sorted(destino.rglob('*')) if p.is_file()},
    }
    escribir_json(destino / 'metadatos.json', meta)
    verificacion = verificar_bundle_cpu(destino)
    escribir_json(destino / 'verificacion_cpu.json', verificacion)
    docs = RAIZ / 'docs'
    docs.mkdir(exist_ok=True)
    (docs / 'VALIDACION_CAUSAL.md').write_text(informe(r, anterior, meta, destino))
    print(json.dumps({'auc_pr': r.auc_pr, 'umbrales': r.umbrales,
                      'veredicto_c': r.veredicto_c, 'controles': controles,
                      'verificacion_cpu': verificacion}, indent=2), flush=True)
    print(f'Listo: {destino} ({time.monotonic() - inicio:.1f}s)', flush=True)


if __name__ == '__main__':
    main()
