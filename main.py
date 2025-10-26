import os
import uuid
import re
import socket
import asyncio
from elevenlabs import ElevenLabs

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from setup_db import setup_database

from graph import graph


from types import SimpleNamespace

from io import BytesIO
from types import SimpleNamespace
from telegram import Update
from telegram.ext import ContextTypes


async def start_simple_server(host='127.0.0.1', port=65432):
    """Start a simple TCP server that listens for connections and sends a greeting."""
    server = await asyncio.start_server(
        handle_client, host, port
    )

    addr = server.sockets[0].getsockname()
    print(f'Server listening on {addr}')

    async with server:
        await server.serve_forever()


async def handle_client(reader, writer):
    """Handle incoming client connections."""
    addr = writer.get_extra_info('peername')
    print(f'Connected by {addr}')

    # Send greeting message
    writer.write(b'Hello from Customer Service Agent Bot\n')
    await writer.drain()

    # Close the connection
    writer.close()
    await writer.wait_closed()
    print(f'Connection closed with {addr}')


def clean_telegram_message(text: str) -> str:
    """
    Clean Markdown formatting and make text Telegram-compatible.
    Telegram doesn't support Markdown by default, so we need to remove formatting.
    """
    if not text:
        return text

    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)

    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)

    text = re.sub(r'`(.*?)`', r'\1', text)

    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)

    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN no está configurado en el archivo .env")
if not ELEVEN_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY no está configurado en el archivo .env")

client = ElevenLabs(api_key=ELEVEN_API_KEY)


def generate_diagram():
    """Generate a PNG diagram of the LangGraph workflow."""
    try:
        from langgraph.graph import StateGraph

        diagram_path = "langgraph_diagram.png"

        from IPython.display import Image, display

        png_data = graph.get_graph().draw_mermaid_png()

        with open(diagram_path, "wb") as f:
            f.write(png_data)

        print(f"Diagrama generado exitosamente: {diagram_path}")
        return True
    except Exception as e:
        print(f"No se pudo generar el diagrama: {e}")
        print("Instala las dependencias necesarias: pip install pygraphviz")
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /start."""
    chat_id = update.message.chat_id
    context.user_data["thread_id"] = str(uuid.uuid4())
    await update.message.reply_text(
        f"👋 ¡Hola! Soy tu asistente de vuelos. Mi ID de conversación es: {context.user_data['thread_id']}\n\n¿Cómo puedo ayudarte hoy?"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los mensajes del usuario y los procesa con el grafo."""
    user_input = update.message.text

    if "thread_id" not in context.user_data:
        context.user_data["thread_id"] = str(uuid.uuid4())
        await update.message.reply_text(
            f"Iniciando nueva conversación. ID: {context.user_data['thread_id']}"
        )

    thread_id = context.user_data["thread_id"]
    config = {"configurable": {"passenger_id": "3442 587242", "thread_id": thread_id}}

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    events = graph.stream(
        {"messages": [HumanMessage(content=user_input)]}, config, stream_mode="values"
    )

    final_response = None
    for event in events:
        if "messages" in event:
            final_response = event["messages"][-1]

    snapshot = graph.get_state(config)

    interrupt_nodes = [
        "flight_sensitive_tools",
        "hotel_sensitive_tools",
        "car_rental_sensitive_tools",
        "excursion_sensitive_tools",
    ]
    if snapshot.next and any(node in snapshot.next for node in interrupt_nodes):
        await update.message.reply_text(
            "El agente quiere realizar una acción que modifica datos (ej. hacer una reserva). Aprobando automáticamente para esta demo..."
        )
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )

        events = graph.stream(None, config, stream_mode="values")
        for event in events:
            if "messages" in event:
                final_response = event["messages"][-1]

    if final_response and final_response.content:
        cleaned_response = clean_telegram_message(final_response.content)
        await update.message.reply_text(cleaned_response)
    else:
        await update.message.reply_text("Acción procesada. ¿Necesitas algo más?")



# ---------- Procesar audios (voz) ----------
async def procesar_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        voice_file = await update.message.voice.get_file()
        audio_bytes = await voice_file.download_as_bytearray()
        audio_stream = BytesIO(audio_bytes)


        # Transcripción directa desde memoria
        result = client.speech_to_text.convert(
            model_id="scribe_v1",
            file=("audio.ogg", audio_stream)
        )

        text = result.text.strip()

        # Crear un objeto tipo Update simulado con todos los campos requeridos
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

        # Llamar al mismo manejador de texto
        await handle_message(fake_update, context)

    except Exception as e:
        await update.message.reply_text(f"⚠️ Disculpa estoy teniendo problemas para procesar el audio , podrias intentarlo de nuevo mas tarde.O si gustas enviarme un mensaje de texto")



async def main_async():
    """Inicia el bot de Telegram y el servidor TCP de forma asíncrona."""
    print("Configurando la base de datos...")
    setup_database()

    print("Iniciando bot y servidor TCP...")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, procesar_audio))

    await asyncio.gather(
        app.run_polling(),
        start_simple_server()
    )

def main():
    """Inicia el bot de Telegram."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
