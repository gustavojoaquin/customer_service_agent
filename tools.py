import sqlite3
from datetime import date, datetime
from typing import Optional, Union

import pytz
from langchain_tavily import TavilySearch
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
import os
from dotenv import load_dotenv
load_dotenv()
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


@tool
def search_car_rentals(
    location: Optional[str] = None,
    name: Optional[str] = None,
    price_tier: Optional[str] = None,
    start_date: Optional[Union[datetime, date]] = None,
    end_date: Optional[Union[datetime, date]] = None,
) -> list[dict]:
    """Busca alquileres de coches."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    query = "SELECT * FROM car_rentals WHERE 1=1"
    params = []
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")
    if name:
        query += " AND name LIKE ?"
        params.append(f"%{name}%")
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    return [
        dict(zip([column[0] for column in cursor.description], row)) for row in results
    ]


@tool
def book_car_rental(rental_id: int) -> str:
    """Reserva un alquiler de coche por su ID."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("UPDATE car_rentals SET booked = 1 WHERE id = ?", (rental_id,))
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Alquiler de coche {rental_id} reservado con éxito."
    conn.close()
    return f"No se encontró un alquiler de coche con ID {rental_id}."


@tool
def cancel_car_rental(rental_id: int) -> str:
    """Cancela una reserva de alquiler de coche por su ID."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("UPDATE car_rentals SET booked = 0 WHERE id = ?", (rental_id,))
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Reserva de alquiler de coche {rental_id} cancelada con éxito."
    conn.close()
    return f"No se encontró un alquiler de coche con ID {rental_id}."


@tool
def search_hotels(
    location: Optional[str] = None,
    name: Optional[str] = None,
    price_tier: Optional[str] = None,
    checkin_date: Optional[Union[datetime, date]] = None,
    checkout_date: Optional[Union[datetime, date]] = None,
) -> list[dict]:
    """Busca hoteles."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    query = "SELECT * FROM hotels WHERE 1=1"
    params = []
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")
    if name:
        query += " AND name LIKE ?"
        params.append(f"%{name}%")
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    return [
        dict(zip([column[0] for column in cursor.description], row)) for row in results
    ]


@tool
def book_hotel(hotel_id: int) -> str:
    """Reserva un hotel por su ID."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("UPDATE hotels SET booked = 1 WHERE id = ?", (hotel_id,))
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Hotel {hotel_id} reservado con éxito."
    conn.close()
    return f"No se encontró un hotel con ID {hotel_id}."


@tool
def cancel_hotel(hotel_id: int) -> str:
    """Cancela una reserva de hotel por su ID."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("UPDATE hotels SET booked = 0 WHERE id = ?", (hotel_id,))
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Reserva de hotel {hotel_id} cancelada con éxito."
    conn.close()
    return f"No se encontró un hotel con ID {hotel_id}."


@tool
def search_trip_recommendations(
    location: Optional[str] = None,
    name: Optional[str] = None,
    keywords: Optional[str] = None,
) -> list[dict]:
    """Busca recomendaciones de viajes y excursiones."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    query = "SELECT * FROM trip_recommendations WHERE 1=1"
    params = []
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")
    if name:
        query += " AND name LIKE ?"
        params.append(f"%{name}%")
    if keywords:
        pass
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    return [
        dict(zip([column[0] for column in cursor.description], row)) for row in results
    ]


@tool
def book_excursion(recommendation_id: int) -> str:
    """Reserva una excursión por su ID."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE trip_recommendations SET booked = 1 WHERE id = ?", (recommendation_id,)
    )
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Excursión {recommendation_id} reservada con éxito."
    conn.close()
    return f"No se encontró una excursión con ID {recommendation_id}."


@tool
def cancel_excursion(recommendation_id: int) -> str:
    """Cancela una reserva de excursión por su ID."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE trip_recommendations SET booked = 0 WHERE id = ?", (recommendation_id,)
    )
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Reserva de excursión {recommendation_id} cancelada con éxito."
    conn.close()
    return f"No se encontró una excursión con ID {recommendation_id}."


@tool
def lookup_policy(query: str) -> str:
    """Consulta las políticas de la compañía."""
    if "cambio" in query or "modificar" in query:
        return "Los cambios están permitidos con una tarifa de $100 si se realizan más de 24 horas antes de la salida."
    return "No se encontró una política específica para su consulta."


tavily_tool = TavilySearch(max_results=3)

primary_assistant_tools = [tavily_tool, fetch_user_flight_information, lookup_policy]

flight_safe_tools = [search_flights, lookup_policy]
flight_sensitive_tools = [update_ticket_to_new_flight, cancel_ticket]

car_rental_safe_tools = [search_car_rentals, lookup_policy]
car_rental_sensitive_tools = [book_car_rental, cancel_car_rental]

hotel_safe_tools = [search_hotels, lookup_policy]
hotel_sensitive_tools = [book_hotel, cancel_hotel]

excursion_safe_tools = [search_trip_recommendations, lookup_policy]
excursion_sensitive_tools = [book_excursion, cancel_excursion]
