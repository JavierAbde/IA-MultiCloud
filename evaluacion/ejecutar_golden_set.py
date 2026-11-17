"""
Ejecuta el Golden Set contra el orquestador (root_agent) y calcula el accuracy.

Uso (desde la carpeta raiz del repositorio, con el entorno virtual activo):

    # Prueba rapida con 10 casos y 1 corrida (para ver que todo funciona)
    python -m evaluacion.ejecutar_golden_set --limite 10 --corridas 1

    # Evaluacion completa: todos los casos, 3 corridas
    python -m evaluacion.ejecutar_golden_set --corridas 3

    # Volver a calificar las corridas ya guardadas, SIN llamar a Azure
    python -m evaluacion.ejecutar_golden_set --recalcular

Requisitos:
  - monitoreo_vial/.env con las credenciales de Azure y BACKEND_API_KEY.
  - El backend FastAPI encendido (uvicorn) si se quiere que los eventos se
    registren. Si esta apagado, la clasificacion igual se evalua.

Resultados (carpeta evaluacion/resultados/):
  - corrida_N.jsonl   -> respuesta del sistema para cada caso de la corrida N
  - resumen.json      -> accuracy de cada corrida
  - evaluacion.log    -> log con errores, timeouts y casos lentos
"""

import argparse
import asyncio
import json
import logging
import os
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = Path(__file__).resolve().parent
RESULTADOS = CARPETA / "resultados"
RESULTADOS.mkdir(exist_ok=True)

# Las credenciales se cargan ANTES de importar el agente
load_dotenv(RAIZ / "monitoreo_vial" / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(RESULTADOS / "evaluacion.log", encoding="utf-8"),
              logging.StreamHandler()],
)
log = logging.getLogger("golden_set")

# LiteLLM escribe una linea por cada llamada al modelo: se silencia para que
# la terminal muestre solo el avance de la evaluacion (los errores si salen).
os.environ.setdefault("LITELLM_LOG", "ERROR")
for nombre in ("LiteLLM", "LiteLLM Router", "LiteLLM Proxy", "litellm", "httpx",
               "google_adk", "google.adk"):
    logging.getLogger(nombre).setLevel(logging.WARNING)

# Marca unica de esta ejecucion (dia+hora+minuto), por ejemplo 162130
EJECUCION = datetime.now().strftime("%d%H%M")

TIPOS = {"CASCO", "CELULAR", "VEREDA", "VELOCIDAD", "NINGUNO", "INDETERMINADO"}


# ---------------------------------------------------------------------
# Lectura de la respuesta del orquestador
# ---------------------------------------------------------------------
def buscar_tipo(texto: str):
    """Devuelve el primer codigo de tipo (CASCO, CELULAR, ...) que aparezca.

    Solo cuenta si esta escrito EN MAYUSCULAS: asi "motociclista con casco"
    no se confunde con el codigo CASCO.
    """
    encontrado = re.search(r"\b(" + "|".join(TIPOS) + r")\b", texto or "")
    return encontrado.group(1) if encontrado else None


def extraer_respuesta(texto: str) -> dict:
    """Saca el tipo y el riesgo de la respuesta del orquestador.

    El orquestador deberia responder un JSON como:
      {"id": "...", "evento": "CASCO", "riesgo": "alto", ...}
    pero a veces pone una descripcion en "evento" (ej. "Motociclista sin
    casco"), lo envuelve en ```json``` o agrega texto. Por eso:
      1. Si "tipo" o "evento" es exactamente un codigo valido, se usa.
      2. Si no, se busca un codigo valido dentro de esos campos.
      3. Si no, se busca un codigo valido en todo el texto.
    """
    if not texto:
        return {"tipo": None, "riesgo": None}

    riesgo, campos = None, ""
    bloque = re.search(r"\{.*\}", texto, re.DOTALL)
    if bloque:
        try:
            datos = json.loads(bloque.group(0))
            for clave in ("tipo", "evento"):
                valor = str(datos.get(clave) or "").upper().strip()
                if valor in TIPOS:
                    return {"tipo": valor,
                            "riesgo": str(datos.get("riesgo") or "").lower().strip() or None}
            campos = f"{datos.get('tipo', '')} {datos.get('evento', '')}"
            riesgo = str(datos.get("riesgo") or "").lower().strip() or None
        except json.JSONDecodeError:
            pass

    return {"tipo": buscar_tipo(campos) or buscar_tipo(texto), "riesgo": riesgo}


