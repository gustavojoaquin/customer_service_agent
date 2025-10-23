import sqlite3
from datetime import date, datetime
from typing import Optional, Union

import pytz
from langchain_tavily import TavilySearch
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

db = "travel2.sqlite"


@tool
def fetch_user_flight_information(config: RunnableConfig) -> str:
    """Obtiene toda la información de vuelos y asientos para el usuario actual."""
    passenger_id = config.get("configurable", {}).get("passenger_id")

    if not passenger_id or passenger_id == "pending_validation":
        return "El ID de pasajero aún no ha sido validado. Por favor, proporcione su ID de pasajero o número de vuelo para continuar."

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

    if not results:
        return f"No se encontró información de vuelos para el ID de pasajero: {passenger_id}. Por favor, verifique que el ID sea correcto."

    formatted_flights = []
    for flight in results:
        formatted_flight = (
            f"Vuelo {flight['flight_no']}: {flight['departure_airport']} → {flight['arrival_airport']} "
            f"(Salida: {flight['scheduled_departure']}, Llegada: {flight['scheduled_arrival']}) "
            f"Asiento: {flight['seat_no']}, Clase: {flight['fare_conditions']}"
        )
        formatted_flights.append(formatted_flight)

    return f"Información de vuelos del usuario:\n" + "\n".join(formatted_flights)


@tool
def search_flights(
    departure_airport: Optional[str] = None,
    arrival_airport: Optional[str] = None,
    start_time: Optional[date | datetime] = None,
    end_time: Optional[date | datetime] = None,
    limit: int = 20,
) -> str:
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

    if not results:
        return "No se encontraron vuelos que coincidan con los criterios."

    formatted_flights = []
    for flight in results:
        formatted_flight = (
            f"Vuelo {flight['flight_no']}: {flight['departure_airport']} → {flight['arrival_airport']} "
            f"(Salida: {flight['scheduled_departure']}, Llegada: {flight['scheduled_arrival']})"
        )
        formatted_flights.append(formatted_flight)

    return f"Se encontraron {len(results)} vuelos:\n" + "\n".join(formatted_flights)


@tool
def create_flight(
    flight_id: int,
    flight_no: str,
    scheduled_departure: Union[datetime, date],
    scheduled_arrival: Union[datetime, date],
    departure_airport: str,
    arrival_airport: str,
    status: str = "Scheduled",
    aircraft_code: Optional[str] = None,
) -> str:
    """Crea un nuevo vuelo."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO flights
            (flight_id, flight_no, scheduled_departure, scheduled_arrival,
             departure_airport, arrival_airport, status, aircraft_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (flight_id, flight_no, scheduled_departure, scheduled_arrival,
             departure_airport, arrival_airport, status, aircraft_code)
        )
        conn.commit()
        conn.close()
        return f"Vuelo {flight_no} creado con éxito: {departure_airport} → {arrival_airport}."
    except sqlite3.IntegrityError:
        conn.close()
        return "Error: Ya existe un vuelo con ese ID."


@tool
def update_flight_status(flight_id: int, new_status: str) -> str:
    """Actualiza el estado de un vuelo."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE flights SET status = ? WHERE flight_id = ?",
        (new_status, flight_id)
    )
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Estado del vuelo {flight_id} actualizado con éxito a {new_status}."
    conn.close()
    return "No se encontró un vuelo con ese ID."


