"""Configuración centralizada de tokens y settings"""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN no está configurado en .env")

# ElevenLabs
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not ELEVEN_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY no está configurado en .env")

# Passenger ID por defecto (puedes moverlo luego)
DEFAULT_PASSENGER_ID = "3442 587242"