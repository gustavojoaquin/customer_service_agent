"""Asistente de excursiones y tours"""
from langchain_core.prompts import ChatPromptTemplate
from tools import excursion_safe_tools, excursion_sensitive_tools
from graph.state import CompleteOrEscalate, State
from graph.nodes import _process_messages_for_llm
from .primary import llm


excursion_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """Eres un asistente especializado en recomendar y reservar excursiones 🌍.

Tu trabajo es ayudar al usuario a:
- Buscar recomendaciones de viajes y tours según ubicación
- Reservar excursiones y actividades
- Cancelar reservas de excursiones
- Proporcionar información sobre tours disponibles

Sé entusiasta y ayuda al usuario a descubrir experiencias increíbles.
Si la tarea se completa exitosamente, usa CompleteOrEscalate."""
    ),
    ("placeholder", "{messages}"),
])

excursion_runnable = excursion_prompt | llm.bind_tools(
    excursion_safe_tools + excursion_sensitive_tools + [CompleteOrEscalate]
)


def excursion_assistant_node(state: State):
    """Nodo del asistente de excursiones"""
    temp_state = state.copy()
    temp_state["messages"] = _process_messages_for_llm(state)
    result = excursion_runnable.invoke(temp_state)
    return {"messages": [result]}