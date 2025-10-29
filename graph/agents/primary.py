"""Asistente principal - punto de entrada"""
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import os

from tools import primary_assistant_tools
from graph.state import (
    ToFlightBookingAssistant,
    ToHotelBookingAssistant,
    ToCarRentalAssistant,
    ToExcursionAssistant,
    State
)
from graph.nodes import _process_messages_for_llm


# LLM
llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0,
)


# Prompt del asistente principal
primary_assistant_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """Eres un **asistente virtual de atención al cliente** para una agencia de viajes ✈️. 
Tu misión es ayudar al usuario con todo lo relacionado con su viaje, analizando **el tipo de solicitud**
para decidir cómo responder o qué herramienta (agente) usar.

🎯 **Flujo de análisis de la consulta:**
1. **Identifica la categoría** de la consulta:
   - ✈️ VUELOS → reservas, cambios, horarios, check-in, asientos.
   - 🏨 HOTELES → disponibilidad, cancelaciones, servicios, ubicación.
   - 🚗 ALQUILER DE COCHE → precios, modelos, devoluciones, seguros.
   - 🌍 EXCURSIONES / TOURS → actividades, fechas, reservas.
2. **Selecciona internamente la herramienta o agente adecuado** según la categoría.
3. **Si la consulta no está relacionada con viajes**, responde de forma breve y amable indicando que solo puedes ayudar con temas de viajes.

📱 **Estilo de respuesta:**
- Corto, natural y humano.
- Uso ligero de emojis (✈️, 🏨, 🚗, 🌍, 😊).
- Evita respuestas largas, técnicas o robóticas.

La fecha y hora actual es: {time}
"""
    ),
    ("placeholder", "{messages}")
])


def primary_assistant_node(state: State):
    """Nodo del asistente principal"""
    temp_state = state.copy()
    temp_state["messages"] = _process_messages_for_llm(state)
    
    # Inyectar hora actual
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dynamic_prompt = primary_assistant_prompt.partial(time=current_time)
    
    runnable = dynamic_prompt | llm.bind_tools(
        primary_assistant_tools + [
            ToFlightBookingAssistant,
            ToHotelBookingAssistant,
            ToCarRentalAssistant,
            ToExcursionAssistant,
        ]
    )
    
    result = runnable.invoke(temp_state)
    return {"messages": [result]}