def normalizar_riesgo(riesgo):
    """NINGUNO/INDETERMINADO pueden venir como 'sin_riesgo', 'ninguno', 'N/A'..."""
    if riesgo in ("bajo", "medio", "alto"):
        return riesgo
    return "sin_riesgo"


# ---------------------------------------------------------------------
# Ejecucion de un caso
# ---------------------------------------------------------------------
async def ejecutar_caso(runner, caso, corrida, timeout, semaforo):
    from google.genai import types

    # Prefijo por ejecucion y corrida para que el backend no rechace IDs
    # repetidos de ejecuciones anteriores (409 = evento duplicado)
    id_evento = f"{EJECUCION}-R{corrida}-{caso['id']}"
    mensaje = f"Evento {id_evento}. {caso['entrada']}"

    async with semaforo:
        inicio = time.perf_counter()
        texto_final, error = "", None
        try:
            sesion = await runner.session_service.create_session(
                app_name=runner.app_name, user_id="golden_set")
            contenido = types.Content(role="user", parts=[types.Part(text=mensaje)])

            async def correr():
                nonlocal texto_final
                async for evento in runner.run_async(
                        user_id="golden_set", session_id=sesion.id,
                        new_message=contenido):
                    if evento.is_final_response() and evento.content and evento.content.parts:
                        texto_final = "".join(p.text or "" for p in evento.content.parts)

            await asyncio.wait_for(correr(), timeout=timeout)
        except asyncio.TimeoutError:
            error = f"timeout: el sistema no respondio en {timeout} s"
            log.error(f"[corrida {corrida}] {caso['id']} {error}")
        except Exception as e:  # el modelo fallo, credenciales, etc.
            error = f"{type(e).__name__}: {e}"
            log.error(f"[corrida {corrida}] {caso['id']} error: {error}")

        segundos = time.perf_counter() - inicio
        if segundos > timeout * 0.5 and not error:
            log.warning(f"[corrida {corrida}] {caso['id']} lento: {segundos:.1f} s")

    return calificar({
        **caso,
        "corrida": corrida,
        "segundos": round(segundos, 2),
        "error": error,
        "respuesta_cruda": texto_final,
    })


def calificar(resultado):
    """Compara la respuesta del sistema con la respuesta esperada."""
    obtenido = extraer_respuesta(resultado["respuesta_cruda"])
    acierto_tipo = obtenido["tipo"] == resultado["tipo_esperado"]
    resultado.update({
        "tipo_obtenido": obtenido["tipo"],
        "riesgo_obtenido": obtenido["riesgo"],
        "acierto_tipo": acierto_tipo,
        "acierto_riesgo": acierto_tipo and
            normalizar_riesgo(obtenido["riesgo"]) == resultado["riesgo_esperado"],
    })
    return resultado


# ---------------------------------------------------------------------
# Ejecucion de una corrida completa
# ---------------------------------------------------------------------
async def ejecutar_corrida(casos, corrida, timeout, paralelos):
    from google.adk.runners import InMemoryRunner
    from monitoreo_vial.agent import root_agent

    runner = InMemoryRunner(agent=root_agent, app_name="monitoreo_vial")
    semaforo = asyncio.Semaphore(paralelos)
    log.info(f"=== Corrida {corrida}: {len(casos)} casos ===")

    tareas = [ejecutar_caso(runner, c, corrida, timeout, semaforo) for c in casos]
    resultados = []
    for i, tarea in enumerate(asyncio.as_completed(tareas), start=1):
        resultados.append(await tarea)
        if i % 25 == 0:
            log.info(f"  corrida {corrida}: {i}/{len(casos)} casos listos")

    resultados.sort(key=lambda r: r["id"])
    with (RESULTADOS / f"corrida_{corrida}.jsonl").open("w", encoding="utf-8") as f:
        for r in resultados:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return resultados


