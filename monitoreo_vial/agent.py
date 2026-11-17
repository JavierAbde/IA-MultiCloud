import requests
import os
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool

from .buscador import buscar_criterios_riesgo, buscar_normativa

# Modelo de Azure Foundry que usan todos los agentes
MODELO = LiteLlm(model="azure/gpt-6.1-terra")


# =====================================================
# NIVEL 3 - Especialistas
# =====================================================

clasificador_riesgo = Agent(
    name="clasificador_riesgo",
    model=MODELO,
    description="Clasifica el tipo de evento vial y su nivel de riesgo.",
    instruction="""Recibes la descripcion de un evento de transito.

Antes de clasificar, usa la herramienta buscar_criterios_riesgo con palabras
clave del evento (por ejemplo "casco motocicleta riesgo" o "evidencia
insuficiente") y aplica los criterios que encuentres en el manual.

Clasificalo en UNO de estos tipos:
- CASCO: motociclista o pasajero de moto sin casco.
- CELULAR: conductor usando el telefono mientras conduce.
- VEREDA: bicicleta, scooter o monopatin (electrico o no) circulando por la vereda o acera.
- VELOCIDAD: vehiculo que supera el limite de velocidad.
- NINGUNO: no hay conducta de riesgo.
- INDETERMINADO: la informacion no alcanza para decidir.

Importante sobre la evidencia:
- La descripcion que recibes es lo que la camara o el radar YA observaron:
  trata esos hechos como confirmados, no pidas mas pruebas.
- Usa INDETERMINADO solo si la descripcion dice que algo no se ve, no se
  distingue o falta un dato (imagen borrosa, camara tapada, radar sin lectura).
- Usa el manual para decidir el tipo, el nivel de riesgo y las tolerancias
  (por ejemplo, un margen de velocidad), no para dudar de los hechos descritos.

Asigna un nivel de riesgo: bajo, medio o alto.
Si el tipo es INDETERMINADO, no asignes riesgo e indica que requiere revision humana.
Si la busqueda falla o no trae resultados, clasifica igual con tu criterio
e indicalo en la justificacion.
Responde solo con: tipo, riesgo y una justificacion breve.""",
    tools=[buscar_criterios_riesgo],
)

verificador_normativo = Agent(
    name="verificador_normativo",
    model=MODELO,
    description="Indica que norma de transito chilena se infringe segun el tipo de evento.",
    instruction="""Recibes un tipo de evento vial (CASCO, CELULAR, VEREDA o VELOCIDAD)
y su descripcion.

1. Usa la herramienta buscar_normativa con palabras clave del evento
   (por ejemplo "casco motocicleta", "telefono conduccion manos libres",
   "ciclos vereda acera", "limite de velocidad").
2. Indica que norma se infringe y en que consiste, usando SOLO lo que
   aparece en los resultados de la busqueda. Menciona el articulo si aparece.
3. Si la busqueda no trae la norma, responde "norma no encontrada en la base"
   y NO inventes articulos ni excepciones.
Responde de forma breve.""",
    tools=[buscar_normativa],
)


# =====================================================
# NIVEL 2 - Coordinadores
# =====================================================

agente_analisis = Agent(
    name="agente_analisis",
    model=MODELO,
    description="Analiza un evento vial: clasifica su riesgo y verifica la normativa.",
    instruction="""Recibes un evento vial. Sigue siempre estos pasos:
1. Usa la herramienta clasificador_riesgo con la descripcion completa del evento.
2. Si el tipo NO es NINGUNO ni INDETERMINADO, usa verificador_normativo con ese tipo.
3. Devuelve un resumen con: tipo, riesgo, infraccion y justificacion.""",
    tools=[
        AgentTool(agent=clasificador_riesgo),
        AgentTool(agent=verificador_normativo),
    ],
)


def guardar_evento(id_evento: str, tipo: str, riesgo: str, infraccion: str) -> dict:
    """Guarda un evento vial ya analizado en la base de datos.

    Args:
        id_evento: identificador del evento, por ejemplo EV-001.
        tipo: CASCO, CELULAR, VEREDA, VELOCIDAD o INDETERMINADO.
        riesgo: bajo, medio, alto o sin_riesgo (si es INDETERMINADO).
        infraccion: norma infringida o "revision humana".
    """
    try:
        respuesta = requests.post(
            "http://127.0.0.1:8000/eventos",
            json={
                "id": id_evento,
                "tipo": tipo,
                "riesgo": riesgo,
                "infraccion": infraccion
            },
            headers={
                "X-API-Key": os.environ["BACKEND_API_KEY"]
            },
            timeout=10
        )

        respuesta.raise_for_status()
        return respuesta.json()
    except requests.Timeout:
        return {
            "estado": "error",
            "registrado": False,
            "id": id_evento,
            "detalle": "Timeout: la API no respondió dentro de 10 segundos"
        }
    except requests.HTTPError as error:
        codigo = error.response.status_code if error.response is not None else 500

        return {
            "estado": "error",
            "registrado": False,
            "id": id_evento,
            "codigo_http": codigo,
            "detalle": {
                401: "No autorizado: API Key inválida",
                409: "El evento ya existe en la base de datos",
                422: "Los datos del evento no son válidos",
                500: "Error interno del backend"
            }.get(codigo, f"Error HTTP {codigo}")
        }
    except requests.RequestException as error:
        return {
            "estado": "error",
            "registrado": False,
            "id": id_evento,
            "detalle": str(error)
        }



agente_registro = Agent(
    name="agente_registro",
    model=MODELO,
    description="Guarda en la base de datos los eventos viales ya analizados.",
    instruction="""Recibes el resultado del analisis de un evento vial.
Usa la herramienta guardar_evento con el id, tipo, riesgo e infraccion.
Si no hay id, usa "SIN-ID". Luego confirma si el evento se guardo.""",
    tools=[guardar_evento],
)


# =====================================================
# NIVEL 1 - Orquestador (agente principal)
# =====================================================

root_agent = Agent(
    name="orquestador",
    model=MODELO,
    description="Agente principal del sistema de monitoreo vial.",
    instruction="""Eres el orquestador de un sistema de monitoreo vial en Chile.
Cuando el usuario envie un evento (en texto o en JSON):
1. Envialo a agente_analisis.
2. Si el tipo es distinto de NINGUNO, envia el resultado a agente_registro
   (los INDETERMINADO tambien se registran, para revision humana).
3. Responde al usuario SOLO con un JSON con este formato:
   {"id": "...", "evento": "<TIPO>", "riesgo": "<RIESGO>", "infraccion": "...", "registrado": true}

Reglas del JSON:
- "evento" debe ser EXACTAMENTE uno de estos codigos, en mayusculas y sin
  descripcion: CASCO, CELULAR, VEREDA, VELOCIDAD, NINGUNO, INDETERMINADO.
- "riesgo" debe ser exactamente: bajo, medio, alto o sin_riesgo
  (usa sin_riesgo cuando el evento es NINGUNO o INDETERMINADO).
- "registrado" debe ser true solo si agente_registro confirmo que se guardo.
- La descripcion del hecho va en "infraccion", nunca en "evento".
- Si el analisis concluye que NO hay infraccion (por ejemplo, porque aplica
  una excepcion legal), el evento es NINGUNO, aunque el tipo sugerido fuera otro.

Si el mensaje no es un evento vial, explica brevemente que informacion necesitas.""",
    tools=[
        AgentTool(agent=agente_analisis),
        AgentTool(agent=agente_registro),
    ],
)