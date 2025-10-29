# 🛠️ Tools Module - Documentación

Este módulo contiene todas las herramientas (tools) de LangChain que los agentes pueden usar para interactuar con la base de datos y realizar acciones.

## 🏗️ Estructura

```
tools/
├── __init__.py              # Exporta todas las tools y las agrupa por categoría
├── base.py                  # Funciones helper comunes
├── flights_tools.py         # Herramientas de vuelos
├── hotel_tools.py           # Herramientas de hoteles
├── car_tools.py             # Herramientas de alquiler de coches
├── excursion_tools.py       # Herramientas de excursiones
├── policy_tools.py          # Consultas de políticas de la compañía
└── README.md                # Este archivo
```

---

## 📄 Descripción de Archivos

### `base.py`
Funciones auxiliares compartidas por todas las tools.

#### `get_passenger_id(config: RunnableConfig) -> str`
Extrae el `passenger_id` del config o lanza un error.

```python
from tools.base import get_passenger_id

def my_tool(config: RunnableConfig):
    passenger_id = get_passenger_id(config)
    # passenger_id = "3442 587242"
```

#### `verify_ticket_ownership(cursor, ticket_no: str, passenger_id: str) -> bool`
Verifica si un ticket pertenece al pasajero actual.

```python
if not verify_ticket_ownership(cursor, ticket_no, passenger_id):
    return "No tienes permisos para cancelar este ticket"
```

**¿Por qué es importante?**
- Seguridad: Evita que un usuario modifique tickets de otro
- Reutilizable: Todas las tools de tickets usan esta función
- Centralizado: Un solo lugar para auditar permisos

---

### `flights_tools.py`
Herramientas para gestionar vuelos y billetes.

#### Safe Tools (Solo lectura)

##### `fetch_user_flight_information(config: RunnableConfig) -> list[dict]`
Obtiene todos los vuelos del usuario actual.

```python
# Retorna:
[
    {
        "ticket_no": "T001",
        "flight_no": "AA100",
        "departure_airport": "MAD",
        "arrival_airport": "CDG",
        "seat_no": "12A",
        ...
    }
]
```

##### `search_flights(...) -> list[dict]`
Busca vuelos disponibles por criterios.

**Parámetros:**
- `departure_airport`: Código IATA (ej: "MAD")
- `arrival_airport`: Código IATA (ej: "CDG")
- `start_time`: Fecha/hora mínima de salida
- `end_time`: Fecha/hora máxima de salida
- `limit`: Máximo de resultados (default: 20)

```python
flights = search_flights(
    departure_airport="MAD",
    arrival_airport="CDG",
    start_time=datetime(2025, 11, 1)
)
```

#### Sensitive Tools (Modifican datos)

##### `update_ticket_to_new_flight(ticket_no: str, new_flight_id: int, config: RunnableConfig) -> str`
Cambia un billete a un nuevo vuelo.

**Validaciones:**
- El ticket existe
- El pasajero es propietario del ticket
- El nuevo vuelo existe

```python
result = update_ticket_to_new_flight("T001", "F002", config)
# "¡Billete actualizado al nuevo vuelo con éxito!"
```

##### `cancel_ticket(ticket_no: str, config: RunnableConfig) -> str`
Cancela un billete y todas sus asociaciones.

**Acciones:**
1. Elimina el boarding pass
2. Elimina la asociación ticket-flight
3. Elimina el ticket

```python
result = cancel_ticket("T001", config)
# "¡Billete cancelado con éxito!"
```

##### `register_new_flight(...) -> str`
Registra un nuevo vuelo y crea un billete.

**Parámetros requeridos:**
- Información del vuelo (número, aeropuertos, horarios)
- Información del pasajero (nombre, email)
- Clase de vuelo (default: Economy)

**Genera automáticamente:**
- `flight_id`: UUID único
- `ticket_no`: UUID único
- `book_ref`: Referencia de reserva (6 caracteres)
- `seat_no`: Asiento asignado

```python
result = register_new_flight(
    flight_no="AA100",
    departure_airport="MAD",
    arrival_airport="CDG",
    scheduled_departure="2025-11-01 10:00:00",
    scheduled_arrival="2025-11-01 12:00:00",
    passenger_name="Juan Pérez",
    passenger_email="juan@example.com",
    fare_conditions="Economy"
)
```

---

### `hotel_tools.py`
Herramientas para gestionar hoteles.

#### Safe Tools

