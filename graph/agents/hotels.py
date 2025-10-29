"""Asistente de hoteles"""
from langchain_core.prompts import ChatPromptTemplate
from tools import hotel_safe_tools, hotel_sensitive_tools
from graph.state import CompleteOrEscalate, State
from graph.nodes import _process_messages_for_llm
from .primary import llm


hotel_booking_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """Eres un asistente especializado en reservar hoteles. 
Ayuda al usuario a encontrar y reservar un hotel. 
Si la tarea se completa, usa CompleteOrEscalate."""
    ),
    ("placeholder", "{messages}"),
])

hotel_runnable = hotel_booking_prompt | llm.bind_tools(
    hotel_safe_tools + hotel_sensitive_tools + [CompleteOrEscalate]
)


def hotel_assistant_node(state: State):
    temp_state = state.copy()
    temp_state["messages"] = _process_messages_for_llm(state)
    result = hotel_runnable.invoke(temp_state)
    return {"messages": [result]}