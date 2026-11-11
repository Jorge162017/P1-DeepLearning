import numpy as np
import pytest
from src.config import ConfigGenerador
from src.experimento import Resultados, ejecutar_experimento


@pytest.fixture(scope="module")
def resultados():
    c = ConfigGenerador(n_tarjetas=300, n_dias=180)
    return ejecutar_experimento(c, epocas=3, semilla=0, leer_prueba=True)


def test_devuelve_resultados_completos(resultados):
    assert isinstance(resultados, Resultados)
    for modelo in ["A", "B", "C"]:
        assert "validacion" in resultados.auc_pr[modelo]
        assert 0.0 <= resultados.auc_pr[modelo]["validacion"] <= 1.0
        assert 0.0 <= resultados.umbrales[modelo] <= 1.0


def test_los_umbrales_salen_de_validacion_no_de_prueba(resultados):
    """El umbral sale de validacion, aunque prueba ya este calculada."""
    from src.evaluacion import barrer_umbrales, costo_esperado
    y = resultados.puntajes_validacion["y"]
    for modelo in ["A", "B", "C"]:
        p = resultados.puntajes_validacion[modelo]
        u = resultados.umbrales[modelo]
        assert costo_esperado(y, p, u) == pytest.approx(barrer_umbrales(y, p)["costo"].min())


def test_la_permutacion_no_altera_al_modelo_a(resultados):
    """Los agregados no dependen del orden, asi que si A se mueve hay un error."""
    for variante in ["P1", "P2"]:
        assert resultados.permutacion["A"][variante] == pytest.approx(
            resultados.auc_pr["A"]["validacion"])


def test_la_permutacion_si_toca_a_los_modelos_secuenciales(resultados):
    """Sin afirmar hacia donde: solo que el numero cambia y queda anotado."""
    for modelo in ["B", "C"]:
        assert resultados.permutacion[modelo]["P1"] != resultados.auc_pr[modelo]["validacion"]


def test_el_desglose_cubre_los_cuatro_mecanismos(resultados):
    d = resultados.desglose["B"]
    assert {"F1", "F2", "F3", "F4"} <= set(d.index)
    assert (d["n"] > 0).all()


def test_f4_no_aparece_en_validacion(resultados):
    """F4 quedo fuera del entrenamiento. Si aparece en validacion, algo se rompio."""
    assert "F4" not in resultados.desglose_validacion["B"].index


def test_el_veredicto_de_c_esta_declarado(resultados):
    v = resultados.veredicto_c
    assert set(v) >= {"margen", "supera_umbral", "sostenido_por_mecanismo", "util"}
    assert isinstance(v["util"], bool)


def test_la_economia_reporta_ahorro_contra_a(resultados):
    e = resultados.economia
    for modelo in ["A", "B", "C"]:
        assert e[modelo]["costo_mensual"] > 0
    assert "ahorro_mensual_vs_A" in e["B"]


def test_la_compuerta_del_senuelo_queda_registrada(resultados):
    assert 0.0 <= resultados.go_no_go <= 1.0


def test_es_reproducible():
    c = ConfigGenerador(n_tarjetas=200, n_dias=180)
    a = ejecutar_experimento(c, epocas=2, semilla=7)
    b = ejecutar_experimento(c, epocas=2, semilla=7)
    assert a.auc_pr["B"]["validacion"] == pytest.approx(b.auc_pr["B"]["validacion"])
