import os
import re
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


def clean_telegram_message(text: str) -> str:
    if not text:
        return text

    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)

    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"_(.*?)_", r"\1", text)

    text = re.sub(r"`(.*?)`", r"\1", text)

    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)

    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    return text


load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN no está configurado en el archivo .env")


def generate_diagram():
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
    chat_id = update.message.chat_id
    context.user_data["thread_id"] = str(uuid.uuid4())

    context.user_data["passenger_id"] = None

    await update.message.reply_text(
        f"👋 ¡Hola! Soy tu asistente de vuelos. Mi ID de conversación es: {context.user_data['thread_id']}\n\n"
        "Por favor, proporciona tu ID de pasajero o número de vuelo para continuar:"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text

    if "thread_id" not in context.user_data:
        context.user_data["thread_id"] = str(uuid.uuid4())

    thread_id = context.user_data["thread_id"]

    passenger_id = context.user_data.get("passenger_id", "pending_validation")
    config = {"configurable": {"passenger_id": passenger_id, "thread_id": thread_id}}

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

        if (
            "passenger_id" in context.user_data
            and context.user_data["passenger_id"] == "pending_validation"
        ):
            pass
    else:
        await update.message.reply_text("Acción procesada. ¿Necesitas algo más?")


def main():
    print("Iniciando bot...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot en marcha... esperando mensajes.")
    app.run_polling()


if __name__ == "__main__":
    main()
