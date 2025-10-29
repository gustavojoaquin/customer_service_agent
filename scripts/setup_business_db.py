"""
Crea todas las tablas de negocio: flights, hotels, cars, excursions
Ejecutar UNA SOLA VEZ al iniciar el proyecto.
"""
from datetime import datetime, timedelta
from psycopg2.extras import execute_batch
from config.database import get_db_connection
def setup_business_tables():
    """Crea tablas de negocio y datos de prueba"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # --- Crear tablas ---
    # Tabla de usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_user_id BIGINT PRIMARY KEY,
            passenger_id TEXT NOT NULL,
            current_thread_id TEXT,  -- Conversación actual activa
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabla de historial de conversaciones
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id SERIAL PRIMARY KEY,
            telegram_user_id BIGINT NOT NULL,
            thread_id TEXT NOT NULL UNIQUE,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id)
        )
    """)

    # Índices para búsquedas rápidas
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_user 
        ON conversations(telegram_user_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_active 
        ON conversations(telegram_user_id, is_active)
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_no TEXT PRIMARY KEY,
            book_ref TEXT,
            passenger_id TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flights (
            flight_id TEXT PRIMARY KEY,
            flight_no TEXT,
            departure_airport TEXT,
            arrival_airport TEXT,
            scheduled_departure TIMESTAMP,
            scheduled_arrival TIMESTAMP
        )
    """)

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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS car_rentals (
            id SERIAL PRIMARY KEY,
            name TEXT,
            location TEXT,
            price_tier TEXT,
            booked BOOLEAN DEFAULT false
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hotels (
            id SERIAL PRIMARY KEY,
            name TEXT,
            location TEXT,
            price_tier TEXT,
            booked BOOLEAN DEFAULT false
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trip_recommendations (
            id SERIAL PRIMARY KEY,
            name TEXT,
            location TEXT,
            booked BOOLEAN DEFAULT false
        )
    """)

    # --- Insertar datos de prueba ---
    tickets = [
        ("T001", "BR001", "3442 587242"),
        ("T002", "BR002", "3442 587242"),
        ("T003", "BR003", "U1002"),
        ("T004", "BR004", "U1003"),
    ]
    execute_batch(cursor, "INSERT INTO tickets (ticket_no, book_ref, passenger_id) VALUES (%s, %s, %s) ON CONFLICT (ticket_no) DO NOTHING", tickets)

    now = datetime.now()
    flights = [
        ("F001", "AA100", "MAD", "CDG", now + timedelta(hours=2), now + timedelta(hours=4)),
        ("F002", "BA200", "CDG", "TXL", now + timedelta(days=1, hours=3), now + timedelta(days=1, hours=5)),
        ("F003", "UA300", "JFK", "LHR", now + timedelta(hours=5), now + timedelta(hours=11)),
        ("F004", "KE400", "NRT", "ICN", now + timedelta(hours=8), now + timedelta(hours=10)),
    ]
    execute_batch(cursor, "INSERT INTO flights (flight_id, flight_no, departure_airport, arrival_airport, scheduled_departure, scheduled_arrival) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (flight_id) DO NOTHING", flights)

    ticket_flights = [
        ("T001", "F001", "Economy"),
        ("T002", "F002", "Business"),
        ("T003", "F003", "Economy"),
        ("T004", "F004", "First"),
    ]
    execute_batch(cursor, "INSERT INTO ticket_flights (ticket_no, flight_id, fare_conditions) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", ticket_flights)

    boarding_passes = [
        ("T001", "F001", "12A"),
        ("T002", "F002", "1B"),
        ("T003", "F003", "24C"),
        ("T004", "F004", "2A"),
    ]
    execute_batch(cursor, "INSERT INTO boarding_passes (ticket_no, flight_id, seat_no) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", boarding_passes)

    car_rentals = [
        ("Hertz", "Madrid Airport", "Premium", False),
        ("Avis", "Paris CDG", "Standard", False),
        ("Europcar", "Berlin Tegel", "Luxury", False),
        ("Budget", "London Heathrow", "Economy", False),
    ]
    execute_batch(cursor, "INSERT INTO car_rentals (name, location, price_tier, booked) VALUES (%s, %s, %s, %s)", car_rentals)

    hotels = [
        ("Hotel Ritz", "Madrid", "Luxury", False),
        ("Hotel Plaza", "Paris", "Premium", False),
        ("Hotel Berlin", "Berlin", "Standard", False),
        ("Hotel Savoy", "London", "Luxury", False),
    ]
    execute_batch(cursor, "INSERT INTO hotels (name, location, price_tier, booked) VALUES (%s, %s, %s, %s)", hotels)

    trip_recommendations = [
        ("Tour del Louvre", "Paris", False),
        ("Paseo por el Retiro", "Madrid", False),
        ("Visita al Muro de Berlín", "Berlin", False),
        ("Tour del Big Ben", "London", False),
    ]
    execute_batch(cursor, "INSERT INTO trip_recommendations (name, location, booked) VALUES (%s, %s, %s)", trip_recommendations)

    conn.commit()
    conn.close()
    print("✅ Tablas de negocio creadas correctamente")

if __name__ == "__main__":
    setup_business_tables()