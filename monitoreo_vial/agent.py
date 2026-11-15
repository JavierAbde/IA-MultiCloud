from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool

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
Clasificalo en UNO de estos tipos:
- CASCO: motociclista o pasajero de moto sin casco.
- CELULAR: conductor usando el telefono mientras conduce.
- VEREDA: bicicleta circulando por la vereda.
- VELOCIDAD: vehiculo que supera el limite de velocidad.
- NINGUNO: no hay conducta de riesgo.
- INDETERMINADO: la informacion no alcanza para decidir.

Asigna un nivel de riesgo: bajo, medio o alto.
Si el tipo es INDETERMINADO, no asignes riesgo e indica que requiere revision humana.
Responde solo con: tipo, riesgo y una justificacion breve.""",
)

verificador_normativo = Agent(
    name="verificador_normativo",
    model=MODELO,
    description="Indica que norma de transito chilena se infringe segun el tipo de evento.",
    instruction="""Recibes un tipo de evento vial (CASCO, CELULAR, VEREDA o VELOCIDAD).
Indica que norma de la Ley de Transito chilena (Ley 18.290) se infringe y en que consiste.
Si no estas seguro del numero de articulo, dilo: no inventes articulos.
Responde de forma breve.""",
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
    # TEMPORAL: esta funcion solo imprime en la terminal.
    # Cuando el Integrante 2 tenga lista la API, aqui se reemplaza
    # por la llamada real que guarda en la base de datos.
    
    import requests

    try:
        respuesta = requests.post(
            "http://127.0.0.1:8000/eventos",
            json={
                "id": id_evento,
                "tipo": tipo,
                "riesgo": riesgo,
                "infraccion": infraccion
            },
            timeout=10
        )

        respuesta.raise_for_status()
        return respuesta.json()

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
   {"id": "...", "evento": "...", "riesgo": "...", "infraccion": "...", "registrado": true}

Si el mensaje no es un evento vial, explica brevemente que informacion necesitas.""",
    tools=[
        AgentTool(agent=agente_analisis),
        AgentTool(agent=agente_registro),
    ],
)