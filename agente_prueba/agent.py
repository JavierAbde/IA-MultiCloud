from google.adk.agents.llm_agent import Agent

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

root_agent = Agent(
    name="agente_prueba",
    model=LiteLlm(model="azure/gpt-6.1-terra"),
    instruction="Eres un asistente de monitoreo vial. Responde en español.",
)