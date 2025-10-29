"""Asistente de vuelos"""
from langchain_core.prompts import ChatPromptTemplate
from tools import flight_safe_tools, flight_sensitive_tools
from graph.state import CompleteOrEscalate, State
from graph.nodes import _process_messages_for_llm
from .primary import llm  # Reutilizar el mismo LLM


flight_booking_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """Eres un asistente experto en la gestión de reservas de vuelos. 
Tus tareas incluyen buscar vuelos, actualizar billetes existentes y registrar nuevos vuelos.

Para registrar un nuevo vuelo, DEBES obtener primero del usuario:
- Nombre completo
- Dirección de correo electrónico

Utiliza las herramientas disponibles para completar la tarea. 
Si la tarea se completa, usa la herramienta CompleteOrEscalate."""
    ),
    ("placeholder", "{messages}"),
])

flight_runnable = flight_booking_prompt | llm.bind_tools(
    flight_safe_tools + flight_sensitive_tools + [CompleteOrEscalate]
)


def flight_assistant_node(state: State):
    """Nodo del asistente de vuelos"""
    temp_state = state.copy()
    temp_state["messages"] = _process_messages_for_llm(state)
    result = flight_runnable.invoke(temp_state)
    return {"messages": [result]}