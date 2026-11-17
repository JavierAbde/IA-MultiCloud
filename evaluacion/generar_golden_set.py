"""
Genera el Golden Set del sistema de monitoreo vial.

Cada caso tiene:
  - id: identificador unico (GS-001, GS-002, ...)
  - entrada: el texto del evento que recibira el orquestador
  - tipo_esperado: CASCO, CELULAR, VEREDA, VELOCIDAD, NINGUNO o INDETERMINADO
  - riesgo_esperado: bajo, medio, alto o sin_riesgo
  - categoria: facil, dificil o indeterminado (para analizar los errores)

Uso:
    python evaluacion/generar_golden_set.py

Crea el archivo evaluacion/golden_set.jsonl. La semilla es fija, asi que
siempre se generan los mismos casos (importante para comparar corridas).
"""

import json
import random
from pathlib import Path

random.seed(22)  # Grupo 22: semilla fija = mismos casos siempre

SALIDA = Path(__file__).resolve().parent / "golden_set.jsonl"

# ---------------------------------------------------------------------
# Piezas para armar descripciones variadas
# ---------------------------------------------------------------------
LUGARES = [
    "Av. Providencia con Los Leones", "Alameda frente al cerro Santa Lucia",
    "Av. Vicuna Mackenna altura Nuble", "Gran Avenida paradero 12",
    "Av. Matta con San Diego", "Av. Las Condes con Manquehue",
    "Av. Pajaritos en Maipu", "calle Irarrazaval con Macul",
    "Av. Grecia en Penalolen", "Av. Kennedy frente al Parque Arauco",
    "Av. Independencia con Dorsal", "costanera de Valparaiso",
    "Av. Libertad en Vina del Mar", "Av. Alemania en Temuco",
    "calle O'Higgins en Concepcion", "Av. Recoleta con Dominica",
]
HORAS = ["07:45", "08:10", "09:30", "12:15", "13:40", "17:55", "18:20",
         "19:05", "21:30", "23:10"]
CAMARAS = ["CAM-01", "CAM-02", "CAM-03", "CAM-07", "CAM-12", "CAM-15"]
AUTOS = ["un automovil sedan", "una camioneta", "un taxi", "un furgon",
         "un auto blanco", "un SUV gris", "un colectivo", "un auto rojo"]


def contexto():
    """Devuelve un texto de lugar/hora/camara elegido al azar."""
    return (f"Camara {random.choice(CAMARAS)}, {random.choice(LUGARES)}, "
            f"{random.choice(HORAS)} hrs.")


# ---------------------------------------------------------------------
# Generadores por tipo. Cada uno devuelve (descripcion, tipo, riesgo, categoria)
# ---------------------------------------------------------------------
def casos_casco():
    plantillas = [
        ("Se observa un motociclista circulando sin casco a velocidad normal.", "alto"),
        ("Moto en movimiento: el conductor lleva el casco colgando del brazo, con la cabeza descubierta.", "alto"),
        ("El pasajero de una motocicleta va sin casco; el conductor si lo usa.", "alto"),
        ("Repartidor en moto avanza entre los autos sin casco puesto.", "alto"),
        ("Motociclista detenido en luz roja con el casco sobre el estanque, cabeza descubierta.", "medio"),
        ("Scooter a motor circulando por la calzada, conductor sin casco y con jockey.", "alto"),
        ("Conductor de moto sin casco y pasajero tambien sin casco, ambos en movimiento.", "alto"),
        ("Moto avanzando lento en un taco; el conductor no usa casco.", "medio"),
    ]
    dificiles = [
        # El casco esta desabrochado pero puesto: sigue siendo uso de casco,
        # pero un juez/modelo puede dudar. Lo marcamos CASCO riesgo medio
        # porque el casco mal puesto no protege (criterio del grupo).
        ("Motociclista con el casco puesto pero sin abrochar la correa, en movimiento.", "CASCO", "medio"),
        ("Moto con dos ocupantes: el pasajero lleva un gorro de lana en vez de casco.", "CASCO", "alto"),
    ]
    casos = []
    for _ in range(42):
        texto, riesgo = random.choice(plantillas)
        casos.append((texto, "CASCO", riesgo, "facil"))
    for _ in range(6):
        texto, tipo, riesgo = random.choice(dificiles)
        casos.append((texto, tipo, riesgo, "dificil"))
    return casos


def casos_celular():
    plantillas = [
        ("El conductor de {auto} va escribiendo en su celular mientras avanza.", "alto"),
        ("Conductor de {auto} mira la pantalla del telefono que sostiene con la mano mientras conduce.", "alto"),
        ("Se ve al conductor de {auto} hablando por celular con el telefono pegado a la oreja, en movimiento.", "medio"),
        ("Conductor de {auto} grabando un video con el celular mientras circula.", "alto"),
        ("El conductor de {auto} sostiene el celular con una mano y el volante con la otra.", "alto"),
        ("Conductor de {auto} detenido en luz roja revisando mensajes en el telefono en la mano.", "bajo"),
        ("Chofer de {auto} hablando por telefono sostenido entre el hombro y la oreja al doblar.", "medio"),
    ]
    casos = []
    for _ in range(45):
        texto, riesgo = random.choice(plantillas)
        casos.append((texto.format(auto=random.choice(AUTOS)), "CELULAR", riesgo, "facil"))
    return casos


