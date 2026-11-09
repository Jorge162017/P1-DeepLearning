from src.config import K, COSTO_FN, COSTO_FP, CARTERA_TARJETAS, ConfigGenerador


def test_constantes_globales():
    assert K == 20
    assert COSTO_FN == 4200.0
    assert COSTO_FP == 180.0
    assert CARTERA_TARJETAS == 1_400_000


def test_particion_sin_solape_y_con_embargo():
    c = ConfigGenerador()
    assert c.dia_fin_entrenamiento < c.dia_inicio_validacion
    assert c.dia_fin_validacion < c.dia_inicio_prueba
    # embargo de exactamente 2 dias entre bloques
    assert c.dia_inicio_validacion - c.dia_fin_entrenamiento == 3
    assert c.dia_inicio_prueba - c.dia_fin_validacion == 3
    assert c.dia_fin_prueba < c.n_dias


def test_config_es_inmutable_y_reproducible():
    import dataclasses
    c = ConfigGenerador()
    assert dataclasses.is_dataclass(c)
    with __import__("pytest").raises(dataclasses.FrozenInstanceError):
        c.semilla = 7


def test_proporciones_de_mecanismos_suman_uno():
    c = ConfigGenerador()
    assert abs(sum(c.prop_mecanismos.values()) - 1.0) < 1e-9
    assert "F4" not in c.prop_mecanismos  # F4 se retiene, no entra en el reparto