@tool
def update_flight_schedule(flight_id: int, new_departure: Union[datetime, date], new_arrival: Union[datetime, date]) -> str:
    """Actualiza el horario de un vuelo."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE flights SET scheduled_departure = ?, scheduled_arrival = ? WHERE flight_id = ?",
        (new_departure, new_arrival, flight_id)
    )
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Horario del vuelo {flight_id} actualizado con éxito."
    conn.close()
    return "No se encontró un vuelo con ese ID."


@tool
def delete_flight(flight_id: int) -> str:
    """Elimina un vuelo."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM flights WHERE flight_id = ?",
        (flight_id,)
    )
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Vuelo {flight_id} eliminado con éxito."
    conn.close()
    return "No se encontró un vuelo con ese ID."


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
) -> str:
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

    if not results:
        return "No se encontraron alquileres de coches que coincidan con los criterios."

    rentals = []
    for row in results:
        rental_dict = dict(zip([column[0] for column in cursor.description], row))
        formatted_rental = {}
        for key, value in rental_dict.items():
            if isinstance(value, (datetime, date)):
                formatted_rental[key] = value.isoformat()
            else:
                formatted_rental[key] = str(value) if value is not None else "N/A"
        rentals.append(formatted_rental)

    return f"Se encontraron {len(rentals)} alquileres de coches:\n" + "\n".join(
        f"- ID: {r['id']}, Nombre: {r['name']}, Ubicación: {r['location']}, Precio: {r.get('price_tier', 'N/A')}"
        for r in rentals
    )


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
) -> str:
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

    if not results:
        return "No se encontraron hoteles que coincidan con los criterios."

    hotels = [dict(zip([column[0] for column in cursor.description], row)) for row in results]

    return f"Se encontraron {len(hotels)} hoteles:\n" + "\n".join(
        f"- ID: {h['id']}, Nombre: {h['name']}, Ubicación: {h['location']}, Precio: {h.get('price_tier', 'N/A')}"
        for h in hotels
    )


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
) -> str:
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

    if not results:
        return "No se encontraron recomendaciones de viaje que coincidan con los criterios."

    recommendations = [
        dict(zip([column[0] for column in cursor.description], row)) for row in results
    ]

    return f"Se encontraron {len(recommendations)} recomendaciones de viaje:\n" + "\n".join(
        f"- ID: {r['id']}, Nombre: {r['name']}, Ubicación: {r['location']}, Descripción: {r.get('description', 'N/A')}"
        for r in recommendations
    )


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
def search_aircrafts(
    aircraft_code: Optional[str] = None,
    model: Optional[str] = None,
    range_min: Optional[int] = None,
    range_max: Optional[int] = None,
) -> str:
    """Busca información de aeronaves."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    query = "SELECT * FROM aircrafts_data WHERE 1=1"
    params = []
    if aircraft_code:
        query += " AND aircraft_code = ?"
        params.append(aircraft_code)
    if model:
        query += " AND model LIKE ?"
        params.append(f"%{model}%")
    if range_min:
        query += " AND range >= ?"
        params.append(range_min)
    if range_max:
        query += " AND range <= ?"
        params.append(range_max)
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    if not results:
        return "No se encontraron aeronaves que coincidan con los criterios."

    aircrafts = [dict(zip([column[0] for column in cursor.description], row)) for row in results]

    return f"Se encontraron {len(aircrafts)} aeronaves:\n" + "\n".join(
        f"- Código: {a['aircraft_code']}, Modelo: {a['model']}, Rango: {a['range']} km"
        for a in aircrafts
    )


@tool
def search_airports(
    airport_code: Optional[str] = None,
    airport_name: Optional[str] = None,
    city: Optional[str] = None,
) -> str:
    """Busca información de aeropuertos."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    query = "SELECT * FROM airports_data WHERE 1=1"
    params = []
    if airport_code:
        query += " AND airport_code = ?"
        params.append(aircraft_code)
    if airport_name:
        query += " AND airport_name LIKE ?"
        params.append(f"%{airport_name}%")
    if city:
        query += " AND city LIKE ?"
        params.append(f"%{city}%")
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    if not results:
        return "No se encontraron aeropuertos que coincidan con los criterios."

    airports = [dict(zip([column[0] for column in cursor.description], row)) for row in results]

    return f"Se encontraron {len(airports)} aeropuertos:\n" + "\n".join(
        f"- Código: {a['airport_code']}, Nombre: {a['airport_name']}, Ciudad: {a['city']}, Zona horaria: {a['timezone']}"
        for a in airports
    )


