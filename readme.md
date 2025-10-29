# ✈️ Travel Assistant Bot

Bot de Telegram multi-agente para gestionar reservas de vuelos, hoteles, alquiler de coches y excursiones usando LangGraph y PostgreSQL.

## 🚀 Características

- 🤖 **Multi-agente inteligente** con LangGraph
- ✈️ **Gestión de vuelos**: Búsqueda, reserva, cambios y cancelaciones
- 🏨 **Reservas de hoteles**: Búsqueda y gestión de alojamiento
- 🚗 **Alquiler de coches**: Búsqueda y reservas de vehículos
- 🌍 **Excursiones**: Recomendaciones y reservas de tours
- 💾 **Persistencia con PostgreSQL**: Conversaciones guardadas automáticamente
- 🎙️ **Soporte de voz**: Transcripción con ElevenLabs
- 🔒 **Interrupciones seguras**: Confirmación antes de acciones sensibles

---

## 📁 Estructura del Proyecto

```
travel_assistant_bot/
│
├── main.py                           # Punto de entrada del bot
├── .env                              # Variables de entorno (no subir a Git)
├── .env.example                      # Template de variables
├── requirements.txt                  # Dependencias Python
├── README.md                         # Este archivo
│
├── config/                           # Configuración centralizada
│   ├── database.py                   # Conexiones a PostgreSQL
│   ├── settings.py                   # Variables de entorno y tokens
│   └── README.md                     # Documentación del módulo
│
├── scripts/                          # Scripts de setup
│   ├── setup_business_db.py          # Crea tablas de negocio
│   └── setup_langgraph_memory.py     # Crea tablas de memoria LangGraph
│
├── tools/                            # Herramientas (Tools) de LangChain
│   ├── base.py                       # Funciones helper comunes
│   ├── flights_tools.py              # Tools de vuelos
│   ├── hotel_tools.py                # Tools de hoteles
│   ├── car_tools.py                  # Tools de alquiler de coches
│   ├── excursion_tools.py            # Tools de excursiones
│   ├── policy_tools.py               # Consultas de políticas
│   └── README.md                     # Documentación del módulo
│
├── graph/                            # Grafo de conversación multi-agente
│   ├── state.py                      # Definición del State y modelos
│   ├── nodes.py                      # Nodos auxiliares
│   ├── routing.py                    # Lógica de enrutamiento
│   ├── travel_graph.py               # Construcción del grafo
│   ├── README.md                     # Documentación del módulo
│   └── agents/                       # Agentes especializados
│       ├── primary.py                # Asistente principal
│       ├── flights.py                # Asistente de vuelos
│       ├── hotels.py                 # Asistente de hoteles
│       ├── cars.py                   # Asistente de coches
│       └── excursions.py             # Asistente de excursiones
│
└── handlers/                         # Handlers de Telegram
    ├── telegram_handlers.py          # Handlers de comandos y mensajes
    ├── utils.py                      # Funciones auxiliares
    └── README.md                     # Documentación del módulo
```

---

## 🛠️ Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/travel-assistant-bot.git
cd travel-assistant-bot
```

### 2. Crear entorno virtual
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar PostgreSQL

#### Opción A: Local
```bash
# Instalar PostgreSQL
# Crear base de datos
psql -U postgres
CREATE DATABASE travel_db;
\q
```

#### Opción B: Docker
```bash
docker run --name postgres-travel \
  -e POSTGRES_PASSWORD=mypassword \
  -e POSTGRES_DB=travel_db \
  -p 5432:5432 \
  -d postgres:15
```

### 5. Configurar variables de entorno

Copiar `.env.example` a `.env` y completar:

```bash
cp .env.example .env
```

Editar `.env`:
```env
# PostgreSQL
POSTGRES_DB=travel_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=tu_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Telegram (obtener de @BotFather)
TELEGRAM_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

# ElevenLabs (para voz)
ELEVENLABS_API_KEY=sk_abc123...

