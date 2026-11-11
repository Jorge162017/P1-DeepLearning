import numpy as np
import pytest
from src.config import K, ConfigGenerador
from src.generador import generar
from src.ventanas import (ajustar_escaladores, aplicar_escaladores,
                          ajustar_escaladores_agregados,
                          aplicar_escaladores_agregados, construir_dataset)


@pytest.fixture(scope="module")
def datos():
    c = ConfigGenerador(n_tarjetas=150, n_dias=180)
    return construir_dataset(generar(c), c), c


def test_los_escaladores_ignoran_validacion_y_prueba(datos):
    d, _ = datos
    ent = (d.meta["particion"] == "entrenamiento").to_numpy()
    completo = np.ones(len(d.meta), dtype=bool)
    e_ent = ajustar_escaladores(d.seq_num, d.mascara, ent)
    e_todo = ajustar_escaladores(d.seq_num, d.mascara, completo)
    assert not np.allclose(e_ent["medias"], e_todo["medias"]), \
        "los escaladores de entrenamiento no pueden coincidir con los del conjunto completo"


def test_el_escalador_normaliza_solo_lo_observado(datos):
    d, _ = datos
    ent = (d.meta["particion"] == "entrenamiento").to_numpy()
    esc = ajustar_escaladores(d.seq_num, d.mascara, ent)
    z = aplicar_escaladores(d.seq_num, d.mascara, esc)
    sel = d.mascara & ent[:, None]
    assert abs(float(z[sel].mean())) < 0.05
    # las posiciones de relleno quedan en cero, no en un z-score espurio
    assert np.allclose(z[~d.mascara], 0.0)


def test_aplicar_escaladores_es_puro(datos):
    d, _ = datos
    ent = (d.meta["particion"] == "entrenamiento").to_numpy()
    esc = ajustar_escaladores(d.seq_num, d.mascara, ent)
    copia = d.seq_num.copy()
    aplicar_escaladores(d.seq_num, d.mascara, esc)
    assert np.array_equal(d.seq_num, copia), "no debe mutar la entrada"


def test_escaladores_de_agregados_tambien_ignoran_el_futuro(datos):
    d, _ = datos
    ent = (d.meta["particion"] == "entrenamiento").to_numpy()
    esc = ajustar_escaladores_agregados(d.agregados, ent)
    z = aplicar_escaladores_agregados(d.agregados, esc)
    assert abs(float(z[ent].to_numpy().mean())) < 0.05
    assert list(z.columns) == list(d.agregados.columns)


def test_desviacion_cero_no_produce_nan(datos):
    d, _ = datos
    constante = np.zeros_like(d.seq_num)
    esc = ajustar_escaladores(constante, d.mascara, np.ones(len(d.meta), bool))
    z = aplicar_escaladores(constante, d.mascara, esc)
    assert np.isfinite(z).all()
