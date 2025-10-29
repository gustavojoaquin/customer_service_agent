"""Punto de entrada principal del bot"""
import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from config.settings import TELEGRAM_TOKEN
from handlers.telegram_handlers import start, handle_message, procesar_audio

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Inicia el bot de Telegram."""
    logger.info("🚀 Iniciando bot de Telegram...")
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Registrar handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, procesar_audio))
    
    logger.info("✅ Bot en marcha... esperando mensajes.")
    app.run_polling()


if __name__ == "__main__":
    main()