# LLM (DeepSeek u OpenAI)
DEEPSEEK_API_KEY=sk-xyz789...
# O si usas OpenAI:
# OPENAI_API_KEY=sk-proj-...
```

### 6. Inicializar la base de datos

```bash
# Crear tablas de negocio (vuelos, hoteles, etc.)
python -m scripts.setup_business_db

# Crear tablas de memoria LangGraph (checkpoints)
python -m scripts.setup_langgraph_memory
```

---

## 🚀 Ejecución

```bash
python main.py
```

Salida esperada:
```
🚀 Iniciando bot de Telegram...
✅ Bot en marcha... esperando mensajes.
```

---

## 📱 Uso del Bot

### Comandos disponibles
- `/start` - Iniciar conversación

### Ejemplos de conversación

#### Ejemplo 1: Buscar vuelos
```
Usuario: Hola, quiero volar a París

Bot: ¡Hola! 👋 ¿Para cuándo necesitas volar a París?

Usuario: Para el 1 de noviembre

Bot: He encontrado 3 vuelos disponibles de Madrid a París:
     1. AA100 - Salida: 10:00 - Llegada: 12:00 - €150
     2. BA200 - Salida: 14:00 - Llegada: 16:00 - €180
     ...
```

#### Ejemplo 2: Reservar hotel
```
Usuario: Necesito un hotel en Madrid

Bot: 🏨 ¿Qué tipo de hotel buscas? (Economy/Standard/Premium/Luxury)

Usuario: Premium

Bot: He encontrado estos hoteles Premium en Madrid:
     1. Hotel Plaza - €120/noche
     2. Hotel Ritz - €250/noche
     
     ¿Cuál te interesa?

Usuario: El Hotel Plaza

Bot: ⚠️ El agente quiere realizar una reserva...
     ✅ Hotel Plaza reservado con éxito!
```

#### Ejemplo 3: Mensaje de voz
```
Usuario: [Envía mensaje de voz: "Quiero alquilar un coche en el aeropuerto"]

Bot: [Transcribe automáticamente]
     🚗 ¿En qué aeropuerto necesitas alquilar un coche?
```

---

## 🏗️ Arquitectura

### Flujo de datos

```
Usuario (Telegram)
    ↓
handlers/telegram_handlers.py
    ↓
graph/travel_graph.py (LangGraph)
    ↓
graph/agents/ (Primary, Flights, Hotels, Cars, Excursions)
    ↓
tools/ (fetch, search, book, cancel)
    ↓
PostgreSQL (Datos de negocio + Checkpoints)
```

### Agentes especializados

1. **Primary Assistant**: Punto de entrada, analiza intención del usuario
2. **Flight Assistant**: Gestiona reservas de vuelos
3. **Hotel Assistant**: Gestiona reservas de hoteles
4. **Car Rental Assistant**: Gestiona alquiler de coches
5. **Excursion Assistant**: Gestiona tours y excursiones

### Safe vs Sensitive Tools

- **Safe Tools**: Solo lectura (búsqueda, consulta)
- **Sensitive Tools**: Modifican datos (reservar, cancelar)
  - Requieren confirmación (interrupt_before)
  - Se auditan automáticamente

---

## 🔒 Seguridad

### Validaciones implementadas
- ✅ Verificación de propiedad de tickets
- ✅ Passenger ID por usuario
- ✅ Interrupciones antes de acciones sensibles
- ✅ Variables de entorno para credenciales
- ✅ Transacciones SQL con rollback

### Mejoras recomendadas para producción
- [ ] Autenticación de usuarios real
- [ ] Rate limiting por usuario
- [ ] Logging de auditoría
- [ ] Encriptación de datos sensibles
- [ ] HTTPS/SSL para conexiones
- [ ] Backup automático de base de datos

---

## 🧪 Testing

### Probar conexión a base de datos
```bash
python -c "from config.database import get_db_connection; conn = get_db_connection(); print('✅ Conexión exitosa'); conn.close()"
```

### Probar el grafo manualmente
```python
from graph import graph
from langchain_core.messages import HumanMessage

