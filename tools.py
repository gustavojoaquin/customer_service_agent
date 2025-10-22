import sqlite3
from datetime import date, datetime
from typing import Optional

import pytz
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

db = "travel2.sqlite"


@tool
def fetch_user_flight_information(config: RunnableConfig) -> list[dict]:
    """Obtiene toda la información de vuelos y asientos para el usuario actual."""
    passenger_id = config.get("configurable", {}).get("passenger_id")
    if not passenger_id:
        raise ValueError("No se ha configurado un ID de pasajero.")

    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    query = """
    SELECT t.ticket_no, t.book_ref, f.flight_id, f.flight_no, f.departure_airport, f.arrival_airport, f.scheduled_departure, f.scheduled_arrival, bp.seat_no, tf.fare_conditions
    FROM tickets t
    JOIN ticket_flights tf ON t.ticket_no = tf.ticket_no
    JOIN flights f ON tf.flight_id = f.flight_id
    JOIN boarding_passes bp ON bp.ticket_no = t.ticket_no AND bp.flight_id = f.flight_id
    WHERE t.passenger_id = ?
    """
    cursor.execute(query, (passenger_id,))
    rows = cursor.fetchall()
    column_names = [column[0] for column in cursor.description]
    results = [dict(zip(column_names, row)) for row in rows]
    cursor.close()
    conn.close()
    return results


@tool
def search_flights(
    departure_airport: Optional[str] = None,
    arrival_airport: Optional[str] = None,
    start_time: Optional[date | datetime] = None,
    end_time: Optional[date | datetime] = None,
    limit: int = 20,
) -> list[dict]:
    """Busca vuelos basados en el aeropuerto de salida, llegada y rango de fechas."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    query = "SELECT * FROM flights WHERE 1 = 1"
    params = []
    if departure_airport:
        query += " AND departure_airport = ?"
        params.append(departure_airport)
    if arrival_airport:
        query += " AND arrival_airport = ?"
        params.append(arrival_airport)
    if start_time:
        query += " AND scheduled_departure >= ?"
        params.append(start_time)
    if end_time:
        query += " AND scheduled_departure <= ?"
        params.append(end_time)
    query += " LIMIT ?"
    params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    column_names = [column[0] for column in cursor.description]
    results = [dict(zip(column_names, row)) for row in rows]
    cursor.close()
    conn.close()
    return results


@tool
def update_ticket_to_new_flight(
    ticket_no: str, new_flight_id: int, config: RunnableConfig
) -> str:
    """Actualiza el billete del usuario a un nuevo vuelo válido."""
    passenger_id = config.get("configurable", {}).get("passenger_id")
    if not passenger_id:
        raise ValueError("No se ha configurado un ID de pasajero.")

    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT flight_id FROM ticket_flights WHERE ticket_no = ?", (ticket_no,)
    )
    current_flight = cursor.fetchone()
    if not current_flight:
        return "No se encontró un billete existente con ese número."

    cursor.execute(
        "UPDATE ticket_flights SET flight_id = ? WHERE ticket_no = ?",
        (new_flight_id, ticket_no),
    )
    conn.commit()
    cursor.close()
    conn.close()
    return "¡Billete actualizado al nuevo vuelo con éxito!"


@tool
def cancel_ticket(ticket_no: str, config: RunnableConfig) -> str:
    """Cancela el billete del usuario y lo elimina de la base de datos."""
    passenger_id = config.get("configurable", {}).get("passenger_id")
    if not passenger_id:
        raise ValueError("No se ha configurado un ID de pasajero.")

    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT flight_id FROM ticket_flights WHERE ticket_no = ?", (ticket_no,)
    )
    if not cursor.fetchone():
        return "No se encontró un billete con ese número."

    cursor.execute("DELETE FROM ticket_flights WHERE ticket_no = ?", (ticket_no,))
    conn.commit()
    cursor.close()
    conn.close()
    return "¡Billete cancelado con éxito!"


tavily_tool = TavilySearchResults(max_results=5)


@tool
def lookup_policy(query: str) -> str:
    """Consulta las políticas de la compañía para verificar si ciertas opciones están permitidas."""
    if "sooner" in query or "change" in query:
        return "Los cambios de vuelo están permitidos con una tarifa de $100 si se realizan más de 24 horas antes de la salida."
    return "No se encontró una política específica para su consulta. Por favor, sea más específico."


flight_tools = [
    search_flights,
    update_ticket_to_new_flight,
    cancel_ticket,
    lookup_policy,
]

primary_assistant_tools = [
    tavily_tool,
    fetch_user_flight_information,
]
