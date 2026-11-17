
import logging
import time
from pathlib import Path

from google.adk.agents.callback_context import CallbackContext

LOG_PATH = Path(__file__).resolve().parent / "agentes.log"

logger = logging.getLogger("monitoreo_agentes")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    ))
    logger.addHandler(handler)

TIEMPO_LIMITE = 30


def antes_agente(callback_context: CallbackContext):
    nombre = callback_context.agent_name
    clave = f"temp:inicio_{nombre}"

    callback_context.state[clave] = time.perf_counter()
    logger.info(f"{nombre} | Inicio")
    return None


def despues_agente(callback_context: CallbackContext):
    nombre = callback_context.agent_name
    clave = f"temp:inicio_{nombre}"

    inicio = callback_context.state.get(clave)

    if inicio is None:
        logger.warning(f"{nombre} | Inicio no encontrado")
        return None

    duracion = time.perf_counter() - inicio
    logger.info(f"{nombre} | Finalizado en {duracion:.2f} s")

    if duracion > TIEMPO_LIMITE:
        logger.warning(
            f"{nombre} | Superó los {TIEMPO_LIMITE} s: "
            f"{duracion:.2f} s"
        )

    return None
def error_modelo(callback_context, llm_request, error):
    nombre = callback_context.agent_name
    logger.error(
        "%s | Error del modelo | %s: %s",
        nombre,
        type(error).__name__,
        str(error)[:300]
    )
    return None


def error_herramienta(tool, args, tool_context, error):
    logger.error(
        "%s | Error de herramienta %s | %s: %s",
        tool_context.agent_name,
        tool.name,
        type(error).__name__,
        str(error)[:300]
    )
    return None