import os
from datetime import datetime
from typing import Annotated, Literal

from langchain_openai import ChatOpenAI
from langchain_core.messages import AnyMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from tools import (
    primary_assistant_tools,
    flight_safe_tools,
    flight_sensitive_tools,
    hotel_safe_tools,
    hotel_sensitive_tools,
    car_rental_safe_tools,
    car_rental_sensitive_tools,
    excursion_safe_tools,
    excursion_sensitive_tools,
    fetch_user_flight_information
)


def update_dialog_stack(left: list[str], right: str | None) -> list[str]:
    if right is None:
        return left
    if right == "pop":
        return left[:-1] if left else []
    return left + [right]


class State(TypedDict):
    messages: Annotated[list[AnyMessage], lambda x, y: x + y]
    user_info: str
    passenger_id: str
    dialog_state: Annotated[
        list[
            Literal[
                "primary_assistant",
                "flight_assistant",
                "hotel_assistant",
                "car_rental_assistant",
                "excursion_assistant",
            ]
        ],
        update_dialog_stack,
    ]


class CompleteOrEscalate(BaseModel):
    """Marca la tarea actual como completada o escala el control al asistente principal."""

    reason: str


class ToFlightBookingAssistant(BaseModel):
    """Transfiere el trabajo a un asistente especializado en vuelos."""

    request: str = Field(
        description="Preguntas de seguimiento para aclarar la solicitud de vuelo."
    )


class ToHotelBookingAssistant(BaseModel):
    """Transfiere el trabajo a un asistente especializado en hoteles."""

    request: str = Field(description="Solicitud del usuario sobre la reserva de hotel.")


class ToCarRentalAssistant(BaseModel):
    """Transfiere el trabajo a un asistente especializado en alquiler de coches."""

    request: str = Field(
        description="Solicitud del usuario sobre el alquiler de un coche."
    )


class ToExcursionAssistant(BaseModel):
    """Transfiere el trabajo a un asistente especializado en excursiones."""

    request: str = Field(
        description="Solicitud del usuario sobre recomendaciones de viaje o excursiones."
    )


llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0,
)

primary_assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Eres un asistente de soporte al cliente. Tu rol es responder preguntas generales y delegar tareas de reserva (vuelos, hoteles, coches, excursiones) al asistente apropiado. Información del vuelo del usuario: <Flights>{user_info}</Flights>. Hora actual: {time}.",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.now)

assistant_runnable = primary_assistant_prompt | llm.bind_tools(
    primary_assistant_tools
    + [
        ToFlightBookingAssistant,
        ToHotelBookingAssistant,
        ToCarRentalAssistant,
        ToExcursionAssistant,
    ]
)


def primary_assistant_node(state: State):
    return {"messages": [assistant_runnable.invoke(state)]}


def create_entry_node(assistant_name: str, new_dialog_state: str) -> callable:
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
    tool_call_id = state["messages"][-1].tool_calls[0]["id"]
    return {
        "dialog_state": "pop",
        "messages": [
            ToolMessage(
                content="Regresando al asistente principal.", tool_call_id=tool_call_id
            )
        ],
    }


def route_primary_assistant(state: State):
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


def route_to_workflow(state: State):
    return (
        state.get("dialog_state", [])[-1]
        if state.get("dialog_state")
        else "primary_assistant"
    )


