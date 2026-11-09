"""El senuelo tiene que dejar ciegas a las variables agregadas.

Si esto falla, el generador esta mal calibrado y no tiene sentido seguir con los
modelos secuenciales.
"""
import pytest
from src.config import ConfigGenerador
from src.generador import generar
from src.modelos import verificar_senuelo
from src.ventanas import construir_dataset

UMBRAL_COBRO = 0.60            # la compuerta, en el ancla donde el diseno promete ceguera
TECHO_TODAS_LAS_ANCLAS = 0.70  # cuanta senal residual toleramos


@pytest.fixture(scope="module")
def datos():
    c = ConfigGenerador(n_tarjetas=6000, n_dias=180)
    return construir_dataset(generar(c), c)


def test_los_agregados_no_separan_f1_del_senuelo_en_el_cobro(datos):
    """La compuerta. En el cobro, F1 y el senuelo traen los mismos montos, los
    mismos huecos y los mismos rubros. Lo unico que cambia es el orden.
    """
    auc = verificar_senuelo(datos, solo_cobro=True)
    assert auc <= UMBRAL_COBRO, (
        f"ROC-AUC={auc:.3f} > {UMBRAL_COBRO} en el ancla del cobro: los agregados "
        "separan F1 del senuelo. Recalibrar el generador antes de entrenar B."
    )


def test_la_senal_residual_en_las_anclas_intermedias_esta_acotada(datos):
    """Sobre todas las anclas queda algo de senal, y sabemos de donde sale.

    Como F1 es una rampa, en sus anclas intermedias el prefijo siempre trae los
    montos mas chicos, y el del senuelo no. Le ponemos techo para que no crezca
    sin que nadie se de cuenta.
    """
    auc = verificar_senuelo(datos, solo_cobro=False)
    assert auc <= TECHO_TODAS_LAS_ANCLAS, f"senal residual demasiado alta: {auc:.3f}"
    # y debe ser estrictamente mayor que en el cobro: esa asimetria ES el hallazgo
    assert auc > verificar_senuelo(datos, solo_cobro=True)
