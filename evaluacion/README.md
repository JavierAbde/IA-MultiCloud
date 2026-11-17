# Golden Set – Evaluación automática

## Archivos
| Archivo | Para qué sirve |
|---|---|
| `generar_golden_set.py` | Crea `golden_set.jsonl` con 303 casos (semilla fija: siempre los mismos). |
| `golden_set.jsonl` | Los casos: entrada, tipo esperado, riesgo esperado y categoría. |
| `ejecutar_golden_set.py` | Pasa cada caso por el orquestador, compara y calcula el accuracy. |
| `resultados/` | Se crea al ejecutar: `corrida_N.jsonl`, `resumen.json`, `evaluacion.log`. |

## Distribución de casos
| Tipo | Casos |
|---|---|
| CASCO | 48 |
| CELULAR | 45 |
| VEREDA | 45 |
| VELOCIDAD | 45 |
| NINGUNO | 84 (30 son casos trampa) |
| INDETERMINADO | 36 |

Categorías: `facil` (231), `dificil` (36, casos trampa) e `indeterminado` (36).
Los casos trampa parecen una infracción, pero no lo son. Por ejemplo: la pasajera usa el celular, el conductor usa manos libres, una ambulancia en emergencia o un auto justo en el límite de velocidad.

## Cómo ejecutar (desde la raíz del repositorio)
```powershell
# 1. Terminal 1: encender el backend
uvicorn backend.main:app --port 8000

# 2. Terminal 2: prueba rápida (10 casos, 1 corrida)
python -m evaluacion.ejecutar_golden_set --limite 10 --corridas 1

# 3. Evaluación completa (303 casos x 3 corridas)
python -m evaluacion.ejecutar_golden_set --corridas 3
```
Opciones: `--timeout 120` (segundos máximos por caso) y `--paralelos 4` (casos al mismo tiempo; bájenlo a 1 o 2 si Azure responde con error 429).

## Cómo se mide
- **Accuracy principal (tipo):** porcentaje de casos en que el `evento` de la respuesta coincide con `tipo_esperado`.
- **Accuracy tipo + riesgo:** también exige que el riesgo coincida. Es un dato secundario.
- Un caso que no responde dentro del tiempo límite cuenta como error y queda en `evaluacion.log`.

## Regla de riesgo usada en el Golden Set
- **VELOCIDAD:** hasta 10 km/h sobre el límite = bajo; de 11 a 25 = medio; más de 25 o zona escolar = alto.
- **CASCO:** en movimiento = alto; detenido o casco sin abrochar = medio.
- **CELULAR:** manipulándolo en movimiento = alto; hablando con el teléfono en la oreja = medio; detenido en luz roja = bajo.
- **VEREDA:** con peatones cerca o frente a un colegio = alto; con algunos peatones = medio; vereda vacía = bajo.
- **NINGUNO / INDETERMINADO:** sin_riesgo.