@tool
def search_boarding_passes(
    ticket_no: Optional[str] = None,
    flight_id: Optional[int] = None,
    seat_no: Optional[str] = None,
) -> str:
    """Busca pases de abordar."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    query = "SELECT * FROM boarding_passes WHERE 1=1"
    params = []
    if ticket_no:
        query += " AND ticket_no = ?"
        params.append(ticket_no)
    if flight_id:
        query += " AND flight_id = ?"
        params.append(flight_id)
    if seat_no:
        query += " AND seat_no = ?"
        params.append(seat_no)
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    if not results:
        return "No se encontraron pases de abordar que coincidan con los criterios."

    boarding_passes = [dict(zip([column[0] for column in cursor.description], row)) for row in results]

    return f"Se encontraron {len(boarding_passes)} pases de abordar:\n" + "\n".join(
        f"- Ticket: {bp['ticket_no']}, Vuelo: {bp['flight_id']}, Asiento: {bp['seat_no']}, Número de abordaje: {bp['boarding_no']}"
        for bp in boarding_passes
    )


@tool
def create_boarding_pass(ticket_no: str, flight_id: int, seat_no: str, boarding_no: int) -> str:
    """Crea un nuevo pase de abordar."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO boarding_passes (ticket_no, flight_id, seat_no, boarding_no) VALUES (?, ?, ?, ?)",
            (ticket_no, flight_id, seat_no, boarding_no)
        )
        conn.commit()
        conn.close()
        return f"Pase de abordar creado con éxito para el ticket {ticket_no}, vuelo {flight_id}, asiento {seat_no}."
    except sqlite3.IntegrityError:
        conn.close()
        return "Error: Ya existe un pase de abordar para este ticket y vuelo."


@tool
def update_boarding_pass_seat(ticket_no: str, flight_id: int, new_seat_no: str) -> str:
    """Actualiza el asiento de un pase de abordar."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE boarding_passes SET seat_no = ? WHERE ticket_no = ? AND flight_id = ?",
        (new_seat_no, ticket_no, flight_id)
    )
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Asiento actualizado con éxito a {new_seat_no} para el ticket {ticket_no}, vuelo {flight_id}."
    conn.close()
    return "No se encontró un pase de abordar con esos datos."


@tool
def delete_boarding_pass(ticket_no: str, flight_id: int) -> str:
    """Elimina un pase de abordar."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM boarding_passes WHERE ticket_no = ? AND flight_id = ?",
        (ticket_no, flight_id)
    )
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Pase de abordar eliminado con éxito para el ticket {ticket_no}, vuelo {flight_id}."
    conn.close()
    return "No se encontró un pase de abordar con esos datos."


@tool
def search_bookings(
    book_ref: Optional[str] = None,
    start_date: Optional[Union[datetime, date]] = None,
    end_date: Optional[Union[datetime, date]] = None,
    min_amount: Optional[int] = None,
    max_amount: Optional[int] = None,
) -> str:
    """Busca reservas."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    query = "SELECT * FROM bookings WHERE 1=1"
    params = []
    if book_ref:
        query += " AND book_ref = ?"
        params.append(book_ref)
    if start_date:
        query += " AND book_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND book_date <= ?"
        params.append(end_date)
    if min_amount:
        query += " AND total_amount >= ?"
        params.append(min_amount)
    if max_amount:
        query += " AND total_amount <= ?"
        params.append(max_amount)
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    if not results:
        return "No se encontraron reservas que coincidan con los criterios."

    bookings = [dict(zip([column[0] for column in cursor.description], row)) for row in results]

    return f"Se encontraron {len(bookings)} reservas:\n" + "\n".join(
        f"- Referencia: {b['book_ref']}, Fecha: {b['book_date']}, Monto total: ${b['total_amount']}"
        for b in bookings
    )


@tool
def create_booking(book_ref: str, total_amount: int) -> str:
    """Crea una nueva reserva."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO bookings (book_ref, book_date, total_amount) VALUES (?, datetime('now'), ?)",
            (book_ref, total_amount)
        )
        conn.commit()
        conn.close()
        return f"Reserva {book_ref} creada con éxito con monto total de ${total_amount}."
    except sqlite3.IntegrityError:
        conn.close()
        return "Error: Ya existe una reserva con esa referencia."


