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
    
    # Buscar usuario existente
    cursor.execute(
        "SELECT thread_id, passenger_id FROM users WHERE telegram_user_id = %s",
        (telegram_user_id,)
    )
    result = cursor.fetchone()
    
    if result:
        # Usuario existente - actualizar last_active
        thread_id, passenger_id = result
        cursor.execute(
            "UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE telegram_user_id = %s",
            (telegram_user_id,)
        )
        conn.commit()
        conn.close()
        return thread_id, passenger_id
    else:
        # Usuario nuevo - crear registro
        thread_id = str(uuid.uuid4())
        passenger_id = f"TG_{telegram_user_id}"  # Usar Telegram ID como passenger_id
        
        cursor.execute(
            "INSERT INTO users (telegram_user_id, thread_id, passenger_id) VALUES (%s, %s, %s)",
            (telegram_user_id, thread_id, passenger_id)
        )
        conn.commit()
        conn.close()
        return thread_id, passenger_id