# IA MultiCloud – Sistema de Monitoreo Vial

Proyecto universitario de IA Cloud que utiliza un sistema multiagente para analizar eventos de tránsito en Chile y registrar sus resultados en una base de datos.

## Tecnologías utilizadas

- **Azure AI Foundry:** acceso al modelo de inteligencia artificial.
- **Google ADK:** coordinación de los agentes.
- **FastAPI:** API para registrar y consultar eventos.
- **SQLite:** almacenamiento local de eventos.
- **Pytest:** pruebas automáticas.
- **Python:** lenguaje principal.

## Arquitectura

El sistema contiene cinco agentes distribuidos en tres niveles:

1. `orquestador`: coordina las operaciones.
2. `agente_analisis`: organiza la clasificación y verificación de infracciones.
3. `agente_registro`: comunica los resultados al backend.
4. `clasificador_riesgo`: identifica el tipo de evento y su riesgo.
5. `verificador_normativo`: analiza la normativa de tránsito chilena.

Los resultados se envían mediante HTTP a FastAPI y se almacenan en SQLite.

## Instalación

Clonar el repositorio:

```bash
git clone https://github.com/JavierAbde/IA-MultiCloud.git
cd IA-MultiCloud
```

Crear y activar un entorno virtual en Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instalar las dependencias:

```powershell
python -m pip install -r requirements.txt
```

## Configuración

Copiar `backend/.env.example` como `backend/.env`.

Copiar `monitoreo_vial/.env.example` como `monitoreo_vial/.env`.

Configurar las credenciales de Azure y utilizar la misma `BACKEND_API_KEY` en ambos archivos.

No subir los archivos `.env` al repositorio.

## Ejecución

Abrir dos terminales en la carpeta principal del proyecto, con el entorno virtual activado.

**Terminal 1 – FastAPI**

```powershell
python -m uvicorn backend.main:app --reload --port 8000
```

Documentación interactiva:

http://127.0.0.1:8000/docs

**Terminal 2 – Google ADK**

```powershell
adk web --port 8001
```

Interfaz de agentes:

http://127.0.0.1:8001

Seleccionar `monitoreo_vial` para probar el sistema.

## API

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/eventos` | Registra un evento. Requiere `X-API-Key`. |
| GET | `/eventos` | Consulta los eventos almacenados. |

El sistema utiliza validaciones con Pydantic y rechaza los identificadores duplicados.

## Pruebas automáticas

Ejecutar:

```powershell
python -m pytest tests/test_backend.py -v
```

Se incluyen pruebas para:

- Errores de SQLite.
- Advertencias por operaciones lentas.
- Timeouts de comunicación entre el agente y la API.

## Logs y monitoreo

Los registros del backend se almacenan en `backend/backend.log`.

Se registran operaciones exitosas, errores de SQLite y advertencias cuando una operación supera los 100 ms.

Los archivos de logs, las bases de datos locales y las credenciales están excluidos de Git mediante `.gitignore`.

## Estado del proyecto

Prototipo funcional con agentes conectados a una API protegida y almacenamiento persistente en SQLite.

Pendiente: evaluación con Golden Set, monitoreo completo de los agentes, análisis de costos y escalabilidad, y documentación final de arquitectura.