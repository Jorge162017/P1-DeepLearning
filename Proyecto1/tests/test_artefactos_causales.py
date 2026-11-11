"""Verifica los artefactos reales exportados; no vuelve a entrenar."""
import json
from pathlib import Path

import numpy as np

from src.config import CANALES, CIUDADES, RUBROS
from src.evaluacion import auc_pr, barrer_umbrales, costo_esperado
from src.reentrenar import sha256, verificar_bundle_cpu
from src.ventanas import VERSION_PREPROCESAMIENTO

BUNDLE = Path(__file__).resolve().parents[1] / 'artefactos' / VERSION_PREPROCESAMIENTO


def test_hashes_y_paridad_de_pesos_exportados_en_cpu():
    resultado = verificar_bundle_cpu(BUNDLE)
    assert resultado['casos'] >= 5
    assert resultado['hashes_verificados']
    assert resultado['error_maximo'] <= 1e-6


def test_puntajes_exportados_reproducen_metricas_y_umbrales():
    resumen = json.loads((BUNDLE / 'resumen_metricas.json').read_text())
    with np.load(BUNDLE / 'puntajes.npz') as puntajes:
        for m in ['A', 'B', 'C']:
            for particion in ['validacion', 'prueba']:
                y, p = puntajes[f'{particion}_y'], puntajes[f'{particion}_{m}']
                assert np.isfinite(p).all()
                assert ((p >= 0) & (p <= 1)).all()
                assert np.isclose(auc_pr(y, p), resumen['auc_pr'][m][particion])
            y, p = puntajes['validacion_y'], puntajes[f'validacion_{m}']
            assert np.isclose(costo_esperado(y, p, resumen['umbrales'][m]),
                              barrer_umbrales(y, p)['costo'].min())


def test_metadata_corresponde_a_vocabularios_y_arquitectura():
    meta = json.loads((BUNDLE / 'metadatos.json').read_text())
    vocab = json.loads((BUNDLE / 'vocabularios.json').read_text())
    assert meta['version_preprocesamiento'] == VERSION_PREPROCESAMIENTO
    assert meta['entrenamiento']['dispositivo'] == 'cpu'
    assert meta['ventana'] == 20
    assert vocab['rubros'] == RUBROS
    assert vocab['canales'] == CANALES
    assert vocab['ciudades'] == CIUDADES
    for m in ['B', 'C']:
        for parametro, campo in [('n_rubros', 'rubros'), ('n_canales', 'canales'),
                                 ('n_ciudades', 'ciudades')]:
            assert meta['arquitecturas'][m][parametro] == len(vocab[campo]) + 1
    assert meta['arquitecturas']['B']['n_agregados'] == 0
    for archivo, esperado in meta['sha256'].items():
        assert sha256(BUNDLE / archivo) == esperado
