
# IA MultiCloud – Sistema de Monitoreo Vial

Proyecto universitario de IA Cloud que utiliza un sistema multiagente para analizar eventos de tránsito en Chile, consultar bases de conocimiento y registrar sus resultados en una base de datos.

## Tecnologías utilizadas

- **Azure AI Foundry:** acceso al modelo de inteligencia artificial.
- **Azure AI Search:** búsqueda de normativa chilena y criterios de riesgo.
- **Google ADK:** coordinación y ejecución de los agentes.
- **FastAPI:** API para registrar y consultar eventos.
- **SQLite:** almacenamiento local de eventos.
- **Pytest:** pruebas automáticas.
- **Python:** lenguaje principal.

## Arquitectura

El sistema utiliza cinco agentes:

1. `orquestador`: coordina el flujo de trabajo.
2. `agente_analisis`: organiza el análisis del evento.
3. `clasificador_riesgo`: identifica el tipo de evento y su nivel de riesgo.
4. `verificador_normativo`: consulta la normativa aplicable.
5. `agente_registro`: envía los resultados al backend.

El flujo general es:

Evento de tránsito → Orquestador → Análisis y clasificación → Verificación normativa → Registro en FastAPI → SQLite.

Los agentes utilizan Azure AI Foundry para procesar la información y Azure AI Search para consultar dos índices:

- `ks-normativa-vial-index`: normativa de tránsito chilena.
- `ks-riesgos-viales-index`: criterios de clasificación de riesgos.

## Instalación

Clonar el repositorio:

```powershell
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

Copiar los archivos de ejemplo:

- `backend/.env.example` → `backend/.env`
- `monitoreo_vial/.env.example` → `monitoreo_vial/.env`

Configurar las credenciales correspondientes a Azure AI Foundry y Azure AI Search.

En `monitoreo_vial/.env` se requieren las variables:

```env
AZURE_API_KEY=
AZURE_API_BASE=
AZURE_API_VERSION=2024-10-21

AZURE_SEARCH_ENDPOINT=
AZURE_SEARCH_KEY=
AZURE_SEARCH_INDEX_NORMATIVA=ks-normativa-vial-index
AZURE_SEARCH_INDEX_RIESGOS=ks-riesgos-viales-index

BACKEND_API_KEY=
```

En `backend/.env`:

```env
BACKEND_API_KEY=
```

La variable `BACKEND_API_KEY` debe tener el mismo valor en ambos archivos.

Las credenciales y los archivos `.env` no deben publicarse en GitHub.

## Ejecución

Abrir dos terminales en la carpeta principal del proyecto, con el entorno virtual activado.

### Terminal 1 – FastAPI

```powershell
python -m uvicorn backend.main:app --reload --port 8000
```

Documentación interactiva:

http://127.0.0.1:8000/docs

### Terminal 2 – Google ADK

```powershell
adk web --port 8001
```

Interfaz web:

http://127.0.0.1:8001

Seleccionar `monitoreo_vial` para interactuar con el sistema.

El backend debe permanecer ejecutándose para que los agentes puedan registrar eventos.

## API

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/eventos` | Registra un evento. Requiere `X-API-Key`. |
| GET | `/eventos` | Consulta los eventos almacenados. |

Se utilizan validaciones con Pydantic para comprobar los datos recibidos.

La API también maneja identificadores duplicados, errores de SQLite y solicitudes no autorizadas.

## Pruebas automáticas

Para ejecutar las pruebas:

```powershell
python -m pytest tests/test_backend.py -v
```

El sistema cuenta con siete pruebas automatizadas que comprueban:

- Errores de SQLite.
- Advertencias por operaciones lentas.
- Timeouts de comunicación.
- Protección mediante API Key.
- Identificadores duplicados.
- Validación de datos incorrectos.
- Manejo de errores HTTP desde los agentes.

**Última comprobación:** 7 pruebas aprobadas.

## Logs y monitoreo

### Backend

Los registros se almacenan en:

`backend/backend.log`

Incluyen operaciones exitosas, errores de SQLite y advertencias cuando una operación supera los 100 ms.

### Agentes

Los registros de ejecución se almacenan en:

`monitoreo_vial/agentes.log`

Se implementaron callbacks para registrar:

- Inicio de cada agente.
- Tiempo individual de ejecución.
- Finalización de cada agente.
- Advertencias por ejecuciones superiores a 30 segundos.
- Errores del modelo y de herramientas.

El monitoreo permite observar el comportamiento de los cinco agentes e identificar posibles problemas durante su ejecución.

## Evaluación con Golden Set

Se utilizó un Golden Set de 303 casos de tránsito con respuestas esperadas conocidas.

Los resultados generados por los agentes se compararon con las respuestas esperadas para evaluar la clasificación del tipo de evento y del nivel de riesgo.

Se realizaron tres corridas de evaluación.

Los archivos de resultados se encuentran en:

- `evaluacion/corrida_1.jsonl`
- `evaluacion/corrida_2.jsonl`
- `evaluacion/corrida_3.jsonl`
- `evaluacion/resumen.json`

La evaluación permite identificar aciertos, errores de clasificación y diferencias entre el riesgo esperado y el obtenido.

## Seguridad

El sistema incorpora:

- Autenticación mediante `X-API-Key` para registrar eventos.
- Validación de datos con Pydantic.
- Manejo de errores HTTP y de base de datos.
- Exclusión de credenciales, logs y bases de datos locales mediante `.gitignore`.

## Estado del proyecto

Prototipo funcional integrado con Google ADK, Azure AI Foundry, Azure AI Search, FastAPI y SQLite.

Se completaron la integración de los cinco agentes, el registro persistente de eventos, el monitoreo de tiempos, las pruebas automatizadas del backend y la evaluación con Golden Set.

Como posibles mejoras futuras se consideran la precisión de clasificación, una cobertura más amplia de errores y el análisis de costos y escalabilidad en entornos de producción.
