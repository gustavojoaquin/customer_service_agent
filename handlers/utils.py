"""Funciones auxiliares para Telegram"""
import re
import uuid
from config.database import get_db_connection

def clean_telegram_message(text: str) -> str:
    """
    Limpia formato Markdown para hacerlo compatible con Telegram.
    """
    if not text:
        return text

    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()





def get_or_create_thread_id(telegram_user_id: int) -> tuple[str, str]:
    """
    Obtiene o crea el thread_id para un usuario de Telegram.
    
    Returns:
        tuple: (thread_id, passenger_id)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Buscar usuario existente
    cursor.execute(
        "SELECT current_thread_id, passenger_id FROM users WHERE telegram_user_id = %s",
        (telegram_user_id,)
    )
    user_result = cursor.fetchone()
    
    if user_result and user_result[0]:
        # Usuario existe y tiene conversación activa
        thread_id, passenger_id = user_result
        
        # Actualizar last_active
        cursor.execute(
            "UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE telegram_user_id = %s",
            (telegram_user_id,)
        )
        conn.commit()
        conn.close()
        return thread_id, passenger_id
    
    # 2. Usuario nuevo o necesita nueva conversación
    thread_id = str(uuid.uuid4())
    
    if user_result:
        # Usuario existe pero no tiene conversación activa
        passenger_id = user_result[1]
    else:
        # Usuario completamente nuevo
        passenger_id = f"TG_{telegram_user_id}"
        
        # Crear registro de usuario
        cursor.execute(
            "INSERT INTO users (telegram_user_id, passenger_id, current_thread_id) VALUES (%s, %s, %s)",
            (telegram_user_id, passenger_id, thread_id)
        )
    
    # 3. Crear nueva conversación
    cursor.execute(
        "INSERT INTO conversations (telegram_user_id, thread_id) VALUES (%s, %s)",
        (telegram_user_id, thread_id)
    )
    
    # 4. Actualizar current_thread_id del usuario
    cursor.execute(
        "UPDATE users SET current_thread_id = %s, last_active = CURRENT_TIMESTAMP WHERE telegram_user_id = %s",
        (thread_id, telegram_user_id)
    )
    
    conn.commit()
    conn.close()
    return thread_id, passenger_id


def archive_conversation(telegram_user_id: int, old_thread_id: str):
    """
    Archiva una conversación (marca como inactiva).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """UPDATE conversations 
           SET is_active = FALSE, ended_at = CURRENT_TIMESTAMP 
           WHERE telegram_user_id = %s AND thread_id = %s""",
        (telegram_user_id, old_thread_id)
    )
    
    conn.commit()
    conn.close()


def get_user_conversations(telegram_user_id: int, limit: int = 10) -> list[dict]:
    """
    Obtiene el historial de conversaciones de un usuario.
    
    Returns:
        Lista de conversaciones con formato:
        [
            {
                "thread_id": "abc-123",
                "started_at": "2025-10-29 10:00:00",
                "ended_at": "2025-10-29 12:00:00",
                "is_active": False
            },
            ...
        ]
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """SELECT thread_id, started_at, ended_at, is_active 
           FROM conversations 
           WHERE telegram_user_id = %s 
           ORDER BY started_at DESC 
           LIMIT %s""",
        (telegram_user_id, limit)
    )
    
    results = cursor.fetchall()
    conn.close()
    
    conversations = []
    for row in results:
        conversations.append({
            "thread_id": row[0],
            "started_at": row[1],
            "ended_at": row[2],
            "is_active": row[3]
        })
    
    return conversations