def create_graph():
    """Create and configure the main graph with all agents"""
    from agents.subagents.flight_agent import (
        flight_assistant_node,
        flight_safe_tools,
        flight_sensitive_tools,
        create_skill_router as create_flight_router
    )
    from agents.subagents.hotel_agent import (
        hotel_assistant_node,
        hotel_safe_tools,
        hotel_sensitive_tools,
        create_skill_router as create_hotel_router
    )
    from agents.subagents.car_rental_agent import (
        car_rental_assistant_node,
        car_rental_safe_tools,
        car_rental_sensitive_tools,
        create_skill_router as create_car_rental_router
    )
    from agents.subagents.excursion_agent import (
        excursion_assistant_node,
        excursion_safe_tools,
        excursion_sensitive_tools,
        create_skill_router as create_excursion_router
    )

    builder = StateGraph(State)

    builder.add_node("fetch_user_info", fetch_user_info_node)
    builder.add_node("primary_assistant", primary_assistant_node)
    builder.add_node("primary_tools_node", ToolNode(primary_assistant_tools))
    builder.add_node("leave_skill", leave_skill_node)

    builder.add_node(
        "enter_flight_assistant", create_entry_node("Vuelos", "flight_assistant")
    )
    builder.add_node("flight_assistant", flight_assistant_node)
    builder.add_node("flight_safe_tools", ToolNode(flight_safe_tools))
    builder.add_node("flight_sensitive_tools", ToolNode(flight_sensitive_tools))

    builder.add_node(
        "enter_hotel_assistant", create_entry_node("Hoteles", "hotel_assistant")
    )
    builder.add_node("hotel_assistant", hotel_assistant_node)
    builder.add_node("hotel_safe_tools", ToolNode(hotel_safe_tools))
    builder.add_node("hotel_sensitive_tools", ToolNode(hotel_sensitive_tools))

    builder.add_node(
        "enter_car_rental_assistant",
        create_entry_node("Alquiler de Coches", "car_rental_assistant"),
    )
    builder.add_node("car_rental_assistant", car_rental_assistant_node)
    builder.add_node("car_rental_safe_tools", ToolNode(car_rental_safe_tools))
    builder.add_node("car_rental_sensitive_tools", ToolNode(car_rental_sensitive_tools))

    builder.add_node(
        "enter_excursion_assistant", create_entry_node("Excursiones", "excursion_assistant")
    )
    builder.add_node("excursion_assistant", excursion_assistant_node)
    builder.add_node("excursion_safe_tools", ToolNode(excursion_safe_tools))
    builder.add_node("excursion_sensitive_tools", ToolNode(excursion_sensitive_tools))

    builder.add_edge(START, "fetch_user_info")
    builder.add_conditional_edges("fetch_user_info", route_to_workflow)
    builder.add_conditional_edges("primary_assistant", route_primary_assistant)
    builder.add_edge("primary_tools_node", "primary_assistant")
    builder.add_edge("leave_skill", "primary_assistant")

    skills_config = [
        ("flight", create_flight_router(flight_safe_tools)),
        ("hotel", create_hotel_router(hotel_safe_tools)),
        ("car_rental", create_car_rental_router(car_rental_safe_tools)),
        ("excursion", create_excursion_router(excursion_safe_tools)),
    ]

    for skill, router in skills_config:
        builder.add_edge(f"enter_{skill}_assistant", f"{skill}_assistant")
        builder.add_edge(f"{skill}_safe_tools", f"{skill}_assistant")
        builder.add_edge(f"{skill}_sensitive_tools", f"{skill}_assistant")

        builder.add_conditional_edges(
            f"{skill}_assistant",
            router,
            {
                "leave_skill": "leave_skill",
                "safe_tools": f"{skill}_safe_tools",
                "sensitive_tools": f"{skill}_sensitive_tools",
                END: END,
            },
        )

    memory = MemorySaver()
    graph = builder.compile(
        checkpointer=memory,
        interrupt_before=[
            "flight_sensitive_tools",
            "hotel_sensitive_tools",
            "car_rental_sensitive_tools",
            "excursion_sensitive_tools",
        ],
    )

    return graph


def fetch_user_info_node(state: State):
    """Fetch user flight information based on passenger_id"""
    passenger_id = state.get("passenger_id", "")
    if passenger_id:
        config = {"configurable": {"passenger_id": passenger_id}}
        user_info = fetch_user_flight_information.invoke(config)
    else:
        user_info = "No se ha identificado al usuario. Por favor proporcione su información."
    return {"user_info": user_info}