def casos_vereda():
    plantillas = [
        ("Una bicicleta circula por la vereda esquivando peatones.", "alto"),
        ("Ciclista adulto avanza rapido por la acera junto a una parada de buses con gente.", "alto"),
        ("Bicicleta circulando por la vereda, sin peatones alrededor.", "bajo"),
        ("Ciclista va por la vereda a velocidad moderada, hay algunos peatones a lo lejos.", "medio"),
        ("Repartidor en bicicleta sube a la vereda para evitar el taco y sigue por ella.", "medio"),
        ("Un scooter electrico (monopatin) circula por la acera entre peatones.", "alto"),
        ("Ciclista circula por la vereda frente a la entrada de un colegio a la hora de salida.", "alto"),
    ]
    casos = []
    for _ in range(45):
        texto, riesgo = random.choice(plantillas)
        casos.append((texto, "VEREDA", riesgo, "facil"))
    return casos


def riesgo_velocidad(medida, limite, escolar):
    """Regla del grupo para el riesgo por exceso de velocidad."""
    exceso = medida - limite
    if escolar or exceso > 25:
        return "alto"
    if exceso > 10:
        return "medio"
    return "bajo"


def casos_velocidad():
    casos = []
    zonas = [(30, True, "zona escolar"), (50, False, "zona urbana"),
             (60, False, "avenida"), (80, False, "autopista urbana"),
             (100, False, "autopista")]
    for _ in range(45):
        limite, escolar, nombre = random.choice(zonas)
        medida = limite + random.randint(5, 45)
        auto = random.choice(AUTOS)
        texto = (f"Radar registra {auto} a {medida} km/h en {nombre} "
                 f"con limite de {limite} km/h.")
        casos.append((texto, "VELOCIDAD",
                      riesgo_velocidad(medida, limite, escolar), "facil"))
    return casos


def casos_ninguno():
    plantillas = [
        "Motociclista circulando con casco abrochado por su pista.",
        "Pasajero y conductor de moto ambos con casco, detenidos en semaforo.",
        "Ciclista circulando por la ciclovia segregada.",
        "Ciclista avanza por la calzada, pegado a la derecha.",
        "Conductor de {auto} con ambas manos en el volante, sin objetos en las manos.",
        "Radar registra {auto} a {v} km/h en zona urbana con limite de 50 km/h.",
        "Peaton cruza por el paso de cebra con luz verde.",
        "Ciclista camina por la vereda empujando su bicicleta.",
        "{auto} estacionado con el motor apagado; el conductor usa el celular.",
        "Bus del transporte publico circula por su via exclusiva respetando el limite.",
    ]
    casos = []
    for _ in range(54):
        texto = random.choice(plantillas).format(
            auto=random.choice(AUTOS).capitalize(), v=random.randint(35, 50))
        casos.append((texto, "NINGUNO", "sin_riesgo", "facil"))
    return casos


def casos_dificiles_ninguno():
    """Casos trampa: parecen infraccion, pero no lo son."""
    plantillas = [
        # La que fallo en la actividad anterior: el telefono lo usa la pasajera
        "En {auto} en movimiento, la pasajera del asiento delantero usa el celular; el conductor mira al frente con ambas manos en el volante.",
        "Conductor de {auto} usa el GPS en un soporte fijo al parabrisas, sin tocar el telefono.",
        "Conductor de {auto} habla por manos libres (bluetooth), con las dos manos en el volante.",
        "Nino de unos 6 anos anda en bicicleta por la vereda acompanado de un adulto que camina a su lado.",
        "Radar registra {auto} a 50 km/h en zona urbana con limite de 50 km/h.",
        "Radar registra una ambulancia con balizas y sirena encendidas a 85 km/h en zona de 60 km/h.",
        "Motociclista se saca el casco despues de estacionar la moto y apagar el motor.",
        "Ciclista con la bicicleta en la mano cruza la vereda para entrar a un edificio.",
    ]
    casos = []
    for _ in range(30):
        texto = random.choice(plantillas).format(auto=random.choice(AUTOS))
        casos.append((texto, "NINGUNO", "sin_riesgo", "dificil"))
    return casos


def casos_indeterminado():
    plantillas = [
        "Imagen muy borrosa por lluvia: se distingue una moto pero no si el conductor lleva casco.",
        "La camara esta parcialmente tapada; se ve un auto pero no al conductor.",
        "Toma nocturna con contraluz: no se distingue que tiene el conductor en la mano.",
        "Radar con falla: no entrego lectura de velocidad para el vehiculo detectado.",
        "Se ve un bulto en la vereda que podria ser una bicicleta o un carro de supermercado.",
        "El vidrio polarizado impide ver si el conductor usa el telefono.",
        "Solo se ve la parte trasera de la moto; el casco del conductor no es visible.",
        "Imagen pixelada por baja conexion: hay un ciclista, pero no se sabe si esta en la vereda o en la calzada.",
    ]
    casos = []
    for _ in range(36):
        casos.append((random.choice(plantillas), "INDETERMINADO", "sin_riesgo", "indeterminado"))
    return casos


# ---------------------------------------------------------------------
# Armar y guardar
# ---------------------------------------------------------------------
def main():
    todos = (casos_casco() + casos_celular() + casos_vereda()
             + casos_velocidad() + casos_ninguno()
             + casos_dificiles_ninguno() + casos_indeterminado())
    random.shuffle(todos)

    with SALIDA.open("w", encoding="utf-8") as f:
        for i, (texto, tipo, riesgo, categoria) in enumerate(todos, start=1):
            caso = {
                "id": f"GS-{i:03d}",
                "entrada": f"{contexto()} {texto}",
                "tipo_esperado": tipo,
                "riesgo_esperado": riesgo,
                "categoria": categoria,
            }
            f.write(json.dumps(caso, ensure_ascii=False) + "\n")

    # Resumen en pantalla
    from collections import Counter
    print(f"Golden Set generado: {len(todos)} casos -> {SALIDA}")
    for tipo, n in sorted(Counter(t for _, t, _, _ in todos).items()):
        print(f"  {tipo:<14} {n}")


if __name__ == "__main__":
    main()
