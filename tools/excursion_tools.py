from langchain_core.tools import tool
from typing import Optional
from config.database import get_db_connection

@tool
def search_trip_recommendations(
    location: Optional[str] = None,
    name: Optional[str] = None,
    keywords: Optional[str] = None,
) -> list[dict]:
    """Busca recomendaciones de viajes y excursiones."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM trip_recommendations WHERE 1=1"
    params = []
    if location:
        query += " AND location LIKE %s"
        params.append(f"%{location}%")
    if name:
        query += " AND name LIKE %s"
        params.append(f"%{name}%")
    if keywords:
        # Implementar búsqueda por keywords si es necesario
        pass
    cursor.execute(query, params)
    results = cursor.fetchall()
    
    # Obtener nombres de columnas
    column_names = [desc[0] for desc in cursor.description]
    conn.close()
    
    return [
        dict(zip(column_names, row)) for row in results
    ]

@tool
def book_excursion(recommendation_id: int) -> str:
    """Reserva una excursión por su ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE trip_recommendations SET booked = true WHERE id = %s", (recommendation_id,)
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
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE trip_recommendations SET booked = false WHERE id = %s", (recommendation_id,)
    )
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return f"Reserva de excursión {recommendation_id} cancelada con éxito."
    conn.close()
    return f"No se encontró una excursión con ID {recommendation_id}."