##### `search_hotels(...) -> list[dict]`
Busca hoteles disponibles.

**Parámetros:**
- `location`: Ciudad o ubicación
- `name`: Nombre del hotel (búsqueda parcial)
- `price_tier`: "Economy", "Standard", "Premium", "Luxury"
- `checkin_date`: Fecha de entrada
- `checkout_date`: Fecha de salida

```python
hotels = search_hotels(location="Madrid", price_tier="Luxury")
# [{"id": 1, "name": "Hotel Ritz", "location": "Madrid", ...}]
```

#### Sensitive Tools

##### `book_hotel(hotel_id: int) -> str`
Reserva un hotel por su ID.

```python
result = book_hotel(1)
# "Hotel 1 reservado con éxito."
```

##### `cancel_hotel(hotel_id: int) -> str`
Cancela una reserva de hotel.

```python
result = cancel_hotel(1)
# "Reserva de hotel 1 cancelada con éxito."
```

---

### `car_tools.py`
Herramientas para alquiler de coches.

#### Safe Tools

##### `search_car_rentals(...) -> list[dict]`
Busca coches disponibles para alquilar.

**Parámetros:**
- `location`: Ubicación (aeropuerto, ciudad)
- `name`: Compañía de alquiler (Hertz, Avis, etc.)
- `price_tier`: Categoría de precio

```python
cars = search_car_rentals(location="Madrid Airport")
# [{"id": 1, "name": "Hertz", "location": "Madrid Airport", ...}]
```

##### `buscar_carros_rentados() -> list[dict]`
Lista todos los coches actualmente rentados.

```python
rented = buscar_carros_rentados()
# [{"id": 2, "name": "Avis", "booked": True, ...}]
```

#### Sensitive Tools

##### `book_car_rental(rental_id: int) -> str`
Reserva un coche.

##### `cancel_car_rental(rental_id: int) -> str`
Cancela una reserva de coche.

---

### `excursion_tools.py`
Herramientas para tours y excursiones.

#### Safe Tools

##### `search_trip_recommendations(...) -> list[dict]`
Busca recomendaciones de excursiones.

**Parámetros:**
- `location`: Ciudad o país
- `name`: Nombre de la excursión
- `keywords`: Palabras clave (no implementado aún)

```python
tours = search_trip_recommendations(location="Paris")
# [{"id": 1, "name": "Tour del Louvre", "location": "Paris", ...}]
```

#### Sensitive Tools

##### `book_excursion(recommendation_id: int) -> str`
Reserva una excursión.

##### `cancel_excursion(recommendation_id: int) -> str`
Cancela una excursión.

---

### `policy_tools.py`
Consulta de políticas de la compañía.

##### `lookup_policy(query: str) -> str`
Busca políticas relevantes según la consulta.

```python
policy = lookup_policy("cambio de vuelo")
# "Los cambios están permitidos con una tarifa de $100 si se realizan más de 24 horas antes..."
```

**Políticas actuales:**
- Cambios de vuelo: $100 si es >24h antes
- (Puedes agregar más políticas aquí)

---

## 📦 Agrupaciones en `__init__.py`

Las tools se exportan agrupadas por categoría y tipo:

```python
# Primary assistant (herramientas generales)
primary_assistant_tools = [
    fetch_user_flight_information,
    lookup_policy
]

# Flight tools
flight_safe_tools = [search_flights, lookup_policy]
flight_sensitive_tools = [
    update_ticket_to_new_flight,
    cancel_ticket,
    register_new_flight
]

# Hotel tools
hotel_safe_tools = [search_hotels, lookup_policy]
hotel_sensitive_tools = [book_hotel, cancel_hotel]

# Car rental tools
car_rental_safe_tools = [search_car_rentals, buscar_carros_rentados, lookup_policy]
car_rental_sensitive_tools = [book_car_rental, cancel_car_rental]

# Excursion tools
excursion_safe_tools = [search_trip_recommendations, lookup_policy]
excursion_sensitive_tools = [book_excursion, cancel_excursion]
```

**¿Por qué esta agrupación?**
1. **Safe tools**: No modifican datos, se pueden ejecutar sin confirmación
2. **Sensitive tools**: Modifican datos, requieren `interrupt_before` en el grafo
3. Facilita el routing en `graph/routing.py`

---

## 🔑 Patrón Común de Implementación

Todas las tools siguen este patrón:

