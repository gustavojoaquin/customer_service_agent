import os
import uuid

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

from graph import graph

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN no está configurado en el archivo .env")

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
    chat_id = update.message.chat_id
    user_input = update.message.text

    if "thread_id" not in context.user_data:
        context.user_data["thread_id"] = str(uuid.uuid4())
        await update.message.reply_text(
            f"Iniciando nueva conversación. ID: {context.user_data['thread_id']}"
        )

    thread_id = context.user_data["thread_id"]

    config = {
        "configurable": {
            "passenger_id": "3442 587242",
            "thread_id": thread_id,
        }
    }

    events = graph.stream(
        {"messages": [HumanMessage(content=user_input)]}, config, stream_mode="values"
    )

    final_response = None
    for event in events:
        if "messages" in event:
            final_response = event["messages"][-1]

    snapshot = graph.get_state(config)
    if snapshot.next:
        await update.message.reply_text(
            "El agente quiere realizar una acción que modifica tus datos (ej. cambiar un vuelo). Aprobando automáticamente para esta demostración..."
        )

        events = graph.stream(None, config, stream_mode="values")
        for event in events:
            if "messages" in event:
                final_response = event["messages"][-1]

    if final_response and final_response.content:
        await update.message.reply_text(final_response.content)
    else:
        await update.message.reply_text("Acción procesada. ¿Necesitas algo más?")


def main():
    """Inicia el bot de Telegram."""
    print("Iniciando bot...")

    print("Generando diagrama del grafo...")
    generate_diagram()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot en marcha... esperando mensajes.")
    app.run_polling()


if __name__ == "__main__":
    main()
