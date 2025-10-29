"""Nodos auxiliares para el grafo"""
import json
from langchain_core.messages import AnyMessage, ToolMessage
from .state import State


def _process_messages_for_llm(state: State) -> list[AnyMessage]:
    """Procesa mensajes del estado para el LLM, convirtiendo contenido no-string"""
    processed_messages = []
    for msg in state["messages"]:
        if isinstance(msg, ToolMessage) and not isinstance(msg.content, str):
            try:
                content_str = json.dumps(msg.content)
                processed_messages.append(
                    ToolMessage(content=content_str, tool_call_id=msg.tool_call_id)
                )
            except TypeError:
                processed_messages.append(
                    ToolMessage(content=str(msg.content), tool_call_id=msg.tool_call_id)
                )
        else:
            processed_messages.append(msg)
    return processed_messages


def create_entry_node(assistant_name: str, new_dialog_state: str) -> callable:
    """Crea un nodo de entrada para un asistente específico"""
    def entry_node(state: State) -> dict:
        tool_call_id = state["messages"][-1].tool_calls[0]["id"]
        return {
            "messages": [
                ToolMessage(
                    content=f"Entrando al asistente de {assistant_name}.",
                    tool_call_id=tool_call_id,
                )
            ],
            "dialog_state": new_dialog_state,
        }
    return entry_node


def leave_skill_node(state: State) -> dict:
    """Nodo para regresar al asistente principal"""
    tool_call_id = state["messages"][-1].tool_calls[0]["id"]
    return {
        "dialog_state": "pop",
        "messages": [
            ToolMessage(
                content="Regresando al asistente principal.", 
                tool_call_id=tool_call_id
            )
        ],
    }