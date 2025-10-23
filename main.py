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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["thread_id"] = str(uuid.uuid4())

    context.user_data["flight_id"] = None

    await update.message.reply_text(
        f"Bienvenido al asistente de vuelos. ID de sesión: {context.user_data['thread_id']}\n\n"
        "Por favor, ingrese su ID de vuelo para continuar:"
    )


from typing import cast


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text

    if context.user_data is None:
        context.user_data = {}

    if "thread_id" not in context.user_data:
        context.user_data["thread_id"] = str(uuid.uuid4())

    thread_id = context.user_data["thread_id"]

    flight_id = context.user_data.get("flight_id", "pending_validation")
    config = {"configurable": {"flight_id": flight_id, "thread_id": thread_id}}

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    from langchain_core.runnables import RunnableConfig
    runnable_config = cast(RunnableConfig, config)

    snapshot = graph.get_state(runnable_config)

    if not snapshot.values:
        state_input = {
            "messages": [HumanMessage(content=user_input)],
            "user_info": "",
            "flight_id": flight_id,
            "dialog_state": []
        }
    else:
        current_messages = snapshot.values.get("messages", [])
        state_input = {
            "messages": current_messages + [HumanMessage(content=user_input)],
            "user_info": snapshot.values.get("user_info", ""),
            "flight_id": flight_id,
            "dialog_state": snapshot.values.get("dialog_state", [])
        }

    from graph import State
    state_input_cast = cast(State, state_input)

    events = graph.stream(
        state_input_cast, runnable_config, stream_mode="values"
    )

    final_response = None
    for event in events:
        if "messages" in event:
            final_response = event["messages"][-1]

    if final_response and final_response.content:
        if "validado correctamente" in final_response.content.lower():
            try:
                import re
                flight_match = re.search(r'\b\d+\b', user_input)
                if flight_match:
                    validated_flight_id = flight_match.group()
                    context.user_data["flight_id"] = validated_flight_id
            except:
                pass

    snapshot = graph.get_state(runnable_config)

    interrupt_nodes = [
        "flight_sensitive_tools",
        "hotel_sensitive_tools",
        "car_rental_sensitive_tools",
        "excursion_sensitive_tools",
    ]
    if snapshot.next and any(node in snapshot.next for node in interrupt_nodes):
        await update.message.reply_text(
            "El agente solicita realizar una acción que modifica datos. Aprobando automáticamente para esta demostración..."
        )
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )

        events = graph.stream(None, runnable_config, stream_mode="values")
        for event in events:
            if "messages" in event:
                final_response = event["messages"][-1]

    if final_response and final_response.content:
        cleaned_response = clean_telegram_message(final_response.content)
        await update.message.reply_text(cleaned_response)
    else:
        await update.message.reply_text("Acción procesada. ¿Necesita asistencia adicional?")


def main():
    print("Iniciando bot...")
    token = cast(str, TELEGRAM_TOKEN)
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot en marcha... esperando mensajes.")
    app.run_polling()


if __name__ == "__main__":
    main()