config = {
    "configurable": {
        "passenger_id": "3442 587242",
        "thread_id": "test-123"
    }
}

events = graph.stream(
    {"messages": [HumanMessage(content="Hola")]},
    config,
    stream_mode="values"
)

for event in events:
    print(event)
```

---

## 📊 Base de Datos

### Tablas de negocio
- `tickets` - Billetes de pasajeros
- `flights` - Información de vuelos
- `ticket_flights` - Asociación ticket-vuelo
- `boarding_passes` - Pases de abordar
- `car_rentals` - Alquileres de coches
- `hotels` - Hoteles disponibles
- `trip_recommendations` - Excursiones y tours

### Tablas de LangGraph (memoria)
- `checkpoints` - Estados del grafo por conversación
- `checkpoint_writes` - Escrituras pendientes
- `checkpoint_blobs` - Contenido grande (opcional)

---

## 🐛 Debugging

### Ver logs del bot
```bash
# El bot usa logging, verás mensajes como:
2025-10-29 15:30:04 - __main__ - INFO - 🚀 Iniciando bot...
2025-10-29 15:30:05 - __main__ - INFO - ✅ Bot en marcha...
```

### Ver estado del grafo
```python
from graph import graph

config = {"configurable": {"thread_id": "abc-123"}}
snapshot = graph.get_state(config)

print("Estado actual:", snapshot.values)
print("Próximos nodos:", snapshot.next)
```

### Visualizar el grafo
```python
from graph import graph
from IPython.display import Image, display

display(Image(graph.get_graph().draw_mermaid_png()))
```

---

## 🔧 Configuración Avanzada

### Cambiar el LLM

Por defecto usa DeepSeek. Para cambiar a OpenAI:

```python
# graph/agents/primary.py
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0,
)
```

### Agregar nuevas herramientas

1. Crear la tool en `tools/`:
```python
@tool
def my_new_tool(param: str) -> str:
    """Descripción de la tool."""
    # Implementación
    return result
```

2. Exportar en `tools/__init__.py`:
```python
from .my_tools import my_new_tool
primary_assistant_tools.append(my_new_tool)
```

3. Ya está disponible para el agente

---

## 📚 Documentación Adicional

Cada módulo tiene su propio README detallado:
- [config/README.md](config/README.md) - Configuración
- [tools/README.md](tools/README.md) - Herramientas
- [graph/README.md](graph/README.md) - Grafo multi-agente
- [handlers/README.md](handlers/README.md) - Handlers de Telegram

---

## 🤝 Contribuir

1. Fork el proyecto
2. Crear branch (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push al branch (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

---

## 📝 TODO / Roadmap

- [ ] Confirmación interactiva de acciones sensibles
- [ ] Soporte para múltiples idiomas
- [ ] Integración con APIs de aerolíneas reales
- [ ] Sistema de notificaciones (cambios de vuelo, etc.)
- [ ] Dashboard web para administración
- [ ] Soporte para pagos (Stripe, PayPal)
- [ ] Tests automatizados (pytest)
- [ ] Docker Compose para deployment
- [ ] CI/CD con GitHub Actions

---

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE) para más detalles

---

## 👥 Autores

- Tu Nombre - [@tu_usuario](https://github.com/tu_usuario)

---

## 🙏 Agradecimientos

- [LangChain](https://langchain.com/) - Framework de LLM
- [LangGraph](https://langchain-ai.github.io/langgraph/) - Orquestación multi-agente
- [python-telegram-bot](https://python-telegram-bot.org/) - Telegram Bot API
- [ElevenLabs](https://elevenlabs.io/) - Speech-to-Text
- [PostgreSQL](https://www.postgresql.org/) - Base de datos

---

## 📧 Soporte

Si tienes problemas:
1. Revisa los README de cada módulo
2. Busca en [Issues](https://github.com/tu-usuario/travel-assistant-bot/issues)
3. Crea un nuevo issue con detalles del error

---

**¡Disfruta construyendo tu asistente de viajes! ✈️🤖**