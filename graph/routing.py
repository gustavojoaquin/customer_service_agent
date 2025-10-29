"""Funciones de routing para el grafo"""
from langgraph.graph import END
from langgraph.prebuilt import tools_condition

from graph.state import (
    State,
    ToFlightBookingAssistant,
    ToHotelBookingAssistant,
    ToCarRentalAssistant,
    ToExcursionAssistant,
    CompleteOrEscalate
)


def route_primary_assistant(state: State):
    """Routing desde el asistente principal"""
    route = tools_condition(state)
    if route == END:
        return END
    
    tool_call = state["messages"][-1].tool_calls[0]
    
    if tool_call["name"] == ToFlightBookingAssistant.__name__:
        return "enter_flight_assistant"
    if tool_call["name"] == ToHotelBookingAssistant.__name__:
        return "enter_hotel_assistant"
    if tool_call["name"] == ToCarRentalAssistant.__name__:
        return "enter_car_rental_assistant"
    if tool_call["name"] == ToExcursionAssistant.__name__:
        return "enter_excursion_assistant"
    
    return "primary_tools_node"


def create_skill_router(safe_tools: list) -> callable:
    """Crea un router para un asistente especializado"""
    def router(state: State):
        route = tools_condition(state)
        if route == END:
            return END
        
        tool_call = state["messages"][-1].tool_calls[0]
        
        if tool_call["name"] == CompleteOrEscalate.__name__:
            return "leave_skill"
        
        safe_tool_names = {t.name for t in safe_tools}
        if tool_call["name"] in safe_tool_names:
            return "safe_tools"
        
        return "sensitive_tools"
    
    return router


def route_to_workflow(state: State):
    """Routing inicial basado en dialog_state"""
    return (
        state.get("dialog_state", [])[-1]
        if state.get("dialog_state")
        else "primary_assistant"
    )