# 🤖 Handlers Module - Documentación

Este módulo contiene todos los handlers de Telegram y utilidades para procesar mensajes del usuario.

## 🏗️ Estructura

```
handlers/
├── telegram_handlers.py     # Handlers de comandos y mensajes
├── utils.py                 # Funciones auxiliares
└── README.md                # Este archivo
```

---

## 📄 Descripción de Archivos

### `utils.py`
Funciones auxiliares para procesamiento de mensajes.

#### `clean_telegram_message(text: str) -> str`
Limpia el formato Markdown de las respuestas del LLM para hacerlas compatibles con Telegram.

**¿Por qué es necesario?**
- Los LLMs suelen usar Markdown (**, *, _, `, etc.)
- Telegram **no** soporta Markdown por defecto en mensajes plain text
- El formato puede verse roto o confuso para el usuario

**Transformaciones:**
```python
# Entrada:
"**Hola** mundo, aquí está tu _vuelo_: `AA100`"

# Salida:
"Hola mundo, aquí está tu vuelo: AA100"
```

**Reglas de limpieza:**
1. `**texto**` → `texto` (negritas)
2. `*texto*` → `texto` (cursivas)
3. `_texto_` → `texto` (cursivas alt)
4. `` `texto` `` → `texto` (código inline)
5. `[texto](url)` → `texto` (links)
6. Múltiples saltos de línea → máximo 2

**Uso:**
```python
from handlers.utils import clean_telegram_message

raw_response = "**Reserva confirmada!** Tu vuelo es `AA100`"
clean_response = clean_telegram_message(raw_response)
await update.message.reply_text(clean_response)
```

---

### `telegram_handlers.py`
Handlers principales para interactuar con Telegram.

## 📱 Handlers Disponibles

### 1. `start(update: Update, context: ContextTypes.DEFAULT_TYPE)`
Handler para el comando `/start`.

**Comportamiento:**
1. Genera un `thread_id` único para la conversación
2. Lo guarda en `context.user_data`
3. Envía mensaje de bienvenida

**Código:**
```python
@CommandHandler("start")
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["thread_id"] = str(uuid.uuid4())
    await update.message.reply_text(
        f"👋 ¡Hola! Soy tu asistente de vuelos.\n"
        f"Mi ID de conversación es: {context.user_data['thread_id']}\n\n"
        f"¿Cómo puedo ayudarte hoy?"
    )
```

**Ejemplo de uso:**
```
Usuario: /start

Bot: 👋 ¡Hola! Soy tu asistente de vuelos.
     Mi ID de conversación es: a1b2c3d4-5678-90ef-ghij-klmnopqrstuv
     
     ¿Cómo puedo ayudarte hoy?
```

---

### 2. `handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE)`
Handler principal para mensajes de texto.

**Flujo completo:**

#### Paso 1: Inicializar thread_id
```python
if "thread_id" not in context.user_data:
    context.user_data["thread_id"] = str(uuid.uuid4())
    await update.message.reply_text(
        f"Iniciando nueva conversación. ID: {context.user_data['thread_id']}"
    )
```

**¿Por qué?**
- Si el usuario no usó `/start`, crear thread_id automáticamente
- Asegura que siempre hay un ID de conversación

#### Paso 2: Configurar context
```python
thread_id = context.user_data["thread_id"]
config = {
    "configurable": {
        "passenger_id": DEFAULT_PASSENGER_ID,
        "thread_id": thread_id
    }
}
```

**Campos del config:**
- `passenger_id`: Identifica al usuario (en producción, obtener del sistema de auth)
- `thread_id`: Identifica la conversación (para persistencia)

#### Paso 3: Mostrar "typing..."
```python
await context.bot.send_chat_action(
    chat_id=update.effective_chat.id,
    action="typing"
)
```

**¿Por qué es importante?**
- Indica al usuario que el bot está procesando
- Mejora la UX (experiencia de usuario)
- Telegram muestra el indicador "..." en el chat

#### Paso 4: Ejecutar el grafo
```python
events = graph.stream(
    {"messages": [HumanMessage(content=user_input)]},
    config,
    stream_mode="values"
)

