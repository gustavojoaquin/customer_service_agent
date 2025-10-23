# ================================================================
# setup_db.py — Base de datos de prueba para el asistente de vuelos
# ================================================================

import sqlite3
from datetime import datetime, timedelta

DB_FILE = "travel2.sqlite"

def setup_database():
    """Crea una base de datos SQLite pequeña de prueba con vuelos y usuarios."""

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # --- Crear tabla de usuarios ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            passenger_id TEXT PRIMARY KEY,
            name TEXT
        )
    """)

    # --- Crear tabla de vuelos ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flights (
            flight_id TEXT PRIMARY KEY,
            passenger_id TEXT,
            origin TEXT,
            destination TEXT,
            scheduled_departure TEXT,
            scheduled_arrival TEXT,
            actual_departure TEXT,
            actual_arrival TEXT,
            FOREIGN KEY(passenger_id) REFERENCES users(passenger_id)
        )
    """)

    # --- Insertar datos de prueba de usuarios ---
    users = [
        ("U1001", "Alice"),
        ("U1002", "Bob"),
        ("U1003", "Carlos"),
    ]
    cursor.executemany("INSERT OR REPLACE INTO users (passenger_id, name) VALUES (?, ?)", users)

    # --- Insertar datos de prueba de vuelos ---
    now = datetime.now()
    flights = [
        ("F001", "U1001", "Madrid", "Paris", now + timedelta(hours=2), now + timedelta(hours=4), now + timedelta(hours=2, minutes=5), now + timedelta(hours=4, minutes=10)),
        ("F002", "U1001", "Paris", "Berlin", now + timedelta(days=1, hours=3), now + timedelta(days=1, hours=5), None, None),
        ("F003", "U1002", "New York", "London", now + timedelta(hours=5), now + timedelta(hours=11), now + timedelta(hours=5, minutes=10), now + timedelta(hours=11, minutes=5)),
        ("F004", "U1003", "Tokyo", "Seoul", now + timedelta(hours=8), now + timedelta(hours=10), None, None),
    ]
    cursor.executemany("""
        INSERT OR REPLACE INTO flights (
            flight_id, passenger_id, origin, destination,
            scheduled_departure, scheduled_arrival,
            actual_departure, actual_arrival
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [(f[0], f[1], f[2], f[3], f[4].isoformat(), f[5].isoformat(), f[6].isoformat() if f[6] else None, f[7].isoformat() if f[7] else None) for f in flights])

    conn.commit()
    conn.close()
    print(f"Base de datos '{DB_FILE}' creada con datos de prueba.")

if __name__ == "__main__":
    setup_database()
