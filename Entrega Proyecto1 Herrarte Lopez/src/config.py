"""Constantes globales y configuracion del generador."""
from dataclasses import dataclass, field

K = 20                      # transacciones por ventana: 19 de historia + 1 ancla
COSTO_FN = 4200.0           # quetzales por fraude no detectado
COSTO_FP = 180.0            # quetzales por bloquear una transaccion legitima
CARTERA_TARJETAS = 1_400_000

RUBROS = [
    "supermercado", "restaurante", "combustible", "farmacia", "ropa",
    "electronica", "viajes", "entretenimiento", "servicios", "ferreteria",
]
CANALES = ["chip", "contactless", "ecommerce", "atm"]
CIUDADES = [
    "guatemala", "quetzaltenango", "escuintla", "coban", "huehuetenango",
    "peten", "miami", "madrid", "ciudad_de_mexico", "bogota",
]


@dataclass(frozen=True)
class ConfigGenerador:
    semilla: int = 42
    n_tarjetas: int = 6000
    n_dias: int = 180

    tasa_fraude_objetivo: float = 0.006
    prop_mecanismos: dict = field(
        default_factory=lambda: {"F1": 0.40, "F2": 0.25, "F3": 0.35}
    )
    prop_senuelo_f1: float = 0.03      # sobre secuencias legitimas
    # F4 solo va en prueba, y como proporcion en vez de conteo fijo. Con conteo
    # fijo terminaba siendo la mayoria del fraude de ese bloque.
    prop_f4_en_prueba: float = 0.30

    dia_fin_entrenamiento: int = 119
    dia_inicio_validacion: int = 122   # embargo: 120, 121
    dia_fin_validacion: int = 149
    dia_inicio_prueba: int = 152       # embargo: 150, 151
    dia_fin_prueba: int = 179
