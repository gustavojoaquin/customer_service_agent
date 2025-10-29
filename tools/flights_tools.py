from datetime import date, datetime
from typing import Optional
import uuid
import hashlib

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from typing import Optional
from config.database import get_db_connection


@tool
def fetch_user_flight_information(config: RunnableConfig) -> list[dict]:
    """Obtiene toda la información de vuelos y asientos para el usuario actual."""
    passenger_id = config.get("configurable", {}).get("passenger_id")
    if not passenger_id:
        raise ValueError("No se ha configurado un ID de pasajero.")

    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
    SELECT t.ticket_no, t.book_ref, f.flight_id, f.flight_no, f.departure_airport, f.arrival_airport, f.scheduled_departure, f.scheduled_arrival, bp.seat_no, tf.fare_conditions
    FROM tickets t
    JOIN ticket_flights tf ON t.ticket_no = tf.ticket_no
    JOIN flights f ON tf.flight_id = f.flight_id
    JOIN boarding_passes bp ON bp.ticket_no = t.ticket_no AND bp.flight_id = f.flight_id
    WHERE t.passenger_id = %s
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
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM flights WHERE 1 = 1"
    params = []
    if departure_airport:
        query += " AND departure_airport = %s"
        params.append(departure_airport)
    if arrival_airport:
        query += " AND arrival_airport = %s"
        params.append(arrival_airport)
    if start_time:
        query += " AND scheduled_departure >= %s"
        params.append(start_time)
    if end_time:
        query += " AND scheduled_departure <= %s"
        params.append(end_time)
    query += " LIMIT %s"
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

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT passenger_id FROM tickets WHERE ticket_no = %s", (ticket_no,))
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
        "SELECT flight_id FROM ticket_flights WHERE ticket_no = %s", (ticket_no,)
    )
    current_flight = cursor.fetchone()
    if not current_flight:
        cursor.close()
        conn.close()
        return f"El billete {ticket_no} no tiene un vuelo asignado actualmente."

    try:
        cursor.execute(
            "UPDATE ticket_flights SET flight_id = %s WHERE ticket_no = %s",
            (new_flight_id, ticket_no),
        )
        conn.commit()
        msg = "¡Billete actualizado al nuevo vuelo con éxito!"
    except Exception as e:
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

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT passenger_id FROM tickets WHERE ticket_no = %s", (ticket_no,))
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
        cursor.execute("DELETE FROM boarding_passes WHERE ticket_no = %s", (ticket_no,))
        cursor.execute("DELETE FROM ticket_flights WHERE ticket_no = %s", (ticket_no,))
        cursor.execute("DELETE FROM tickets WHERE ticket_no = %s", (ticket_no,))
        conn.commit()

        if cursor.rowcount > 0:
            msg = "¡Billete cancelado con éxito!"
        else:
            msg = f"No se pudo eliminar el billete {ticket_no} (posiblemente ya eliminado)."

    except Exception as e:
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
    # Try to get passenger_id from config, but if not available, generate one from passenger info
    passenger_id = (
        config.get("configurable", {}).get("passenger_id") if config else None
    )

    # If no passenger_id is provided, generate one based on passenger name and email
    if not passenger_id:
        # Create a unique passenger_id from name and email
        passenger_info = f"{passenger_name}{passenger_email}"
        passenger_id = hashlib.md5(passenger_info.encode()).hexdigest()[:12].upper()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        flight_id = str(uuid.uuid4())
        ticket_no = str(uuid.uuid4())
        book_ref = str(uuid.uuid4())[:6].upper()

        cursor.execute(
            "INSERT INTO flights (flight_id, flight_no, departure_airport, arrival_airport, scheduled_departure, scheduled_arrival) VALUES (%s, %s, %s, %s, %s, %s)",
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
            "INSERT INTO tickets (ticket_no, book_ref, passenger_id) VALUES (%s, %s, %s)",
            (ticket_no, book_ref, passenger_id),
        )

        cursor.execute(
            "INSERT INTO ticket_flights (ticket_no, flight_id, fare_conditions) VALUES (%s, %s, %s)",
            (ticket_no, flight_id, fare_conditions),
        )

        seat_no = f"{ord(passenger_name[0]) % 26 + 1}{chr(ord('A') + (len(passenger_name) % 6))}"
        cursor.execute(
            "INSERT INTO boarding_passes (ticket_no, flight_id, seat_no) VALUES (%s, %s, %s)",
            (ticket_no, flight_id, seat_no),
        )

        conn.commit()

        return f"¡Vuelo registrado con éxito!\n\nDetalles:\n- Vuelo: {flight_no}\n- Ruta: {departure_airport} → {arrival_airport}\n- Salida: {scheduled_departure}\n- Llegada: {scheduled_arrival}\n- Pasajero: {passenger_name}\n- Email: {passenger_email}\n- Clase: {fare_conditions}\n- Asiento: {seat_no}\n- Número de billete: {ticket_no}\n- Referencia de reserva: {book_ref}\n- ID de pasajero: {passenger_id}"

    except Exception as e:
        conn.rollback()
        return f"Error al registrar el vuelo: {str(e)}"
    finally:
        cursor.close()
        conn.close()