@tool
def update_booking_amount(book_ref: str, new_amount: int) -> str:
    """Actualiza el monto total de una reserva."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE bookings SET total_amount = ? WHERE book_ref = ?",
        (new_amount, book_ref)
    )
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Monto total actualizado con éxito a ${new_amount} para la reserva {book_ref}."
    conn.close()
    return "No se encontró una reserva con esa referencia."


@tool
def delete_booking(book_ref: str) -> str:
    """Elimina una reserva."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bookings WHERE book_ref = ?", (book_ref,))
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Reserva {book_ref} eliminada con éxito."
    conn.close()
    return "No se encontró una reserva con esa referencia."


@tool
def search_seats(
    aircraft_code: Optional[str] = None,
    seat_no: Optional[str] = None,
    fare_conditions: Optional[str] = None,
) -> str:
    """Busca información de asientos."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    query = "SELECT * FROM seats WHERE 1=1"
    params = []
    if aircraft_code:
        query += " AND aircraft_code = ?"
        params.append(aircraft_code)
    if seat_no:
        query += " AND seat_no = ?"
        params.append(seat_no)
    if fare_conditions:
        query += " AND fare_conditions = ?"
        params.append(fare_conditions)
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    if not results:
        return "No se encontraron asientos que coincidan con los criterios."

    seats = [dict(zip([column[0] for column in cursor.description], row)) for row in results]

    return f"Se encontraron {len(seats)} asientos:\n" + "\n".join(
        f"- Aeronave: {s['aircraft_code']}, Asiento: {s['seat_no']}, Clase: {s['fare_conditions']}"
        for s in seats
    )


@tool
def create_seat(aircraft_code: str, seat_no: str, fare_conditions: str) -> str:
    """Crea un nuevo asiento."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO seats (aircraft_code, seat_no, fare_conditions) VALUES (?, ?, ?)",
            (aircraft_code, seat_no, fare_conditions)
        )
        conn.commit()
        conn.close()
        return f"Asiento {seat_no} creado con éxito para la aeronave {aircraft_code}, clase {fare_conditions}."
    except sqlite3.IntegrityError:
        conn.close()
        return "Error: Ya existe ese asiento para esta aeronave."


@tool
def update_seat_fare_conditions(aircraft_code: str, seat_no: str, new_fare_conditions: str) -> str:
    """Actualiza las condiciones de tarifa de un asiento."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE seats SET fare_conditions = ? WHERE aircraft_code = ? AND seat_no = ?",
        (new_fare_conditions, aircraft_code, seat_no)
    )
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Condiciones de tarifa actualizadas con éxito a {new_fare_conditions} para el asiento {seat_no} de la aeronave {aircraft_code}."
    conn.close()
    return "No se encontró un asiento con esos datos."


@tool
def delete_seat(aircraft_code: str, seat_no: str) -> str:
    """Elimina un asiento."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM seats WHERE aircraft_code = ? AND seat_no = ?",
        (aircraft_code, seat_no)
    )
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Asiento {seat_no} eliminado con éxito de la aeronave {aircraft_code}."
    conn.close()
    return "No se encontró un asiento con esos datos."