final_response = None
for event in events:
    if "messages" in event:
        final_response = event["messages"][-1]
```

**¿Qué hace `stream`?**
- Ejecuta el grafo paso a paso
- Cada `event` es un nodo ejecutado
- `stream_mode="values"` retorna el estado completo en cada paso
- El último mensaje es la respuesta del LLM

#### Paso 5: Manejar interrupciones (sensitive tools)
```python
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
    
    # Continuar ejecución
    events = graph.stream(None, config, stream_mode="values")
    for event in events:
        if "messages" in event:
            final_response = event["messages"][-1]
```

**¿Qué es una interrupción?**
- El grafo se pausa antes de ejecutar un nodo sensible
- Permite confirmar con el usuario antes de modificar datos
- `snapshot.next` contiene los nodos que se ejecutarán a continuación

**En producción:**
- Reemplazar "aprobación automática" con confirmación real del usuario
- Ejemplo: "¿Confirmas cancelar el vuelo AA100? (Sí/No)"

#### Paso 6: Responder al usuario
```python
if final_response and final_response.content:
    cleaned_response = clean_telegram_message(final_response.content)
    await update.message.reply_text(cleaned_response)
else:
    await update.message.reply_text("✅ Acción procesada. ¿Necesitas algo más?")
```

---

### 3. `procesar_audio(update: Update, context: ContextTypes.DEFAULT_TYPE)`
Handler para mensajes de voz (voice notes).

**Flujo:**

#### Paso 1: Descargar el audio
```python
voice_file = await update.message.voice.get_file()
audio_bytes = await voice_file.download_as_bytearray()
audio_stream = BytesIO(audio_bytes)
```

**Formato del audio:**
- Telegram envía voice notes en formato `.ogg` (Opus codec)
- Se descarga como bytes en memoria (no se guarda en disco)

#### Paso 2: Transcribir con ElevenLabs
```python
result = client.speech_to_text.convert(
    model_id="scribe_v1",
    file=("audio.ogg", audio_stream)
)
text = result.text.strip()
```

**¿Por qué ElevenLabs?**
- API simple y rápida
- Soporta múltiples idiomas
- Buena precisión en español
- Alternativas: Whisper (OpenAI), Google Speech-to-Text

#### Paso 3: Simular mensaje de texto
```python
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

await handle_message(fake_update, context)
```

**¿Por qué simular?**
- Reutilizar el handler de texto existente
- Evitar duplicar lógica
- El flujo es idéntico después de la transcripción

#### Paso 4: Manejo de errores
```python
except Exception as e:
    await update.message.reply_text(
        "⚠️ Disculpa, estoy teniendo problemas para procesar el audio. "
        "¿Podrías intentarlo de nuevo más tarde o enviarme un mensaje de texto?"
    )
```

**Errores comunes:**
- Audio muy corto (< 1 segundo)
- Audio muy largo (> 60 segundos en free tier)
- Ruido de fondo excesivo
- Idioma no soportado

---

## 🔄 Flujo Completo de una Conversación

### Ejemplo: Reservar un vuelo

```
1. Usuario: /start
   Bot: 👋 ¡Hola! Soy tu asistente de vuelos...
   [Se crea thread_id: abc-123]

2. Usuario: "Quiero reservar un vuelo a París"
   [typing...]
   Bot: "¿Para cuándo necesitas volar a París?"
   
   Estado del grafo:
   - primary_assistant → ToFlightBookingAssistant
   - enter_flight_assistant
   - flight_assistant

3. Usuario: "Para el 1 de noviembre"
   [typing...]
   Bot: "He encontrado 3 vuelos disponibles:
        1. AA100 - Salida 10:00 - €150
        2. BA200 - Salida 14:00 - €180
        ..."
   
   Estado del grafo:
   - flight_assistant → search_flights (safe tool)