def resumir(resultados):
    n = len(resultados)
    por_tipo = {}
    for tipo in sorted({r["tipo_esperado"] for r in resultados}):
        grupo = [r for r in resultados if r["tipo_esperado"] == tipo]
        por_tipo[tipo] = round(100 * sum(r["acierto_tipo"] for r in grupo) / len(grupo), 1)
    por_categoria = {}
    for cat in sorted({r["categoria"] for r in resultados}):
        grupo = [r for r in resultados if r["categoria"] == cat]
        por_categoria[cat] = round(100 * sum(r["acierto_tipo"] for r in grupo) / len(grupo), 1)
    return {
        "casos": n,
        "accuracy_tipo": round(100 * sum(r["acierto_tipo"] for r in resultados) / n, 2),
        "accuracy_tipo_y_riesgo": round(100 * sum(r["acierto_riesgo"] for r in resultados) / n, 2),
        "errores_o_timeouts": sum(1 for r in resultados if r["error"]),
        "tiempo_promedio_s": round(sum(r["segundos"] for r in resultados) / n, 2),
        "accuracy_por_tipo": por_tipo,
        "accuracy_por_categoria": por_categoria,
        "confusiones": dict(Counter(
            f"{r['tipo_esperado']} -> {r['tipo_obtenido']}"
            for r in resultados if not r["acierto_tipo"]).most_common(10)),
    }


def main():
    parser = argparse.ArgumentParser(description="Evalua el Golden Set")
    parser.add_argument("--corridas", type=int, default=3)
    parser.add_argument("--limite", type=int, default=None,
                        help="usar solo los primeros N casos (para pruebas)")
    parser.add_argument("--timeout", type=int, default=120,
                        help="segundos maximos por caso")
    parser.add_argument("--paralelos", type=int, default=4,
                        help="casos ejecutados al mismo tiempo")
    parser.add_argument("--recalcular", action="store_true",
                        help="no llama a Azure: vuelve a calificar las corridas ya guardadas")
    args = parser.parse_args()

    if args.recalcular:
        recalcular()
        return

    with (CARPETA / "golden_set.jsonl").open(encoding="utf-8") as f:
        casos = [json.loads(linea) for linea in f if linea.strip()]
    if args.limite:
        casos = casos[: args.limite]

    resumen = {"fecha": datetime.now().isoformat(timespec="seconds"), "corridas": []}
    for corrida in range(1, args.corridas + 1):
        resultados = asyncio.run(
            ejecutar_corrida(casos, corrida, args.timeout, args.paralelos))
        datos = resumir(resultados)
        resumen["corridas"].append({"corrida": corrida, **datos})
        log.info(f"Corrida {corrida}: accuracy tipo = {datos['accuracy_tipo']} % | "
                 f"tipo+riesgo = {datos['accuracy_tipo_y_riesgo']} % | "
                 f"errores = {datos['errores_o_timeouts']}")

    guardar_y_mostrar(resumen)


def recalcular():
    """Vuelve a calificar corrida_N.jsonl sin gastar llamadas a Azure."""
    archivos = sorted(RESULTADOS.glob("corrida_*.jsonl"))
    if not archivos:
        print("No hay corridas guardadas en evaluacion/resultados/")
        return
    resumen = {"fecha": datetime.now().isoformat(timespec="seconds"),
               "recalculado": True, "corridas": []}
    for archivo in archivos:
        with archivo.open(encoding="utf-8") as f:
            resultados = [calificar(json.loads(l)) for l in f if l.strip()]
        with archivo.open("w", encoding="utf-8") as f:
            for r in resultados:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        corrida = resultados[0]["corrida"]
        resumen["corridas"].append({"corrida": corrida, **resumir(resultados)})
    guardar_y_mostrar(resumen)


def guardar_y_mostrar(resumen):
    with (RESULTADOS / "resumen.json").open("w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    print("\n===== RESUMEN =====")
    for c in resumen["corridas"]:
        print(f"Corrida {c['corrida']}: {c['accuracy_tipo']} % (tipo) | "
              f"{c['accuracy_tipo_y_riesgo']} % (tipo + riesgo)")
    distintos = len({c["accuracy_tipo"] for c in resumen["corridas"]})
    print(f"Porcentajes distintos de accuracy: {distintos}")


if __name__ == "__main__":
    main()