```python
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from config.database import get_db_connection, dict_factory

@tool
def my_tool(param1: str, config: RunnableConfig) -> str:
    """Descripción clara de lo que hace la tool."""
    
    # 1. Obtener passenger_id si es necesario
    passenger_id = get_passenger_id(config)
    
    # 2. Conectar a la base de datos
    conn = get_db_connection()
    conn.row_factory = dict_factory  # Para retornar dicts
    cursor = conn.cursor()
    
    # 3. Ejecutar query
    cursor.execute("SELECT * FROM table WHERE ...", (param1,))
    results = cursor.fetchall()
    
    # 4. Cerrar conexión
    conn.close()
    
    # 5. Retornar resultado
    return results
```

---

## 🛡️ Validaciones y Seguridad

### Verificación de Propiedad
```python
# Antes de modificar/cancelar, verificar propiedad
if not verify_ticket_ownership(cursor, ticket_no, passenger_id):
    conn.close()
    return "No tienes permisos para esta acción"
```

### Manejo de Errores
```python
try:
    cursor.execute(...)
    conn.commit()
    return "¡Éxito!"
except Exception as e:
    conn.rollback()
    return f"Error: {e}"
finally:
    conn.close()
```

### Transacciones
```python
# Para operaciones múltiples, usar transacciones
try:
    cursor.execute("DELETE FROM boarding_passes WHERE ...")
    cursor.execute("DELETE FROM ticket_flights WHERE ...")
    cursor.execute("DELETE FROM tickets WHERE ...")
    conn.commit()  # Todo o nada
except:
    conn.rollback()  # Revertir si algo falla
```

---

## 🔄 Flujo de Uso

### 1. Agente decide usar una tool
```python
# En graph/agents/flights.py
flight_runnable = prompt | llm.bind_tools(
    flight_safe_tools + flight_sensitive_tools + [CompleteOrEscalate]
)
```

### 2. LLM genera tool call
```python
{
    "name": "search_flights",
    "arguments": {
        "departure_airport": "MAD",
        "arrival_airport": "CDG"
    }
}
```

### 3. LangGraph ejecuta la tool
```python
# En travel_graph.py
ToolNode(flight_safe_tools)  # Ejecuta search_flights
```

### 4. Resultado se agrega al estado
```python
state["messages"].append(
    ToolMessage(
        content=json.dumps(results),
        tool_call_id="..."
    )
)
```

### 5. LLM recibe el resultado y responde
```python
"He encontrado 3 vuelos disponibles de Madrid a París..."
```

---

## 📊 Conexión con Base de Datos

Todas las tools usan:
```python
from config.database import get_db_connection

conn = get_db_connection()  # Conexión a PostgreSQL
```

**Configuración en `config/database.py`:**
```python
def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT")
    )
```

---

## 🚀 Agregar una Nueva Tool

### Paso 1: Crear la tool
```python
# En tools/flights_tools.py
@tool
def get_flight_details(flight_id: str) -> dict:
    """Obtiene detalles de un vuelo específico."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM flights WHERE flight_id = ?", (flight_id,))
    result = cursor.fetchone()
    conn.close()
    return dict(zip([col[0] for col in cursor.description], result))
```

### Paso 2: Exportar en `__init__.py`
```python
from .flights_tools import (
    # ... otras tools ...
    get_flight_details  # Nueva tool
)

flight_safe_tools = [
    search_flights,
    get_flight_details,  # Agregar aquí
    lookup_policy
]
```

### Paso 3: Ya está disponible
```python
# El agente automáticamente puede usarla
flight_runnable = prompt | llm.bind_tools(flight_safe_tools + ...)
```

---

## ⚠️ Consideraciones Importantes

1. **Siempre cerrar conexiones**: Usar `conn.close()` o `finally`
2. **Usar `dict_factory`** para retornar diccionarios en lugar de tuplas
3. **Validar propiedad** antes de modificar datos del usuario
4. **Manejo de errores** con try/except para tools sensibles
5. **Documentación clara** en el docstring de cada tool
6. **Parámetros opcionales** con valores por defecto
7. **Retornar strings descriptivos** para que el LLM entienda el resultado

---

## 📚 Referencias

- [LangChain Tools](https://python.langchain.com/docs/modules/agents/tools/)
- [Tool Decorator](https://api.python.langchain.com/en/latest/tools/langchain_core.tools.tool.html)
- [RunnableConfig](https://api.python.langchain.com/en/latest/runnables/langchain_core.runnables.config.RunnableConfig.html)