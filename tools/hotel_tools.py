from datetime import date, datetime
from typing import Optional, Union

from langchain_core.tools import tool
from config.database import get_db_connection

@tool
def search_hotels(
    location: Optional[str] = None,
    name: Optional[str] = None,
    price_tier: Optional[str] = None,
    checkin_date: Optional[Union[datetime, date]] = None,
    checkout_date: Optional[Union[datetime, date]] = None,
) -> list[dict]:
    """Busca hoteles."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM hotels WHERE 1=1"
    params = []
    if location:
        query += " AND location LIKE %s"
        params.append(f"%{location}%")
    if name:
        query += " AND name LIKE %s"
        params.append(f"%{name}%")
    cursor.execute(query, params)
    results = cursor.fetchall()
    
    # Obtener nombres de columnas
    column_names = [column[0] for column in cursor.description]
    conn.close()
    
    return [
        dict(zip(column_names, row)) for row in results
    ]

@tool
def book_hotel(hotel_id: int) -> str:
    """Reserva un hotel por su ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE hotels SET booked = true WHERE id = %s", (hotel_id,))
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Hotel {hotel_id} reservado con éxito."
    conn.close()
    return f"No se encontró un hotel con ID {hotel_id}."

@tool
def cancel_hotel(hotel_id: int) -> str:
    """Cancela una reserva de hotel por su ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE hotels SET booked = false WHERE id = %s", (hotel_id,))
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Reserva de hotel {hotel_id} cancelada con éxito."
    conn.close()
    return f"No se encontró un hotel con ID {hotel_id}."