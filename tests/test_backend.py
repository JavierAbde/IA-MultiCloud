
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


def test_advertencia_operacion_lenta(caplog, tmp_path):
    from backend.database import inicializar_db

    db_temporal = tmp_path / "eventos_test.db"

    with patch("backend.database.DB_PATH", db_temporal):
        inicializar_db()

    evento = {
        "id": "EV-LENTO",
        "tipo": "VELOCIDAD",
        "riesgo": "alto",
        "infraccion": "Prueba de lentitud"
    }

    with patch("backend.main.DB_PATH", db_temporal):
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
def test_registro_sin_api_key():
    evento = {
        "id": "EV-SEGURIDAD",
        "tipo": "CASCO",
        "riesgo": "alto",
        "infraccion": "Prueba de acceso sin autorización"
    }

    respuesta = client.post(
        "/eventos",
        json=evento
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "API Key inválida o ausente"
def test_evento_duplicado(tmp_path):
    from backend.database import inicializar_db

    db_temporal = tmp_path / "duplicados.db"

    with patch("backend.database.DB_PATH", db_temporal):
        inicializar_db()

    evento = {
        "id": "EV-DUPLICADO",
        "tipo": "CASCO",
        "riesgo": "alto",
        "infraccion": "Motociclista sin casco"
    }

    with patch("backend.main.DB_PATH", db_temporal):
        primera = client.post(
            "/eventos",
            json=evento,
            headers={"X-API-Key": API_KEY}
        )

        segunda = client.post(
            "/eventos",
            json=evento,
            headers={"X-API-Key": API_KEY}
        )

    assert primera.status_code == 200
    assert segunda.status_code == 409
    assert segunda.json()["detail"] == "El evento EV-DUPLICADO ya existe"
def test_datos_invalidos():
    evento = {
        "id": "EV-INVALIDO",
        "tipo": "PIZZA",
        "riesgo": "gigante",
        "infraccion": "Prueba de validación"
    }

    respuesta = client.post(
        "/eventos",
        json=evento,
        headers={"X-API-Key": API_KEY}
    )

    assert respuesta.status_code == 422

    errores = respuesta.json()["detail"]
    assert len(errores) >= 2