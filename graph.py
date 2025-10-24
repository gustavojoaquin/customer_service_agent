import json
import os
from datetime import datetime
from typing import Annotated, Literal

from langchain_core.messages import AIMessage, AnyMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from tools import *


def update_dialog_stack(left: list[str], right: str | None) -> list[str]:
    if right is None:
        return left
    if right == "pop":
        return left[:-1] if left else []
    return left + [right]


class State(TypedDict):
    messages: Annotated[list[AnyMessage], lambda x, y: x + y]
    user_info: list
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
    reason: str


class ToFlightBookingAssistant(BaseModel):
    request: str = Field(
        description="Preguntas de seguimiento para aclarar la solicitud de vuelo."
    )


class ToHotelBookingAssistant(BaseModel):
    request: str = Field(description="Solicitud del usuario sobre la reserva de hotel.")


class ToCarRentalAssistant(BaseModel):
    request: str = Field(
        description="Solicitud del usuario sobre el alquiler de un coche."
    )


class ToExcursionAssistant(BaseModel):
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
            """Eres un asistente virtual de atención al cliente de una agencia de viajes ✈️. 
Tu función principal es **ayudar al usuario con temas relacionados a sus viajes**, especialmente:
- Reservas o cambios de vuelos.
- Consultas sobre hoteles, alquiler de coches o excursiones.
- Preguntas generales sobre su itinerario o próximas reservas.

📱 Contexto: Estás conversando por **Telegram**, por lo que tus respuestas deben ser:
- Cortas, naturales y con tono humano.
- Puedes usar algunos emojis (✈️, 🏨, 🚗, 🌍, 😊) de forma ligera.
- No des respuestas largas ni robóticas, ni uses lenguaje técnico.

🚫 Si el usuario pregunta algo fuera de estos temas (como matemáticas, chistes, política, tecnología, etc.), 
responde de forma amable y breve indicando que solo puedes ayudar con temas de viajes.

Ejemplo:
Usuario: "¿Cuánto es 2+2?"
Tú: "😅 No soy muy bueno con matemáticas, pero puedo ayudarte con tu vuelo o reserva si quieres."

Información del vuelo del usuario: <Flights>{user_info}</Flights>.
Hora actual: {time}.
""",
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
            "Eres un asistente experto en la gestión de reservas de vuelos. Tus tareas incluyen buscar vuelos, actualizar billetes existentes y registrar nuevos vuelos. Para registrar un nuevo vuelo, DEBES obtener primero del usuario la siguiente información: su nombre completo y su dirección de correo electrónico. Una vez que tengas toda la información, utiliza las herramientas disponibles para completar la tarea. Si la tarea se completa, usa la herramienta CompleteOrEscalate.",
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
            "Eres un asistente especializado en reservar hoteles. Ayuda al usuario a encontrar y reservar un hotel. Si la tarea se completa, usa CompleteOrEscalate.",
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
            "Eres un asistente especializado en alquilar coches. Ayuda al usuario a encontrar y reservar un coche. Si la tarea se completa, usa CompleteOrEscalate.",
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
            "Eres un asistente especializado en recomendar y reservar excursiones. Si la tarea se completa, usa CompleteOrEscalate.",
        ),
        ("placeholder", "{messages}"),
    ]
)
excursion_runnable = excursion_prompt | llm.bind_tools(
    excursion_safe_tools + excursion_sensitive_tools + [CompleteOrEscalate]
)


def _process_messages_for_llm(state: State) -> list[AnyMessage]:
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


def primary_assistant_node(state: State):
    temp_state = state.copy()
    temp_state["messages"] = _process_messages_for_llm(state)
    result = assistant_runnable.invoke(temp_state)
    return {"messages": [result]}


def flight_assistant_node(state: State):
    temp_state = state.copy()
    temp_state["messages"] = _process_messages_for_llm(state)
    result = flight_runnable.invoke(temp_state)
    return {"messages": [result]}


def hotel_assistant_node(state: State):
    temp_state = state.copy()
    temp_state["messages"] = _process_messages_for_llm(state)
    result = hotel_runnable.invoke(temp_state)
    return {"messages": [result]}


def car_rental_assistant_node(state: State):
    temp_state = state.copy()
    temp_state["messages"] = _process_messages_for_llm(state)
    result = car_rental_runnable.invoke(temp_state)
    return {"messages": [result]}


def excursion_assistant_node(state: State):
    temp_state = state.copy()
    temp_state["messages"] = _process_messages_for_llm(state)
    result = excursion_runnable.invoke(temp_state)
    return {"messages": [result]}


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


def create_skill_router(safe_tools: list) -> callable:
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
    return (
        state.get("dialog_state", [])[-1]
        if state.get("dialog_state")
        else "primary_assistant"
    )


builder = StateGraph(State)

builder.add_node(
    "fetch_user_info",
    lambda state: {"user_info": fetch_user_flight_information.invoke({})},
)
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

for skill in ["flight", "hotel", "car_rental", "excursion"]:
    builder.add_edge(f"enter_{skill}_assistant", f"{skill}_assistant")
    builder.add_edge(f"{skill}_safe_tools", f"{skill}_assistant")
    builder.add_edge(f"{skill}_sensitive_tools", f"{skill}_assistant")

    safe_tools_list = globals()[f"{skill}_safe_tools"]
    builder.add_conditional_edges(
        f"{skill}_assistant",
        create_skill_router(safe_tools_list),
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
