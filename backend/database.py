
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "eventos.db"


def inicializar_db():
    with sqlite3.connect(DB_PATH) as conexion:
        conexion.execute("""
            CREATE TABLE IF NOT EXISTS eventos (
                id TEXT PRIMARY KEY,
                tipo TEXT NOT NULL,
                riesgo TEXT NOT NULL,
                infraccion TEXT NOT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conexion.commit()
