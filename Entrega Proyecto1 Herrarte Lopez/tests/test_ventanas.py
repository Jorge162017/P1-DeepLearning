import numpy as np
import pandas as pd
import pytest
from src.config import K, ConfigGenerador
from src.ventanas import (COLUMNAS_AGREGADAS, Dataset, asignar_particion,
                          construir_dataset)


def _marco_a_mano():
    """Una tarjeta con 4 transacciones de montos y tiempos conocidos."""
    return pd.DataFrame({
        "id_tx": [0, 1, 2, 3],
        "id_tarjeta": [7, 7, 7, 7],
        "marca_tiempo": [10.0, 10.5, 10.75, 11.0],
        "monto": [100.0, 200.0, 300.0, 900.0],
        "rubro": ["ropa", "ropa", "farmacia", "electronica"],
        "canal": ["chip", "chip", "chip", "ecommerce"],
        "ciudad": ["guatemala", "guatemala", "guatemala", "madrid"],
        "es_fraude": [0, 0, 0, 1],
        "mecanismo": ["legitimo", "legitimo", "legitimo", "F2"],
        "id_episodio": [-1, -1, -1, 0],
    })


def test_asignar_particion_excluye_el_embargo():
    c = ConfigGenerador()
    t = np.array([0.0, 119.9, 120.5, 121.9, 122.0, 149.9, 150.5, 152.0, 179.9])
    p = asignar_particion(t, c)
    assert list(p) == ["entrenamiento", "entrenamiento", "embargo", "embargo",
                       "validacion", "validacion", "embargo", "prueba", "prueba"]


def test_los_agregados_son_causales():
    """El agregado del ancla mira solo hacia atras, nunca a si mismo ni al futuro."""
    df = _marco_a_mano()
    d = construir_dataset(df, ConfigGenerador())
    fila = d.agregados[d.meta["id_tx"] == 3].iloc[0]
    # previas del ancla id_tx=3: montos 100, 200, 300
    assert fila["monto_medio_ventana"] == pytest.approx(200.0)
    assert fila["monto_max_ventana"] == pytest.approx(300.0)   # NO 900
    assert fila["rubros_distintos"] == 2                        # ropa, farmacia
    assert fila["ciudades_distintas"] == 1                      # solo guatemala
    assert fila["monto_rel_mediana"] == pytest.approx(900.0 / 200.0)


def test_la_primera_transaccion_no_tiene_historia():
    df = _marco_a_mano()
    d = construir_dataset(df, ConfigGenerador())
    fila = d.agregados[d.meta["id_tx"] == 0].iloc[0]
    assert fila["monto_medio_ventana"] == 0.0
    assert fila["rubros_distintos"] == 0
    assert bool(d.mascara[0, : K - 1].any()) is False   # historia vacia
    assert bool(d.mascara[0, K - 1]) is True            # el ancla siempre esta


def test_el_ancla_ocupa_la_ultima_posicion_de_la_secuencia():
    df = _marco_a_mano()
    d = construir_dataset(df, ConfigGenerador())
    i = int(np.where(d.meta["id_tx"].to_numpy() == 3)[0][0])
    assert d.seq_num[i, K - 1, 0] == pytest.approx(np.log1p(900.0), rel=1e-5)


def test_las_secuencias_no_mezclan_tarjetas():
    df = pd.concat([_marco_a_mano(),
                    _marco_a_mano().assign(id_tarjeta=8, id_tx=[4, 5, 6, 7])],
                   ignore_index=True).sort_values(["id_tarjeta", "marca_tiempo"])
    d = construir_dataset(df.reset_index(drop=True), ConfigGenerador())
    i = int(np.where(d.meta["id_tx"].to_numpy() == 4)[0][0])  # primera de la tarjeta 8
    assert bool(d.mascara[i, : K - 1].any()) is False


def test_columnas_y_formas():
    df = _marco_a_mano()
    d = construir_dataset(df, ConfigGenerador())
    assert list(d.agregados.columns) == COLUMNAS_AGREGADAS
    assert len(COLUMNAS_AGREGADAS) == 15
    n = len(df)
    assert d.seq_cat.shape == (n, K, 3)
    assert d.seq_num.shape == (n, K, 7)
    assert d.mascara.shape == (n, K)
    assert d.seq_num.dtype == np.float32


def test_sobre_datos_generados_no_hay_nan():
    from src.generador import generar
    c = ConfigGenerador(n_tarjetas=120, n_dias=180)
    d = construir_dataset(generar(c), c)
    assert not d.agregados.isna().any().any()
    assert np.isfinite(d.seq_num).all()
    assert set(d.meta["particion"].unique()) <= {
        "entrenamiento", "validacion", "prueba", "embargo"}
