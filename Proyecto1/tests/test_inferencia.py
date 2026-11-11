import numpy as np
import pandas as pd
import pytest

from src.config import ConfigGenerador
from src.ventanas import (construir_dataset, preparar_inferencia,
                          aplicar_escaladores)
from tests.test_ventanas import _marco_a_mano

ESC = {"medias": np.arange(7), "desviaciones": np.ones(7) * 2}
CAMPOS = ["marca_tiempo", "monto", "rubro", "canal", "ciudad"]


def test_inferencia_sin_etiquetas_coincide_con_entrenamiento():
    df = _marco_a_mano()
    d = construir_dataset(df, ConfigGenerador())
    r = preparar_inferencia(df[CAMPOS].to_dict("records"), ESC)
    np.testing.assert_array_equal(r["cat"], d.seq_cat[-1:])
    np.testing.assert_array_equal(r["mascara"], d.mascara[-1:])
    np.testing.assert_allclose(r["num"], aplicar_escaladores(
        d.seq_num, d.mascara, ESC)[-1:])


def test_futuro_no_cambia_ninguna_caracteristica_del_pasado():
    df = _marco_a_mano()
    futuro = pd.concat([df, pd.concat([df.iloc[[-1]].assign(
        id_tx=10+i, marca_tiempo=20+i, ciudad="madrid") for i in range(10)])],
        ignore_index=True)
    a = construir_dataset(df, ConfigGenerador())
    b = construir_dataset(futuro, ConfigGenerador())
    np.testing.assert_array_equal(a.seq_num, b.seq_num[:len(df)])
    np.testing.assert_array_equal(a.seq_cat, b.seq_cat[:len(df)])
    pd.testing.assert_frame_equal(a.agregados, b.agregados.iloc[:len(df)])
    assert a.seq_num[-1, -1, 6] == 2  # madrid, base previa guatemala


def test_ventana_de_20_reproduce_historial_largo():
    df = pd.concat([_marco_a_mano().assign(
        id_tx=np.arange(4)+i*4, marca_tiempo=np.arange(4)+i*4,
        ciudad="madrid" if i < 6 else "guatemala") for i in range(12)],
        ignore_index=True)
    d = construir_dataset(df, ConfigGenerador())
    r = preparar_inferencia(df[CAMPOS].tail(20).to_dict("records"), ESC)
    np.testing.assert_allclose(r["num"], aplicar_escaladores(
        d.seq_num[-1:], d.mascara[-1:], ESC))


def test_categorias_nuevas_se_codifican_como_cero_sin_enmascarar_evento():
    eventos = _marco_a_mano()[CAMPOS].iloc[:1].assign(
        rubro="nuevo", canal="nuevo", ciudad="nueva")
    r = preparar_inferencia(eventos.to_dict("records"), ESC)
    assert (r["cat"] == 0).all()
    assert r["mascara"].sum() == 1
    assert (r["num"][~r["mascara"]] == 0).all()


@pytest.mark.parametrize("cambio", [
    {"monto": -1}, {"monto": float("nan")}, {"marca_tiempo": float("inf")},
    {"rubro": None}, {"canal": ""},
])
def test_entrada_invalida(cambio):
    eventos = _marco_a_mano()[CAMPOS].assign(**cambio)
    with pytest.raises(ValueError):
        preparar_inferencia(eventos.to_dict("records"), ESC)


def test_rechaza_vacio_desorden_y_exceso():
    eventos = _marco_a_mano()[CAMPOS].to_dict("records")
    for datos in [[], eventos[::-1], eventos * 6]:
        with pytest.raises(ValueError):
            preparar_inferencia(datos, ESC)


def test_ciudad_base_desempata_solo_con_historia_previa():
    df = _marco_a_mano().iloc[:3].copy()
    # Antes del tercer evento hay empate: guatemala gana alfabeticamente.
    # Incluir el ancla haria ganar madrid, ocultando su lejania.
    df['ciudad'] = ['guatemala', 'madrid', 'madrid']
    d = construir_dataset(df, ConfigGenerador())
    assert d.seq_num[-1, -1, 6] == 2
    assert d.agregados.iloc[-1]['es_ciudad_base'] == 0
    np.testing.assert_array_equal(d.seq_num[-1, -3:, 6], [0, 2, 2])
