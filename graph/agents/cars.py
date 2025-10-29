"""Asistente de alquiler de coches"""
from langchain_core.prompts import ChatPromptTemplate
from tools import car_rental_safe_tools, car_rental_sensitive_tools
from graph.state import CompleteOrEscalate, State
from graph.nodes import _process_messages_for_llm
from .primary import llm


car_rental_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """Eres un asistente especializado en alquilar coches 🚗.

Tu trabajo es ayudar al usuario a:
- Buscar coches disponibles según ubicación, precio y tipo
- Reservar coches
- Cancelar reservas de coches
- Consultar políticas de alquiler

Siempre confirma los detalles importantes con el usuario antes de hacer reservas.
Si la tarea se completa exitosamente, usa CompleteOrEscalate."""
    ),
    ("placeholder", "{messages}"),
])

car_rental_runnable = car_rental_prompt | llm.bind_tools(
    car_rental_safe_tools + car_rental_sensitive_tools + [CompleteOrEscalate]
)


def car_rental_assistant_node(state: State):
    """Nodo del asistente de alquiler de coches"""
    temp_state = state.copy()
    temp_state["messages"] = _process_messages_for_llm(state)
    result = car_rental_runnable.invoke(temp_state)
    return {"messages": [result]}