4. Usuario: "Reserva el vuelo AA100"
   Bot: "⚠️ El agente quiere realizar una reserva. Aprobando..."
   [typing...]
   Bot: "Para completar la reserva necesito tu nombre y email"
   
   Estado del grafo:
   - flight_assistant → register_new_flight (sensitive tool)
   - PAUSA en interrupt_before
   - Continúa después de aprobación

5. Usuario: "Juan Pérez, juan@example.com"
   [typing...]
   Bot: "¡Vuelo registrado con éxito!
        Vuelo: AA100
        Pasajero: Juan Pérez
        Ticket: T123456
        ..."
   
   Estado del grafo:
   - flight_assistant → CompleteOrEscalate
   - leave_skill
   - Regresa a primary_assistant

6. Usuario: "Gracias!"
   Bot: "¡De nada! ¿Necesitas ayuda con algo más?"
```

---

## 🎯 Context de Telegram

### `context.user_data`
Diccionario persistente por usuario durante la sesión del bot.

```python
# Guardar datos
context.user_data["thread_id"] = "abc-123"
context.user_data["last_search"] = {...}

# Leer datos
thread_id = context.user_data.get("thread_id")
```

**¿Qué se persiste?**
- Solo durante la ejecución del bot
- Si el bot se reinicia, se pierde
- Para persistencia real, usar PostgreSQL (checkpointer)

### `update.message`
Contiene información del mensaje del usuario.

```python
update.message.text          # Contenido del mensaje
update.message.from_user     # Información del usuario
update.message.chat          # Información del chat
update.message.voice         # Si es mensaje de voz
```

---

## 🔧 Configuración en `main.py`

```python
from handlers.telegram_handlers import start, handle_message, procesar_audio

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# Registrar handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(MessageHandler(filters.VOICE, procesar_audio))
```

**Filtros:**
- `filters.TEXT`: Solo mensajes de texto
- `~filters.COMMAND`: Excluir comandos (ej: /start)
- `filters.VOICE`: Solo mensajes de voz

---

## 🚀 Mejoras Futuras

### 1. Confirmación real de acciones sensibles
```python
# En lugar de aprobar automáticamente
await update.message.reply_text(
    "¿Confirmas cancelar el vuelo AA100?",
    reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Sí", callback_data="confirm_cancel")],
        [InlineKeyboardButton("❌ No", callback_data="cancel_action")]
    ])
)
```

### 2. Soporte para imágenes
```python
@MessageHandler(filters.PHOTO)
async def handle_photo(update, context):
    # Extraer texto con OCR
    # Procesar solicitud
    pass
```

### 3. Comandos adicionales
```python
@CommandHandler("mybookings")
async def my_bookings(update, context):
    # Mostrar reservas del usuario
    pass

@CommandHandler("help")
async def help_command(update, context):
    # Mostrar comandos disponibles
    pass
```

### 4. Rate limiting
```python
from functools import wraps
from time import time

user_last_request = {}

def rate_limit(seconds=2):
    def decorator(func):
        @wraps(func)
        async def wrapper(update, context):
            user_id = update.effective_user.id
            now = time()
            
            if user_id in user_last_request:
                if now - user_last_request[user_id] < seconds:
                    await update.message.reply_text("⚠️ Por favor espera un momento")
                    return
            
            user_last_request[user_id] = now
            return await func(update, context)
        return wrapper
    return decorator

@rate_limit(seconds=3)
async def handle_message(update, context):
    # ...
```

---

## ⚠️ Consideraciones Importantes

1. **Error handling**: Siempre usar try/except para capturar errores
2. **Logging**: Loggear mensajes importantes para debugging
3. **Thread ID único**: Cada conversación debe tener su propio ID
4. **Typing indicator**: Siempre mostrar al procesar mensajes largos
5. **Mensajes claros**: Respuestas simples y directas para el usuario
6. **Seguridad**: Validar permisos antes de ejecutar acciones sensibles

---

## 📚 Referencias

- [python-telegram-bot Documentation](https://docs.python-telegram-bot.org/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [ElevenLabs API](https://elevenlabs.io/docs/api-reference/speech-to-text)