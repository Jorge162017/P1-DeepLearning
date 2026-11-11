import numpy as np
import pandas as pd
from src.config import ConfigGenerador, RUBROS, CANALES, CIUDADES
from src.generador import generar_perfiles, generar_trafico_legitimo


def _pequena():
    return ConfigGenerador(n_tarjetas=200, n_dias=60)


def test_misma_semilla_produce_perfiles_identicos():
    c = _pequena()
    a = generar_perfiles(c, np.random.default_rng(c.semilla))
    b = generar_perfiles(c, np.random.default_rng(c.semilla))
    pd.testing.assert_frame_equal(a, b)


def test_semillas_distintas_producen_perfiles_distintos():
    c = _pequena()
    a = generar_perfiles(c, np.random.default_rng(1))
    b = generar_perfiles(c, np.random.default_rng(2))
    assert not a["monto_mu"].equals(b["monto_mu"])


def test_perfiles_tienen_una_fila_por_tarjeta():
    c = _pequena()
    p = generar_perfiles(c, np.random.default_rng(c.semilla))
    assert len(p) == c.n_tarjetas
    assert p["id_tarjeta"].is_unique
    assert p["ciudad_base"].isin(CIUDADES).all()


def test_mezclas_son_distribuciones_validas():
    c = _pequena()
    p = generar_perfiles(c, np.random.default_rng(c.semilla))
    for col, n in [("mezcla_rubros", len(RUBROS)), ("mezcla_canales", len(CANALES))]:
        m = np.stack(p[col].to_numpy())
        assert m.shape == (c.n_tarjetas, n)
        assert np.allclose(m.sum(axis=1), 1.0)
        assert (m >= 0).all()


def test_trafico_legitimo_esta_ordenado_y_dentro_del_horizonte():
    c = _pequena()
    rng = np.random.default_rng(c.semilla)
    p = generar_perfiles(c, rng)
    df = generar_trafico_legitimo(p, c, rng)
    assert (df["es_fraude"] == 0).all()
    assert (df["mecanismo"] == "legitimo").all()
    assert df["marca_tiempo"].between(0, c.n_dias).all()
    assert (df["monto"] > 0).all()
    ordenado = df.sort_values(["id_tarjeta", "marca_tiempo"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(df.reset_index(drop=True), ordenado)


def test_cada_tarjeta_tiene_historia_suficiente_para_ventanas():
    # sin al menos K transacciones la ventana queda casi toda enmascarada
    c = _pequena()
    rng = np.random.default_rng(c.semilla)
    df = generar_trafico_legitimo(generar_perfiles(c, rng), c, rng)
    conteos = df.groupby("id_tarjeta").size()
    assert conteos.min() >= 20


def test_monto_tipico_varia_entre_tarjetas():
    # el perfil por tarjeta es lo que hace que "Q3000" sea normal para unas y no para otras
    c = _pequena()
    rng = np.random.default_rng(c.semilla)
    df = generar_trafico_legitimo(generar_perfiles(c, rng), c, rng)
    medianas = df.groupby("id_tarjeta")["monto"].median()
    assert medianas.max() / medianas.min() > 3.0
