# ================================================================
# setup_db.py — Base de datos completa para el asistente de vuelos
# ================================================================

import sqlite3
from datetime import datetime, timedelta

DB_FILE = "travel2.sqlite"

def setup_database():
    """Crea una base de datos SQLite completa con todas las tablas necesarias."""

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # --- Crear tabla de tickets ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_no TEXT PRIMARY KEY,
            book_ref TEXT,
            passenger_id TEXT
        )
    """)

    # --- Crear tabla de flights ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flights (
            flight_id TEXT PRIMARY KEY,
            flight_no TEXT,
            departure_airport TEXT,
            arrival_airport TEXT,
            scheduled_departure TEXT,
            scheduled_arrival TEXT
        )
    """)

    # --- Crear tabla de ticket_flights ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ticket_flights (
            ticket_no TEXT,
            flight_id TEXT,
            fare_conditions TEXT,
            PRIMARY KEY (ticket_no, flight_id),
            FOREIGN KEY (ticket_no) REFERENCES tickets(ticket_no),
            FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
        )
    """)

    # --- Crear tabla de boarding_passes ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS boarding_passes (
            ticket_no TEXT,
            flight_id TEXT,
            seat_no TEXT,
            PRIMARY KEY (ticket_no, flight_id),
            FOREIGN KEY (ticket_no) REFERENCES tickets(ticket_no),
            FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
        )
    """)

    # --- Crear tabla de car_rentals ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS car_rentals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            location TEXT,
            price_tier TEXT,
            booked INTEGER DEFAULT 0
        )
    """)

    # --- Crear tabla de hotels ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hotels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            location TEXT,
            price_tier TEXT,
            booked INTEGER DEFAULT 0
        )
    """)

    # --- Crear tabla de trip_recommendations ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trip_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            location TEXT,
            booked INTEGER DEFAULT 0
        )
    """)

    # --- Insertar datos de prueba de tickets ---
    tickets = [
        ("T001", "BR001", "3442 587242"),
        ("T002", "BR002", "3442 587242"),
        ("T003", "BR003", "U1002"),
        ("T004", "BR004", "U1003"),
    ]
    cursor.executemany("INSERT OR REPLACE INTO tickets (ticket_no, book_ref, passenger_id) VALUES (?, ?, ?)", tickets)

    # --- Insertar datos de prueba de flights ---
    now = datetime.now()
    flights = [
        ("F001", "AA100", "MAD", "CDG", (now + timedelta(hours=2)).isoformat(), (now + timedelta(hours=4)).isoformat()),
        ("F002", "BA200", "CDG", "TXL", (now + timedelta(days=1, hours=3)).isoformat(), (now + timedelta(days=1, hours=5)).isoformat()),
        ("F003", "UA300", "JFK", "LHR", (now + timedelta(hours=5)).isoformat(), (now + timedelta(hours=11)).isoformat()),
        ("F004", "KE400", "NRT", "ICN", (now + timedelta(hours=8)).isoformat(), (now + timedelta(hours=10)).isoformat()),
    ]
    cursor.executemany("INSERT OR REPLACE INTO flights (flight_id, flight_no, departure_airport, arrival_airport, scheduled_departure, scheduled_arrival) VALUES (?, ?, ?, ?, ?, ?)", flights)

    # --- Insertar datos de prueba de ticket_flights ---
    ticket_flights = [
        ("T001", "F001", "Economy"),
        ("T002", "F002", "Business"),
        ("T003", "F003", "Economy"),
        ("T004", "F004", "First"),
    ]
    cursor.executemany("INSERT OR REPLACE INTO ticket_flights (ticket_no, flight_id, fare_conditions) VALUES (?, ?, ?)", ticket_flights)

    # --- Insertar datos de prueba de boarding_passes ---
    boarding_passes = [
        ("T001", "F001", "12A"),
        ("T002", "F002", "1B"),
        ("T003", "F003", "24C"),
        ("T004", "F004", "2A"),
    ]
    cursor.executemany("INSERT OR REPLACE INTO boarding_passes (ticket_no, flight_id, seat_no) VALUES (?, ?, ?)", boarding_passes)

    # --- Insertar datos de prueba de car_rentals ---
    car_rentals = [
        ("Hertz", "Madrid Airport", "Premium", 0),
        ("Avis", "Paris CDG", "Standard", 0),
        ("Europcar", "Berlin Tegel", "Luxury", 0),
        ("Budget", "London Heathrow", "Economy", 0),
    ]
    cursor.executemany("INSERT OR REPLACE INTO car_rentals (name, location, price_tier, booked) VALUES (?, ?, ?, ?)", car_rentals)

    # --- Insertar datos de prueba de hotels ---
    hotels = [
        ("Hotel Ritz", "Madrid", "Luxury", 0),
        ("Hotel Plaza", "Paris", "Premium", 0),
        ("Hotel Berlin", "Berlin", "Standard", 0),
        ("Hotel Savoy", "London", "Luxury", 0),
    ]
    cursor.executemany("INSERT OR REPLACE INTO hotels (name, location, price_tier, booked) VALUES (?, ?, ?, ?)", hotels)

    # --- Insertar datos de prueba de trip_recommendations ---
    trip_recommendations = [
        ("Tour del Louvre", "Paris", 0),
        ("Paseo por el Retiro", "Madrid", 0),
        ("Visita al Muro de Berlín", "Berlin", 0),
        ("Tour del Big Ben", "London", 0),
    ]
    cursor.executemany("INSERT OR REPLACE INTO trip_recommendations (name, location, booked) VALUES (?, ?, ?)", trip_recommendations)

    conn.commit()
    conn.close()
    print(f"Base de datos '{DB_FILE}' creada con todas las tablas y datos de prueba.")

if __name__ == "__main__":
    setup_database()
