import json
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from src.api import crear_app
from src.inferencia import BUNDLE_PREDETERMINADO, ErrorArtefactos, PredictorFraudeCPU


@pytest.fixture(scope='module')
def casos():
    return json.loads((BUNDLE_PREDETERMINADO / 'casos_inferencia.json').read_text())


@pytest.fixture(scope='module')
def cliente():
    with TestClient(crear_app(hilos=4)) as cliente:
        yield cliente


def test_health_y_documentacion(cliente):
    r = cliente.get('/health')
    assert r.status_code == 200
    assert r.json()['dispositivo'] == 'cpu'
    assert r.json()['estado'] == 'ok'
    assert r.headers['X-Request-ID']
    assert cliente.get('/docs').status_code == 200
    esquema = cliente.get('/openapi.json').json()
    assert '/predict' in esquema['paths']


def test_predicciones_http_coinciden_con_experimento(cliente, casos):
    for caso in casos:
        r = cliente.post('/predict', json={'transacciones': caso['transacciones']})
        assert r.status_code == 200
        assert r.json()['puntaje_riesgo'] == pytest.approx(caso['puntaje_b_esperado'], abs=1e-6)
        assert 'decision' not in r.json()


@pytest.mark.parametrize('cuerpo', [{}, {'transacciones': []}, {'transacciones': [None]},
    {'transacciones': [{'monto': 1}]}, {'transacciones': 'lista'},
    {'transacciones': [], 'etiqueta': 'fraude'}])
def test_estructura_invalida_devuelve_422(cliente, cuerpo):
    assert cliente.post('/predict', json=cuerpo).status_code == 422


@pytest.mark.parametrize('cambio', [dict(monto=-1), dict(monto=True), dict(monto='100'),
    dict(canal='   '), dict(rubro=4), dict(ciudad=None), dict(es_fraude=1)])
def test_eventos_invalidos(cliente, casos, cambio):
    evento = dict(casos[0]['transacciones'][0], **cambio)
    r = cliente.post('/predict', json={'transacciones': [evento]})
    assert r.status_code == 422


def test_rechaza_desorden_y_exceso(cliente, casos):
    eventos = max(casos, key=lambda c: len(c['transacciones']))['transacciones']
    for entrada in [eventos[::-1], eventos * 2]:
        assert cliente.post('/predict', json={'transacciones': entrada}).status_code == 422


def test_desconocidos_son_aceptados(cliente, casos):
    evento = dict(casos[0]['transacciones'][0], rubro='nuevo', ciudad='nueva', canal='nuevo')
    r = cliente.post('/predict', json={'transacciones': [evento]})
    assert r.status_code == 200
    assert 0 <= r.json()['puntaje_riesgo'] <= 1


def test_json_roto_y_no_finito(cliente):
    for entrada in ['{', '{"transacciones":[{"marca_tiempo":NaN,"monto":1,"rubro":"a","canal":"b","ciudad":"c"}]}']:
        r = cliente.post('/predict', content=entrada, headers={'Content-Type': 'application/json'})
        assert r.status_code == 422


def test_carga_unica_por_arranque_y_limpieza(casos):
    app = crear_app(hilos=4)
    with patch('src.api.PredictorFraudeCPU', wraps=PredictorFraudeCPU) as cargar:
        with TestClient(app) as c:
            c.get('/health')
            for _ in range(3):
                assert c.post('/predict', json={'transacciones': casos[0]['transacciones']}).status_code == 200
            assert cargar.call_count == 1
        assert app.state.predictor is None


def test_falla_arranque_con_bundle_incompleto(tmp_path):
    with pytest.raises(ErrorArtefactos):
        with TestClient(crear_app(tmp_path)):
            pass


def test_no_listo_devuelve_503():
    with TestClient(crear_app()) as c:
        c.app.state.predictor = None
        assert c.get('/health').status_code == 503
        assert c.post('/predict', json={'transacciones': [{
            'marca_tiempo': 0, 'monto': 1, 'rubro': 'a', 'canal': 'b', 'ciudad': 'c'}]}).status_code == 503


def test_logs_no_incluyen_transacciones(cliente, casos, caplog):
    with caplog.at_level('INFO', logger='uvicorn.error'):
        r = cliente.post('/predict', json={'transacciones': casos[0]['transacciones']})
    registro = next(json.loads(e.message) for e in caplog.records if 'solicitud_http' in e.message)
    assert registro['id_solicitud'] == r.headers['X-Request-ID']
    assert registro['estado_http'] == 200
    assert registro['duracion_ms'] > 0
    assert 'transacciones' not in registro
    assert 'monto' not in registro


def test_error_interno_controlado(cliente, casos):
    with patch.object(cliente.app.state.predictor, 'predecir', side_effect=RuntimeError('interno')):
        r = cliente.post('/predict', json={'transacciones': casos[0]['transacciones']})
    assert r.status_code == 500
    assert 'interno' not in r.text
