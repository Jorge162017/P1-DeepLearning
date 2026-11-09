import numpy as np
import pandas as pd
from src.config import ConfigGenerador
from src.generador import generar


def _pequena():
    return ConfigGenerador(n_tarjetas=1200, n_dias=180)


def test_generar_es_reproducible():
    c = _pequena()
    pd.testing.assert_frame_equal(generar(c), generar(c))


def test_tasa_de_fraude_cercana_al_objetivo():
    c = _pequena()
    df = generar(c)
    tasa = df["es_fraude"].mean()
    assert 0.003 < tasa < 0.011, f"tasa fuera de rango: {tasa}"


def test_el_senuelo_es_legitimo():
    df = generar(_pequena())
    senuelo = df[df["mecanismo"] == "senuelo_f1"]
    assert len(senuelo) > 0
    assert (senuelo["es_fraude"] == 0).all()


def test_ambos_terminan_en_la_compra_grande():
    """Si el senuelo empezara con la grande, los agregados del cobro cambiarian
    y el senuelo no serviria."""
    df = generar(_pequena())
    for mecanismo in ["F1", "senuelo_f1"]:
        for _, g in df[df["mecanismo"] == mecanismo].groupby(["id_tarjeta", "id_episodio"]):
            montos = g.sort_values("marca_tiempo")["monto"].to_numpy()
            assert int(np.argmax(montos)) == len(montos) - 1


def test_f1_tiene_rampa_ascendente_y_el_senuelo_no():
    """Lo unico que cambia entre fraude y senuelo es el orden de las micro-compras."""
    df = generar(_pequena())
    ascendentes = {}
    for mecanismo in ["F1", "senuelo_f1"]:
        conteo = 0
        episodios = list(df[df["mecanismo"] == mecanismo].groupby(["id_tarjeta", "id_episodio"]))
        for _, g in episodios:
            micros = g.sort_values("marca_tiempo")["monto"].to_numpy()[:-1]  # sin la grande
            conteo += int(np.all(np.diff(micros) >= 0))
        ascendentes[mecanismo] = conteo / len(episodios)
    assert ascendentes["F1"] == 1.0, "F1 debe ser siempre una rampa ascendente"
    assert ascendentes["senuelo_f1"] == 0.0, "el senuelo nunca debe imitar la rampa"


def test_f1_y_senuelo_comparten_la_distribucion_de_montos():
    """Si los montos difieren, los agregados podrian separarlos y el senuelo no sirve.

    Comparamos el monto medio por episodio con Kolmogorov-Smirnov. Comparar medias
    globales seria ruidoso porque F1 y el senuelo no tienen el mismo numero de
    episodios. La prueba que manda sobre el senuelo es el go/no-go, no esta.
    """
    from scipy.stats import ks_2samp
    df = generar(_pequena())
    por_episodio = (df[df["mecanismo"].isin(["F1", "senuelo_f1"])]
                    .groupby(["mecanismo", "id_tarjeta", "id_episodio"])["monto"]
                    .mean().reset_index())
    f1 = por_episodio.loc[por_episodio["mecanismo"] == "F1", "monto"]
    se = por_episodio.loc[por_episodio["mecanismo"] == "senuelo_f1", "monto"]
    assert len(f1) > 20 and len(se) > 20
    assert ks_2samp(f1, se).pvalue > 0.05, "los montos por episodio son distinguibles"


def test_f1_y_senuelo_tienen_episodios_del_mismo_tamano():
    """El conteo por ventana es uno de los agregados, asi que tiene que coincidir."""
    from scipy.stats import ks_2samp
    df = generar(_pequena())
    tam = (df[df["mecanismo"].isin(["F1", "senuelo_f1"])]
           .groupby(["mecanismo", "id_tarjeta", "id_episodio"]).size().reset_index(name="n"))
    f1 = tam.loc[tam["mecanismo"] == "F1", "n"]
    se = tam.loc[tam["mecanismo"] == "senuelo_f1", "n"]
    assert ks_2samp(f1, se).pvalue > 0.05


def test_todo_el_episodio_f1_esta_etiquetado_como_fraude():
    """Si solo etiquetaramos la compra grande, el modelo aprenderia a esperar al cobro."""
    df = generar(_pequena())
    assert (df.loc[df["mecanismo"] == "F1", "es_fraude"] == 1).all()
    tam = df[df["mecanismo"] == "F1"].groupby(["id_tarjeta", "id_episodio"]).size()
    assert tam.min() >= 4  # 3+ micro-compras y la grande


def test_f4_es_medible_pero_no_mayoritario_en_prueba():
    """F4 tiene que poder medirse aparte sin comerse el bloque de prueba."""
    c = _pequena()
    df = generar(c)
    prueba = df[df["marca_tiempo"] >= c.dia_inicio_prueba]
    fraude = prueba[prueba["es_fraude"] == 1]
    prop_f4 = (fraude["mecanismo"] == "F4").mean()
    assert 0.15 < prop_f4 < 0.45, f"F4 es el {prop_f4:.0%} del fraude en prueba"
    # el fixture es pequeno; la configuracion real produce ~190 transacciones F4
    assert (fraude["mecanismo"] == "F4").sum() >= 15, "muy pocas F4 para medir"


def test_f4_aparece_solo_en_el_bloque_de_prueba():
    c = _pequena()
    df = generar(c)
    f4 = df[df["mecanismo"] == "F4"]
    assert len(f4) > 0
    assert f4["marca_tiempo"].min() >= c.dia_inicio_prueba
    assert (f4["es_fraude"] == 1).all()


def test_los_demas_mecanismos_no_aparecen_solo_en_prueba():
    c = _pequena()
    df = generar(c)
    for m in ["F1", "F2", "F3"]:
        sub = df[df["mecanismo"] == m]
        assert (sub["marca_tiempo"] < c.dia_fin_entrenamiento).any(), f"{m} falta en entrenamiento"


def test_f2_es_geograficamente_imposible():
    df = generar(_pequena())
    f2 = df[df["mecanismo"] == "F2"]
    assert len(f2) > 0
    assert (f2["es_fraude"] == 1).all()
    for fila in f2.itertuples():
        # existe una transaccion previa reciente en otra ciudad (otra inyeccion
        # puede haberse colado en medio, asi que no se exige la inmediata anterior)
        cercanas = df[(df["id_tarjeta"] == fila.id_tarjeta)
                      & (df["marca_tiempo"] < fila.marca_tiempo)
                      & (df["marca_tiempo"] > fila.marca_tiempo - 0.25)]  # 6 horas
        assert (cercanas["ciudad"] != fila.ciudad).any()


def test_el_marco_sigue_ordenado_por_tarjeta_y_tiempo():
    df = generar(_pequena())
    ordenado = df.sort_values(["id_tarjeta", "marca_tiempo"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(df, ordenado)
    assert df["id_tx"].is_unique
