
from fastapi import FastAPI
from pydantic import BaseModel
from .database import inicializar_db
import sqlite3
from .database import DB_PATH
import os
import secrets
from pathlib import Path
from dotenv import load_dotenv
from fastapi import Header, HTTPException, Depends

load_dotenv(Path(__file__).resolve().parent / ".env")

API_KEY = os.getenv("BACKEND_API_KEY")

if not API_KEY:
    raise RuntimeError("Falta configurar BACKEND_API_KEY en backend/.env")


def verificar_api_key(x_api_key: str = Header(default="")):
    if not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(
            status_code=401,
            detail="API Key inválida o ausente"
        )

app = FastAPI(title="API Monitoreo Vial")


class Evento(BaseModel):
    id: str
    tipo: str
    riesgo: str
    infraccion: str


inicializar_db()


@app.get("/")
def inicio():
    return {
        "mensaje": "API de Monitoreo Vial funcionando",
        "estado": "ok"
    }


@app.post("/eventos", dependencies=[Depends(verificar_api_key)])
def registrar_evento(evento: Evento):
    with sqlite3.connect(DB_PATH) as conexion:
        conexion.execute(
            """
            INSERT OR REPLACE INTO eventos
            (id, tipo, riesgo, infraccion)
            VALUES (?, ?, ?, ?)
            """,
            (
                evento.id,
                evento.tipo,
                evento.riesgo,
                evento.infraccion
            )
        )
        conexion.commit()

    return {
        "estado": "ok",
        "registrado": True,
        "id": evento.id
    }

@app.get("/eventos")
def listar_eventos():
    with sqlite3.connect(DB_PATH) as conexion:
        conexion.row_factory = sqlite3.Row
        eventos = conexion.execute(
            "SELECT * FROM eventos"
        ).fetchall()

    return {
        "total": len(eventos),
        "eventos": [dict(evento) for evento in eventos]
    }
