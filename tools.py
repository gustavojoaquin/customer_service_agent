import os
import sqlite3
from datetime import date, datetime
from typing import Optional, Union

import pytz
from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_tavily import TavilySearch

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
    """Actualiza el billete de un pasajero a un nuevo vuelo."""
    passenger_id = config.get("configurable", {}).get("passenger_id")
    if not passenger_id:
        raise ValueError("No se ha configurado un ID de pasajero.")

    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    cursor.execute("SELECT passenger_id FROM tickets WHERE ticket_no = ?", (ticket_no,))
    ticket_owner = cursor.fetchone()

    if not ticket_owner:
        cursor.close()
        conn.close()
        return f"No se encontró el billete con el número {ticket_no}."

    if ticket_owner[0] != passenger_id:
        cursor.close()
        conn.close()
        return f"El pasajero actual no es el propietario del billete {ticket_no}."

    cursor.execute(
        "SELECT flight_id FROM ticket_flights WHERE ticket_no = ?", (ticket_no,)
    )
    current_flight = cursor.fetchone()
    if not current_flight:
        cursor.close()
        conn.close()
        return f"El billete {ticket_no} no tiene un vuelo asignado actualmente."

    try:
        cursor.execute(
            "UPDATE ticket_flights SET flight_id = ? WHERE ticket_no = ?",
            (new_flight_id, ticket_no),
        )
        conn.commit()
        msg = "¡Billete actualizado al nuevo vuelo con éxito!"
    except sqlite3.Error as e:
        conn.rollback()
        msg = f"Error al actualizar el billete: {e}"
    finally:
        cursor.close()
        conn.close()

    return msg


@tool
def cancel_ticket(ticket_no: str, config: RunnableConfig) -> str:
    """
    Cancela una reserva de vuelo completa asociada a un número de billete.
    Esta acción elimina el billete, el asiento asignado y la asociación con el vuelo. Es irreversible.
    Utiliza esta herramienta para cualquier solicitud de cancelación de un pasajero.
    """
    passenger_id = config.get("configurable", {}).get("passenger_id")
    if not passenger_id:
        raise ValueError("No se ha configurado un ID de pasajero.")

    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    cursor.execute("SELECT passenger_id FROM tickets WHERE ticket_no = ?", (ticket_no,))
    ticket_row = cursor.fetchone()
    if not ticket_row:
        cursor.close()
        conn.close()
        return f"No se encontró el billete con el número {ticket_no}."

    if ticket_row[0] != passenger_id:
        cursor.close()
        conn.close()
        return f"El pasajero actual no es el propietario del billete {ticket_no}."

    try:
        cursor.execute("DELETE FROM boarding_passes WHERE ticket_no = ?", (ticket_no,))
        cursor.execute("DELETE FROM ticket_flights WHERE ticket_no = ?", (ticket_no,))
        cursor.execute("DELETE FROM tickets WHERE ticket_no = ?", (ticket_no,))
        conn.commit()

        if cursor.rowcount > 0:
            msg = "¡Billete cancelado con éxito!"
        else:
            msg = f"No se pudo eliminar el billete {ticket_no} (posiblemente ya eliminado)."

    except sqlite3.Error as e:
        conn.rollback()
        msg = f"Error al cancelar el billete: {e}"
    finally:
        cursor.close()
        conn.close()

    return msg


@tool
def register_new_flight(
    flight_no: str,
    departure_airport: str,
    arrival_airport: str,
    scheduled_departure: str,
    scheduled_arrival: str,
    passenger_name: str,
    passenger_email: str,
    fare_conditions: str = "Economy",
    config: Optional[RunnableConfig] = None,
) -> str:
    """Registra un nuevo vuelo y crea un billete para el pasajero."""
    passenger_id = (
        config.get("configurable", {}).get("passenger_id") if config else None
    )
    if not passenger_id:
        raise ValueError("No se ha configurado un ID de pasajero.")

    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    try:
        import uuid

        flight_id = str(uuid.uuid4())
        ticket_no = str(uuid.uuid4())
        book_ref = str(uuid.uuid4())[:6].upper()

        cursor.execute(
            "INSERT INTO flights (flight_id, flight_no, departure_airport, arrival_airport, scheduled_departure, scheduled_arrival) VALUES (?, ?, ?, ?, ?, ?)",
            (
                flight_id,
                flight_no,
                departure_airport,
                arrival_airport,
                scheduled_departure,
                scheduled_arrival,
            ),
        )

        cursor.execute(
            "INSERT INTO tickets (ticket_no, book_ref, passenger_id) VALUES (?, ?, ?)",
            (ticket_no, book_ref, passenger_id),
        )

        cursor.execute(
            "INSERT INTO ticket_flights (ticket_no, flight_id, fare_conditions) VALUES (?, ?, ?)",
            (ticket_no, flight_id, fare_conditions),
        )

        seat_no = f"{ord(passenger_name[0]) % 26 + 1}{chr(ord('A') + (len(passenger_name) % 6))}"
        cursor.execute(
            "INSERT INTO boarding_passes (ticket_no, flight_id, seat_no) VALUES (?, ?, ?)",
            (ticket_no, flight_id, seat_no),
        )

        conn.commit()

        return f"¡Vuelo registrado con éxito!\n\nDetalles:\n- Vuelo: {flight_no}\n- Ruta: {departure_airport} → {arrival_airport}\n- Salida: {scheduled_departure}\n- Llegada: {scheduled_arrival}\n- Pasajero: {passenger_name}\n- Email: {passenger_email}\n- Clase: {fare_conditions}\n- Asiento: {seat_no}\n- Número de billete: {ticket_no}\n- Referencia de reserva: {book_ref}"

    except Exception as e:
        conn.rollback()
        return f"Error al registrar el vuelo: {str(e)}"
    finally:
        cursor.close()
        conn.close()


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

primary_assistant_tools = [ fetch_user_flight_information, lookup_policy]

flight_safe_tools = [search_flights, lookup_policy]
flight_sensitive_tools = [
    update_ticket_to_new_flight,
    cancel_ticket,
    register_new_flight,
]

car_rental_safe_tools = [search_car_rentals, lookup_policy]
car_rental_sensitive_tools = [book_car_rental, cancel_car_rental]

hotel_safe_tools = [search_hotels, lookup_policy]
hotel_sensitive_tools = [book_hotel, cancel_hotel]

excursion_safe_tools = [search_trip_recommendations, lookup_policy]
excursion_sensitive_tools = [book_excursion, cancel_excursion]
