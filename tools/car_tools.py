from datetime import date, datetime
from typing import Optional, Union

from langchain_core.tools import tool
from config.database import get_db_connection


@tool
def search_car_rentals(
    location: Optional[str] = None,
    name: Optional[str] = None,
    price_tier: Optional[str] = None,
    start_date: Optional[Union[datetime, date]] = None,
    end_date: Optional[Union[datetime, date]] = None,
) -> list[dict]:
    """Busca alquileres de coches."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM car_rentals WHERE 1=1"
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
    column_names = [desc[0] for desc in cursor.description]
    conn.close()
    
    return [
        dict(zip(column_names, row)) for row in results
    ]

# Coches disponibles
@tool
def buscar_carros_rentados() -> list[dict]:
    """
    Busca todos los carros que están actualmente rentados/reservados (booked = true).
    
    Returns:
        Lista de todos los carros rentados con todos sus campos
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Solo carros rentados - PostgreSQL usa true/false en lugar de 1/0
    query = "SELECT * FROM car_rentals WHERE booked = true"
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    # Obtener nombres de columnas
    column_names = [desc[0] for desc in cursor.description]
    conn.close()
    
    return [
        dict(zip(column_names, row)) for row in results
    ]

@tool
def book_car_rental(rental_id: int) -> str:
    """Reserva un alquiler de coche por su ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE car_rentals SET booked = true WHERE id = %s", (rental_id,))
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Alquiler de coche {rental_id} reservado con éxito."
    conn.close()
    return f"No se encontró un alquiler de coche con ID {rental_id}."


@tool
def cancel_car_rental(rental_id: int) -> str:
    """Cancela una reserva de alquiler de coche por su ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE car_rentals SET booked = false WHERE id = %s", (rental_id,))
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Reserva de alquiler de coche {rental_id} cancelada con éxito."
    conn.close()
    return f"No se encontró un alquiler de coche con ID {rental_id}."

