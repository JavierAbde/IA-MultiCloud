
import sqlite3
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.main import API_KEY

client = TestClient(app)


def test_error_base_datos():
    evento = {
        "id": "EV-ERROR",
        "tipo": "CASCO",
        "riesgo": "alto",
        "infraccion": "Prueba de error de SQLite"
    }

    with patch(
        "backend.main.sqlite3.connect",
        side_effect=sqlite3.OperationalError("Error simulado")
    ):
        respuesta = client.post(
            "/eventos",
            json=evento,
            headers={"X-API-Key": API_KEY}
        )

    assert respuesta.status_code == 500
    assert respuesta.json()["detail"] == "No se pudo guardar el evento"


def test_advertencia_operacion_lenta(caplog):
    evento = {
        "id": "EV-LENTO",
        "tipo": "VELOCIDAD",
        "riesgo": "alto",
        "infraccion": "Prueba de lentitud"
    }

    with patch("backend.main.time") as reloj_simulado:
        reloj_simulado.perf_counter.side_effect = [100.0, 100.2]

        respuesta = client.post(
            "/eventos",
            json=evento,
            headers={"X-API-Key": API_KEY}
        )

    assert respuesta.status_code == 200
    assert "superó el umbral de 100 ms" in caplog.text

import requests
from monitoreo_vial.agent import guardar_evento


def test_timeout_api():
    with patch(
        "monitoreo_vial.agent.requests.post",
        side_effect=requests.Timeout("Tiempo agotado")
    ):
        resultado = guardar_evento(
            id_evento="EV-TIMEOUT",
            tipo="CASCO",
            riesgo="alto",
            infraccion="Motociclista sin casco"
        )

    assert resultado["estado"] == "error"
    assert resultado["registrado"] is False
    assert "Timeout" in resultado["detalle"]
