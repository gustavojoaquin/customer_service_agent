"""Definición del State y modelos Pydantic para el grafo"""
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langchain_core.messages import AnyMessage
from pydantic import BaseModel, Field


def update_dialog_stack(left: list[str], right: str | None) -> list[str]:
    """Maneja la pila de diálogos para navegar entre asistentes"""
    if right is None:
        return left
    if right == "pop":
        return left[:-1] if left else []
    return left + [right]


class State(TypedDict):
    """Estado global del grafo de conversación"""
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


# Modelos de escalado entre asistentes
class CompleteOrEscalate(BaseModel):
    """Señala que el asistente completó su tarea"""
    reason: str


class ToFlightBookingAssistant(BaseModel):
    """Transferir al asistente de vuelos"""
    request: str = Field(
        description="Preguntas de seguimiento para aclarar la solicitud de vuelo."
    )


class ToHotelBookingAssistant(BaseModel):
    """Transferir al asistente de hoteles"""
    request: str = Field(description="Solicitud del usuario sobre la reserva de hotel.")


class ToCarRentalAssistant(BaseModel):
    """Transferir al asistente de alquiler de coches"""
    request: str = Field(
        description="Solicitud del usuario sobre el alquiler de un coche."
    )


class ToExcursionAssistant(BaseModel):
    """Transferir al asistente de excursiones"""
    request: str = Field(
        description="Solicitud del usuario sobre recomendaciones de viaje o excursiones."
    )