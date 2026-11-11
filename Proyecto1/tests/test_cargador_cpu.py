import copy
import hashlib
import json
import shutil
from unittest.mock import patch

import pytest
import torch

from src.inferencia import BUNDLE_PREDETERMINADO, ErrorArtefactos, PredictorFraudeCPU


@pytest.fixture(scope='module')
def predictor():
    return PredictorFraudeCPU()


@pytest.fixture(scope='module')
def casos():
    return json.loads((BUNDLE_PREDETERMINADO / 'casos_inferencia.json').read_text())


@pytest.fixture
def bundle(tmp_path):
    for archivo in ['metadatos.json', 'modelo_b_gru.pt', 'escaladores.json', 'vocabularios.json']:
        shutil.copy2(BUNDLE_PREDETERMINADO / archivo, tmp_path / archivo)
    return tmp_path


def modificar(bundle, archivo, funcion, actualizar_hash=False):
    contenido = json.loads((bundle / archivo).read_text())
    funcion(contenido)
    (bundle / archivo).write_text(json.dumps(contenido))
    if actualizar_hash:
        meta = json.loads((bundle / 'metadatos.json').read_text())
        meta['sha256'][archivo] = hashlib.sha256((bundle / archivo).read_bytes()).hexdigest()
        (bundle / 'metadatos.json').write_text(json.dumps(meta))


def test_reproduce_todos_los_casos_en_cpu_sin_mutar_entrada(predictor, casos):
    for caso in casos:
        eventos = copy.deepcopy(caso['transacciones'])
        resultado = predictor.predecir(eventos)
        assert resultado['puntaje_riesgo'] == pytest.approx(caso['puntaje_b_esperado'], abs=1e-6)
        assert resultado['version_modelo'].startswith('B-causal_v2-')
        assert eventos == caso['transacciones']
    assert not predictor._modelo.training
    assert all(p.device.type == 'cpu' and not p.requires_grad for p in predictor._modelo.parameters())
    assert all(p.grad is None for p in predictor._modelo.parameters())
    assert predictor.umbral_sugerido == pytest.approx(0.7336683417085427)


def test_carga_una_vez_y_no_requiere_modelos_a_c(bundle, casos):
    with patch('src.inferencia.torch.load', wraps=torch.load) as cargar:
        modelo = PredictorFraudeCPU(bundle)
        for _ in range(3):
            modelo.predecir(casos[0]['transacciones'])
        assert cargar.call_count == 1


def test_acepta_desconocidos_y_historia_corta(predictor, casos):
    eventos = [dict(casos[0]['transacciones'][0], rubro='nuevo', canal='nuevo', ciudad='nueva')]
    resultado = predictor.predecir(eventos)
    assert 0 <= resultado['puntaje_riesgo'] <= 1
    assert 'decision' not in resultado


@pytest.mark.parametrize('datos', [[], {}, [3], [{'monto': 10}],
    [{'marca_tiempo': True, 'monto': 10}], [{'marca_tiempo': 0, 'monto': float('nan')}],
    [{'marca_tiempo': 0, 'monto': False}]])
def test_rechaza_entrada_invalida(predictor, datos):
    with pytest.raises(ValueError):
        predictor.predecir(datos)


def test_rechaza_desorden_exceso_y_montos_negativos(predictor, casos):
    eventos = max(casos, key=lambda c: len(c['transacciones']))['transacciones']
    for entrada in [eventos[::-1], eventos * 2, [dict(eventos[0], monto=-1)]]:
        with pytest.raises(ValueError):
            predictor.predecir(entrada)


@pytest.mark.parametrize('archivo', ['metadatos.json', 'modelo_b_gru.pt', 'escaladores.json', 'vocabularios.json'])
def test_rechaza_archivo_ausente(bundle, archivo):
    (bundle / archivo).unlink()
    with pytest.raises(ErrorArtefactos):
        PredictorFraudeCPU(bundle)


def test_rechaza_pesos_alterados(bundle):
    with (bundle / 'modelo_b_gru.pt').open('ab') as f:
        f.write(b'alterado')
    with pytest.raises(ErrorArtefactos, match='SHA-256'):
        PredictorFraudeCPU(bundle)


def test_rechaza_version_incompatible(bundle):
    modificar(bundle, 'metadatos.json', lambda d: d.update(version_preprocesamiento='otro'))
    with pytest.raises(ErrorArtefactos, match='Version'):
        PredictorFraudeCPU(bundle)


def test_rechaza_vocabulario_reordenado_aunque_hash_coincida(bundle):
    modificar(bundle, 'vocabularios.json', lambda d: d['rubros'].reverse(), True)
    with pytest.raises(ErrorArtefactos, match='Vocabulario'):
        PredictorFraudeCPU(bundle)


def test_rechaza_arquitectura_incompatible(bundle):
    modificar(bundle, 'metadatos.json', lambda d: d['arquitecturas']['B'].update(n_agregados=15))
    with pytest.raises(ErrorArtefactos, match='Arquitectura'):
        PredictorFraudeCPU(bundle)


def test_rechaza_escalador_invalido_aunque_hash_coincida(bundle):
    modificar(bundle, 'escaladores.json', lambda d: d['secuencia']['desviaciones'].__setitem__(0, 0), True)
    with pytest.raises(ErrorArtefactos, match='Escaladores'):
        PredictorFraudeCPU(bundle)


def test_rechaza_json_malformado(bundle):
    (bundle / 'metadatos.json').write_text('{')
    with pytest.raises(ErrorArtefactos, match='metadatos'):
        PredictorFraudeCPU(bundle)


def test_rechaza_pesos_ilegibles_con_error_claro(bundle):
    archivo = bundle / 'modelo_b_gru.pt'
    archivo.write_bytes(b'no es un checkpoint')
    modificar(bundle, 'metadatos.json', lambda d: d['sha256'].update(
        {'modelo_b_gru.pt': hashlib.sha256(archivo.read_bytes()).hexdigest()}))
    with pytest.raises(ErrorArtefactos, match='pesos'):
        PredictorFraudeCPU(bundle)


def test_rechaza_numero_fuera_de_rango(predictor, casos):
    eventos = [dict(casos[0]['transacciones'][0], monto=10**1000)]
    with pytest.raises(ValueError, match='finito'):
        predictor.predecir(eventos)
