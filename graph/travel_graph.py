"""Construcción y compilación del grafo principal"""

from .agents import (
    primary_assistant_node,
    flight_assistant_node,
    hotel_assistant_node,
    car_rental_assistant_node,
    excursion_assistant_node
)


from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import Connection

from config.database import get_connection_string
from tools import (
    primary_assistant_tools,
    fetch_user_flight_information,
    flight_safe_tools, flight_sensitive_tools,
    hotel_safe_tools, hotel_sensitive_tools,
    car_rental_safe_tools, car_rental_sensitive_tools,
    excursion_safe_tools, excursion_sensitive_tools
)
from .state import State
from .nodes import create_entry_node, leave_skill_node
from .routing import route_primary_assistant, create_skill_router, route_to_workflow



# ✅ Checkpointer con PostgreSQL
connection_string = get_connection_string()


# Construcción del grafo
builder = StateGraph(State)

# Nodos iniciales
builder.add_node(
    "fetch_user_info",
    lambda state: {"user_info": fetch_user_flight_information.invoke({})}
)
builder.add_node("primary_assistant", primary_assistant_node)
builder.add_node("primary_tools_node", ToolNode(primary_assistant_tools))
builder.add_node("leave_skill", leave_skill_node)

# Asistente de vuelos
builder.add_node("enter_flight_assistant", create_entry_node("Vuelos", "flight_assistant"))
builder.add_node("flight_assistant", flight_assistant_node)
builder.add_node("flight_safe_tools", ToolNode(flight_safe_tools))
builder.add_node("flight_sensitive_tools", ToolNode(flight_sensitive_tools))

# Asistente de hoteles
builder.add_node("enter_hotel_assistant", create_entry_node("Hoteles", "hotel_assistant"))
builder.add_node("hotel_assistant", hotel_assistant_node)
builder.add_node("hotel_safe_tools", ToolNode(hotel_safe_tools))
builder.add_node("hotel_sensitive_tools", ToolNode(hotel_sensitive_tools))

# Asistente de coches
builder.add_node("enter_car_rental_assistant", create_entry_node("Alquiler de Coches", "car_rental_assistant"))
builder.add_node("car_rental_assistant", car_rental_assistant_node)
builder.add_node("car_rental_safe_tools", ToolNode(car_rental_safe_tools))
builder.add_node("car_rental_sensitive_tools", ToolNode(car_rental_sensitive_tools))

# Asistente de excursiones
builder.add_node("enter_excursion_assistant", create_entry_node("Excursiones", "excursion_assistant"))
builder.add_node("excursion_assistant", excursion_assistant_node)
builder.add_node("excursion_safe_tools", ToolNode(excursion_safe_tools))
builder.add_node("excursion_sensitive_tools", ToolNode(excursion_sensitive_tools))

# Edges
builder.add_edge(START, "fetch_user_info")
builder.add_conditional_edges("fetch_user_info", route_to_workflow)
builder.add_conditional_edges("primary_assistant", route_primary_assistant)
builder.add_edge("primary_tools_node", "primary_assistant")
builder.add_edge("leave_skill", "primary_assistant")

# Edges dinámicos para cada skill
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

# Crear el checkpointer SIN usar 'with'
checkpointer = PostgresSaver(
    Connection.connect(connection_string, autocommit=True)
)
# ✅ Compilar con checkpointer
graph = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=[
        "flight_sensitive_tools",
        "hotel_sensitive_tools",
        "car_rental_sensitive_tools",
        "excursion_sensitive_tools",
    ],
)