@tool
def search_ticket_flights(
    ticket_no: Optional[str] = None,
    flight_id: Optional[int] = None,
    fare_conditions: Optional[str] = None,
) -> str:
    """Busca información de vuelos de tickets."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    query = "SELECT * FROM ticket_flights WHERE 1=1"
    params = []
    if ticket_no:
        query += " AND ticket_no = ?"
        params.append(ticket_no)
    if flight_id:
        query += " AND flight_id = ?"
        params.append(flight_id)
    if fare_conditions:
        query += " AND fare_conditions = ?"
        params.append(fare_conditions)
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    if not results:
        return "No se encontraron vuelos de tickets que coincidan con los criterios."

    ticket_flights = [dict(zip([column[0] for column in cursor.description], row)) for row in results]

    return f"Se encontraron {len(ticket_flights)} vuelos de tickets:\n" + "\n".join(
        f"- Ticket: {tf['ticket_no']}, Vuelo: {tf['flight_id']}, Clase: {tf['fare_conditions']}, Monto: ${tf['amount']}"
        for tf in ticket_flights
    )


@tool
def create_ticket_flight(ticket_no: str, flight_id: int, fare_conditions: str, amount: int) -> str:
    """Crea una nueva relación ticket-vuelo."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO ticket_flights (ticket_no, flight_id, fare_conditions, amount) VALUES (?, ?, ?, ?)",
            (ticket_no, flight_id, fare_conditions, amount)
        )
        conn.commit()
        conn.close()
        return f"Relación ticket-vuelo creada con éxito: ticket {ticket_no}, vuelo {flight_id}, clase {fare_conditions}, monto ${amount}."
    except sqlite3.IntegrityError:
        conn.close()
        return "Error: Ya existe una relación para este ticket y vuelo."


@tool
def update_ticket_flight_fare_conditions(ticket_no: str, flight_id: int, new_fare_conditions: str) -> str:
    """Actualiza las condiciones de tarifa de un ticket-vuelo."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE ticket_flights SET fare_conditions = ? WHERE ticket_no = ? AND flight_id = ?",
        (new_fare_conditions, ticket_no, flight_id)
    )
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Condiciones de tarifa actualizadas con éxito a {new_fare_conditions} para el ticket {ticket_no}, vuelo {flight_id}."
    conn.close()
    return "No se encontró una relación ticket-vuelo con esos datos."


@tool
def update_ticket_flight_amount(ticket_no: str, flight_id: int, new_amount: int) -> str:
    """Actualiza el monto de un ticket-vuelo."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE ticket_flights SET amount = ? WHERE ticket_no = ? AND flight_id = ?",
        (new_amount, ticket_no, flight_id)
    )
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Monto actualizado con éxito a ${new_amount} para el ticket {ticket_no}, vuelo {flight_id}."
    conn.close()
    return "No se encontró una relación ticket-vuelo con esos datos."


@tool
def delete_ticket_flight(ticket_no: str, flight_id: int) -> str:
    """Elimina una relación ticket-vuelo."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM ticket_flights WHERE ticket_no = ? AND flight_id = ?",
        (ticket_no, flight_id)
    )
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Relación ticket-vuelo eliminada con éxito para el ticket {ticket_no}, vuelo {flight_id}."
    conn.close()
    return "No se encontró una relación ticket-vuelo con esos datos."


@tool
def create_aircraft(aircraft_code: str, model: str, range_km: int) -> str:
    """Crea una nueva aeronave."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO aircrafts_data (aircraft_code, model, range) VALUES (?, ?, ?)",
            (aircraft_code, model, range_km)
        )
        conn.commit()
        conn.close()
        return f"Aeronave {aircraft_code} creada con éxito: modelo {model}, rango {range_km} km."
    except sqlite3.IntegrityError:
        conn.close()
        return "Error: Ya existe una aeronave con ese código."


