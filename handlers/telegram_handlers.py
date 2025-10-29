"""Handlers de Telegram (start, mensajes de texto, voz)"""
import uuid
from io import BytesIO
from types import SimpleNamespace

from telegram import Update
from telegram.ext import ContextTypes
from langchain_core.messages import HumanMessage
from elevenlabs import ElevenLabs

from config.settings import ELEVEN_API_KEY
from graph.travel_graph import graph
from .utils import (
    clean_telegram_message, 
    get_or_create_thread_id, 
    archive_conversation,
    get_user_conversations
)

from config.database import get_db_connection

# Cliente de ElevenLabs
client = ElevenLabs(api_key=ELEVEN_API_KEY)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /start."""
    telegram_user_id = update.effective_user.id
    
    # ✅ Obtener thread_id persistente
    thread_id, passenger_id = get_or_create_thread_id(telegram_user_id)
    
    # Guardar en context para esta sesión (opcional, para caché)
    context.user_data["thread_id"] = thread_id
    context.user_data["passenger_id"] = passenger_id
    
    await update.message.reply_text(
        f"👋 ¡Hola! Soy tu asistente de vuelos.\n"
        f"Tu ID de conversación es: {thread_id}\n\n"
        f"¿Cómo puedo ayudarte hoy?"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes de texto del usuario."""
    user_input = update.message.text
    telegram_user_id = update.effective_user.id

    # ✅ Obtener thread_id persistente (no depender de context.user_data)
    thread_id, passenger_id = get_or_create_thread_id(telegram_user_id)
    
    # Guardar en context para esta sesión
    context.user_data["thread_id"] = thread_id
    context.user_data["passenger_id"] = passenger_id
    
    # ✅ Configuración con passenger_id real del usuario
    config = {
        "configurable": {
            "passenger_id": passenger_id,  # ← Ahora usa el ID real
            "thread_id": thread_id
        }
    }

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    # Stream del grafo
    events = graph.stream(
        {"messages": [HumanMessage(content=user_input)]},
        config,
        stream_mode="values"
    )

    final_response = None
    for event in events:
        if "messages" in event:
            final_response = event["messages"][-1]

    # Manejo de interrupciones (sensitive tools)
    snapshot = graph.get_state(config)
    interrupt_nodes = [
        "flight_sensitive_tools",
        "hotel_sensitive_tools",
        "car_rental_sensitive_tools",
        "excursion_sensitive_tools",
    ]

    if snapshot.next and any(node in snapshot.next for node in interrupt_nodes):
        await update.message.reply_text(
            "⚠️ El agente quiere realizar una acción sensible (reserva/cancelación). "
            "Aprobando automáticamente para esta demo..."
        )
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )

        # Continuar con la ejecución
        events = graph.stream(None, config, stream_mode="values")
        for event in events:
            if "messages" in event:
                final_response = event["messages"][-1]

    # Responder al usuario
    if final_response and final_response.content:
        cleaned_response = clean_telegram_message(final_response.content)
        await update.message.reply_text(cleaned_response)
    else:
        await update.message.reply_text("✅ Acción procesada. ¿Necesitas algo más?")


async def procesar_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa mensajes de voz con ElevenLabs."""
    try:
        voice_file = await update.message.voice.get_file()
        audio_bytes = await voice_file.download_as_bytearray()
        audio_stream = BytesIO(audio_bytes)

        # Transcripción
        result = client.speech_to_text.convert(
            model_id="scribe_v1",
            file=("audio.ogg", audio_stream)
        )

        text = result.text.strip()

        # Simular un mensaje de texto
        fake_message = SimpleNamespace(
            text=text,
            chat=update.message.chat,
            from_user=update.message.from_user,
            reply_text=update.message.reply_text,
        )

        fake_update = SimpleNamespace(
            message=fake_message,
            effective_chat=update.effective_chat,
            effective_user=update.effective_user,
        )

        # Reutilizar el handler de texto
        await handle_message(fake_update, context)

    except Exception as e:
        await update.message.reply_text(
            f"⚠️ Disculpa, estoy teniendo problemas para procesar el audio. "
            f"¿Podrías intentarlo de nuevo más tarde o enviarme un mensaje de texto?"
        )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reinicia la conversación del usuario (archiva la anterior)."""
    telegram_user_id = update.effective_user.id
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Obtener thread_id actual
    cursor.execute(
        "SELECT current_thread_id FROM users WHERE telegram_user_id = %s",
        (telegram_user_id,)
    )
    result = cursor.fetchone()
    
    if result and result[0]:
        old_thread_id = result[0]
        
        # 2. Archivar conversación anterior
        archive_conversation(telegram_user_id, old_thread_id)
        
        await update.message.reply_text(
            f"📦 Conversación anterior archivada: {old_thread_id[:8]}..."
        )
    
    # 3. Generar nuevo thread_id
    new_thread_id = str(uuid.uuid4())
    
    # 4. Crear nueva conversación
    cursor.execute(
        "INSERT INTO conversations (telegram_user_id, thread_id) VALUES (%s, %s)",
        (telegram_user_id, new_thread_id)
    )
    
    # 5. Actualizar current_thread_id del usuario
    cursor.execute(
        "UPDATE users SET current_thread_id = %s WHERE telegram_user_id = %s",
        (new_thread_id, telegram_user_id)
    )
    
    conn.commit()
    conn.close()
    
    # Actualizar context
    context.user_data["thread_id"] = new_thread_id
    
    await update.message.reply_text(
        f"🔄 Nueva conversación iniciada\n"
        f"ID: {new_thread_id}"
    )


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el historial de conversaciones del usuario."""
    telegram_user_id = update.effective_user.id
    
    conversations = get_user_conversations(telegram_user_id, limit=10)
    
    if not conversations:
        await update.message.reply_text("No tienes conversaciones previas.")
        return
    
    # Formatear respuesta
    message = "📜 **Historial de Conversaciones**\n\n"
    
    for i, conv in enumerate(conversations, 1):
        status = "🟢 Activa" if conv["is_active"] else "⚪ Archivada"
        thread_short = conv["thread_id"][:8]
        started = conv["started_at"].strftime("%d/%m/%Y %H:%M")
        
        message += f"{i}. {status}\n"
        message += f"   ID: {thread_short}...\n"
        message += f"   Inicio: {started}\n"
        
        if conv["ended_at"]:
            ended = conv["ended_at"].strftime("%d/%m/%Y %H:%M")
            message += f"   Fin: {ended}\n"
        
        message += "\n"
    
    await update.message.reply_text(clean_telegram_message(message))

"""""""""

#Manejo de callbacks para confirmación de reset (HABILITAR EN MAIN.PY)


from telegram.ext import CallbackQueryHandler

app.add_handler(CommandHandler("reset", reset))
app.add_handler(CallbackQueryHandler(handle_reset_callback, pattern="^(confirm_reset|cancel_reset)$"))

"""""""""