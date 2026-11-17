"""
Herramientas de busqueda en las bases de conocimiento (Azure AI Search).

Son las mismas dos bases creadas en la actividad Knowledge Base:
  - ks-normativa-vial-index -> normativa de transito chilena
  - ks-riesgos-viales-index -> criterios para clasificar eventos y su riesgo

Las credenciales se leen del archivo monitoreo_vial/.env:
  AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_KEY, AZURE_SEARCH_INDEX_NORMATIVA,
  AZURE_SEARCH_INDEX_RIESGOS
"""

import logging
import os
import time

import requests

logger = logging.getLogger("monitoreo_vial.buscador")

API_VERSION = "2024-07-01"
TIMEOUT_SEGUNDOS = 10
MAX_RESULTADOS = 3
MAX_CARACTERES = 1500  # por fragmento, para no gastar tokens de mas


def _limpiar_documento(doc: dict) -> dict:
    """Deja solo los campos de texto utiles de un resultado.

    Se descartan los vectores (listas de numeros) y los metadatos internos
    de Azure (los que empiezan con @search, salvo el puntaje).
    """
    limpio = {}
    for campo, valor in doc.items():
        if campo == "@search.score":
            limpio["puntaje"] = round(valor, 2)
        elif campo.startswith("@"):
            continue
        elif isinstance(valor, str) and valor.strip():
            limpio[campo] = valor[:MAX_CARACTERES]
        elif isinstance(valor, (int, float)) and not isinstance(valor, bool):
            limpio[campo] = valor
    return limpio


def _buscar(indice_env: str, consulta: str) -> dict:
    endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT", "").rstrip("/")
    clave = os.environ.get("AZURE_SEARCH_KEY", "")
    indice = os.environ.get(indice_env, "")
    if not (endpoint and clave and indice):
        logger.error("Faltan variables de Azure AI Search en monitoreo_vial/.env")
        return {"estado": "error",
                "detalle": "Busqueda no configurada (faltan datos en .env)"}

    inicio = time.perf_counter()
    try:
        respuesta = requests.post(
            f"{endpoint}/indexes/{indice}/docs/search",
            params={"api-version": API_VERSION},
            headers={"api-key": clave, "Content-Type": "application/json"},
            json={"search": consulta, "top": MAX_RESULTADOS},
            timeout=TIMEOUT_SEGUNDOS,
        )
        respuesta.raise_for_status()
    except requests.Timeout:
        logger.error(f"Busqueda en {indice} supero {TIMEOUT_SEGUNDOS} s: '{consulta}'")
        return {"estado": "error", "detalle": "La busqueda tardo demasiado"}
    except requests.HTTPError as error:
        codigo = error.response.status_code if error.response is not None else 0
        logger.error(f"Busqueda en {indice} fallo con HTTP {codigo}")
        return {"estado": "error", "detalle": f"Error HTTP {codigo} en la busqueda"}
    except requests.RequestException as error:
        logger.error(f"Busqueda en {indice} fallo: {error}")
        return {"estado": "error", "detalle": str(error)}

    duracion = time.perf_counter() - inicio
    documentos = [_limpiar_documento(d) for d in respuesta.json().get("value", [])]
    logger.info(f"Busqueda en {indice}: {len(documentos)} resultados en {duracion:.2f} s")

    if not documentos:
        return {"estado": "sin_resultados",
                "detalle": "No se encontro informacion sobre esto en la base."}
    return {"estado": "ok", "resultados": documentos}


def buscar_normativa(consulta: str) -> dict:
    """Busca en la normativa de transito chilena (Ley 18.290 y relacionadas).

    Args:
        consulta: palabras clave en espanol, por ejemplo
            "uso de casco motocicleta" o "celular conduciendo manos libres".

    Returns:
        Los fragmentos de la normativa mas relacionados con la consulta.
    """
    return _buscar("AZURE_SEARCH_INDEX_NORMATIVA", consulta)


def buscar_criterios_riesgo(consulta: str) -> dict:
    """Busca en el manual de criterios para clasificar eventos viales y su riesgo.

    Args:
        consulta: palabras clave en espanol, por ejemplo
            "evidencia insuficiente" o "bicicleta en la vereda nivel de riesgo".

    Returns:
        Los fragmentos del manual mas relacionados con la consulta.
    """
    return _buscar("AZURE_SEARCH_INDEX_RIESGOS", consulta)