@tool
def update_aircraft_range(aircraft_code: str, new_range: int) -> str:
    """Actualiza el rango de una aeronave."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE aircrafts_data SET range = ? WHERE aircraft_code = ?",
        (new_range, aircraft_code)
    )
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Rango actualizado con éxito a {new_range} km para la aeronave {aircraft_code}."
    conn.close()
    return "No se encontró una aeronave con ese código."


@tool
def delete_aircraft(aircraft_code: str) -> str:
    """Elimina una aeronave."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM aircrafts_data WHERE aircraft_code = ?",
        (aircraft_code,)
    )
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Aeronave {aircraft_code} eliminada con éxito."
    conn.close()
    return "No se encontró una aeronave con ese código."


@tool
def create_airport(airport_code: str, airport_name: str, city: str, timezone: str) -> str:
    """Crea un nuevo aeropuerto."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO airports_data (airport_code, airport_name, city, timezone) VALUES (?, ?, ?, ?)",
            (airport_code, airport_name, city, timezone)
        )
        conn.commit()
        conn.close()
        return f"Aeropuerto {airport_code} creado con éxito: {airport_name} en {city}, zona horaria {timezone}."
    except sqlite3.IntegrityError:
        conn.close()
        return "Error: Ya existe un aeropuerto con ese código."


@tool
def update_airport_timezone(airport_code: str, new_timezone: str) -> str:
    """Actualiza la zona horaria de un aeropuerto."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE airports_data SET timezone = ? WHERE airport_code = ?",
        (new_timezone, airport_code)
    )
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Zona horaria actualizada con éxito a {new_timezone} para el aeropuerto {airport_code}."
    conn.close()
    return "No se encontró un aeropuerto con ese código."


@tool
def delete_airport(airport_code: str) -> str:
    """Elimina un aeropuerto."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM airports_data WHERE airport_code = ?",
        (airport_code,)
    )
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Aeropuerto {airport_code} eliminado con éxito."
    conn.close()
    return "No se encontró un aeropuerto con ese código."


@tool
def search_tickets(
    ticket_no: Optional[str] = None,
    book_ref: Optional[str] = None,
    passenger_id: Optional[str] = None,
) -> str:
    """Busca tickets."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    query = "SELECT * FROM tickets WHERE 1=1"
    params = []
    if ticket_no:
        query += " AND ticket_no = ?"
        params.append(ticket_no)
    if book_ref:
        query += " AND book_ref = ?"
        params.append(book_ref)
    if passenger_id:
        query += " AND passenger_id = ?"
        params.append(passenger_id)
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    if not results:
        return "No se encontraron tickets que coincidan con los criterios."

    tickets = [dict(zip([column[0] for column in cursor.description], row)) for row in results]

    return f"Se encontraron {len(tickets)} tickets:\n" + "\n".join(
        f"- Ticket: {t['ticket_no']}, Reserva: {t['book_ref']}, Pasajero: {t['passenger_id']}"
        for t in tickets
    )


@tool
def create_ticket(ticket_no: str, book_ref: str, passenger_id: str) -> str:
    """Crea un nuevo ticket."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO tickets (ticket_no, book_ref, passenger_id) VALUES (?, ?, ?)",
            (ticket_no, book_ref, passenger_id)
        )
        conn.commit()
        conn.close()
        return f"Ticket {ticket_no} creado con éxito para el pasajero {passenger_id}, reserva {book_ref}."
    except sqlite3.IntegrityError:
        conn.close()
        return "Error: Ya existe un ticket con ese número."


@tool
def update_ticket_passenger(ticket_no: str, new_passenger_id: str) -> str:
    """Actualiza el pasajero de un ticket."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tickets SET passenger_id = ? WHERE ticket_no = ?",
        (new_passenger_id, ticket_no)
    )
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Pasajero actualizado con éxito a {new_passenger_id} para el ticket {ticket_no}."
    conn.close()
    return "No se encontró un ticket con ese número."


@tool
def delete_ticket(ticket_no: str) -> str:
    """Elimina un ticket."""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM tickets WHERE ticket_no = ?",
        (ticket_no,)
    )
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Ticket {ticket_no} eliminado con éxito."
    conn.close()
    return "No se encontró un ticket con ese número."


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
