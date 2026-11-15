
from fastapi import FastAPI
from pydantic import BaseModel
from .database import inicializar_db
import sqlite3
from .database import DB_PATH

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


@app.post("/eventos")
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
