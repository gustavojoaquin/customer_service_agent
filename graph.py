import os
from datetime import datetime
from typing import Annotated, Any, Literal, cast

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, Field, SecretStr
from typing_extensions import TypedDict

from tools import *

primary_assistant_tools = [
    fetch_user_flight_information,
    validate_flight_id,
    search_flights,
    search_available_flights,
    search_hotels,
    search_car_rentals,
    search_trip_recommendations,
    search_aircrafts,
    search_airports,
    search_boarding_passes,
    search_bookings,
    search_seats,
    search_ticket_flights,
    search_tickets,
]

flight_safe_tools = [
    fetch_user_flight_information,
    search_flights,
    search_available_flights,
    search_aircrafts,
    search_airports,
    search_boarding_passes,
    search_bookings,
    search_seats,
    search_ticket_flights,
    search_tickets,
]

flight_sensitive_tools = [
    create_flight,
    update_flight_status,
    update_flight_schedule,
    delete_flight,
    update_ticket_to_new_flight,
    cancel_ticket,
    book_flight,
    create_boarding_pass,
    update_boarding_pass_seat,
    delete_boarding_pass,
    create_booking,
    update_booking_amount,
    delete_booking,
    create_seat,
    update_seat_fare_conditions,
    delete_seat,
    create_ticket_flight,
    update_ticket_flight_fare_conditions,
    update_ticket_flight_amount,
    delete_ticket_flight,
    create_aircraft,
    update_aircraft_range,
    delete_aircraft,
    create_airport,
    update_airport_timezone,
    delete_airport,
    create_ticket,
    update_ticket_passenger,
    delete_ticket,
]

hotel_safe_tools = [
    search_hotels,
]

hotel_sensitive_tools = [
    book_hotel,
    cancel_hotel,
]

car_rental_safe_tools = [
    search_car_rentals,
]

car_rental_sensitive_tools = [
    book_car_rental,
    cancel_car_rental,
]

excursion_safe_tools = [
    search_trip_recommendations,
]

excursion_sensitive_tools = [
    book_excursion,
    cancel_excursion,
]



def update_dialog_stack(left: list[str], right: str | None) -> list[str]:
    """Función para gestionar la pila de diálogo de asistentes."""
    if right is None:
        return left
    if right == "pop":
        return left[:-1] if left else []
    return left + [right]


class State(TypedDict):
    """Define el estado del grafo."""

    messages: Annotated[list[AnyMessage], lambda x, y: x + y]
    user_info: str
    flight_id: str
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
    api_key=SecretStr(os.getenv("DEEPSEEK_API_KEY") or ""),
    base_url="https://api.deepseek.com",
    temperature=0,
)

primary_assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Eres un asistente de soporte al cliente. **RESPUESTAS EXTREMADAMENTE BREVES Y DIRECTAS.** Máximo 2-3 frases por respuesta. No expliques errores, solo di el resultado. No repitas información. Delega tareas específicas a especialistas. Info vuelos: <Flights>{user_info}</Flights>. Hora: {time}.",
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

flight_booking_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Especialista en vuelos. **RESPUESTAS EXTREMADAMENTE CORTAS.** Solo información esencial. No expliques errores. Puedes crear nuevos vuelos con create_flight. Usa CompleteOrEscalate al terminar.",
        ),
        ("placeholder", "{messages}"),
    ]
)

flight_runnable = flight_booking_prompt | llm.bind_tools(
    flight_safe_tools + flight_sensitive_tools + [CompleteOrEscalate]
)

hotel_booking_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Especialista en hoteles. **RESPUESTAS MUY CORTAS.** Solo información esencial. Usa CompleteOrEscalate al terminar.",
        ),
        ("placeholder", "{messages}"),
    ]
)

hotel_runnable = hotel_booking_prompt | llm.bind_tools(
    hotel_safe_tools + hotel_sensitive_tools + [CompleteOrEscalate]
)

car_rental_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Especialista en alquiler de coches. **RESPUESTAS MUY CORTAS.** Solo información esencial. Usa CompleteOrEscalate al terminar.",
        ),
        ("placeholder", "{messages}"),
    ]
)

car_rental_runnable = car_rental_prompt | llm.bind_tools(
    car_rental_safe_tools + car_rental_sensitive_tools + [CompleteOrEscalate]
)

excursion_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Especialista en excursiones. **RESPUESTAS MUY CORTAS.** Solo información esencial. Usa CompleteOrEscalate al terminar.",
        ),
        ("placeholder", "{messages}"),
    ]
)

excursion_runnable = excursion_prompt | llm.bind_tools(
    excursion_safe_tools + excursion_sensitive_tools + [CompleteOrEscalate]
)




def primary_assistant_node(state: State):
    """Nodo del asistente principal."""
    return {"messages": [assistant_runnable.invoke(state)]}


def flight_assistant_node(state: State):
    """Nodo del asistente de vuelos."""
    return {"messages": [flight_runnable.invoke(state)]}


def hotel_assistant_node(state: State):
    """Nodo del asistente de hoteles."""
    return {"messages": [hotel_runnable.invoke(state)]}


def car_rental_assistant_node(state: State):
    """Nodo del asistente de alquiler de coches."""
    return {"messages": [car_rental_runnable.invoke(state)]}


def excursion_assistant_node(state: State):
    """Nodo del asistente de excursiones."""
    return {"messages": [excursion_runnable.invoke(state)]}


def fetch_user_info_node(state: State):
    """Obtiene la información de vuelo del usuario basada en flight_id."""
    flight_id = state.get("flight_id", "")
    if flight_id and flight_id != "pending_validation":
        config = {"configurable": {"flight_id": flight_id}}
        try:
            user_info = fetch_user_flight_information.invoke(config)
        except Exception as e:
            user_info = f"Error al buscar información de vuelo: {e}"
    else:
        user_info = (
            "No se ha identificado el vuelo. Por favor proporcione su ID de vuelo."
        )
    return {"user_info": user_info}

def create_entry_node(assistant_name: str, new_dialog_state: str) -> callable:
    """Crea un nodo de entrada para un asistente especialista."""

    def entry_node(state: State) -> dict:
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            tool_call_id = last_message.tool_calls[0]["id"]
        else:
            tool_call_id = "unknown"
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
    """Nodo para salir de un asistente especialista y volver al principal."""
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        tool_call_id = last_message.tool_calls[0]["id"]
    else:
        tool_call_id = "unknown"
    return {
        "dialog_state": "pop",
        "messages": [
            ToolMessage(
                content="Regresando al asistente principal.", tool_call_id=tool_call_id
            )
        ],
    }


def route_primary_assistant(state: State):
    """Enrutador para el asistente principal."""
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
    """Crea un enrutador para un asistente especialista."""

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
    """Enrutador principal que dirige al asistente adecuado según el estado del diálogo."""
    return (
        state.get("dialog_state", [])[-1]
        if state.get("dialog_state")
        else "primary_assistant"
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
    ("flight", create_skill_router(flight_safe_tools)),
    ("hotel", create_skill_router(hotel_safe_tools)),
    ("car_rental", create_skill_router(car_rental_safe_tools)),
    ("excursion", create_skill_router(excursion_safe_tools)),
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
