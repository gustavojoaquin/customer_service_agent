# 📊 Graph Module - Documentación

Este módulo contiene toda la lógica del grafo de conversación multi-agente usando LangGraph.

## 🏗️ Estructura

```
graph/
├── __init__.py              # Exporta el grafo compilado
├── state.py                 # Definición del State y modelos Pydantic
├── travel_graph.py          # Construcción y compilación del grafo
├── routing.py               # Funciones de routing (condicionales)
├── nodes.py                 # Nodos auxiliares (entry, leave, process_messages)
├── README.md                # Este archivo
└── agents/
    ├── __init__.py          # Exporta todos los agentes
    ├── primary.py           # Asistente principal (punto de entrada)
    ├── flights.py           # Asistente de vuelos
    ├── hotels.py            # Asistente de hoteles
    ├── cars.py              # Asistente de alquiler de coches
    └── excursions.py        # Asistente de excursiones
```

---

## 📄 Descripción de Archivos

### `state.py`
Define el estado global del grafo y los modelos de transferencia entre agentes.

**Componentes principales:**
- `State`: TypedDict que contiene `messages`, `user_info` y `dialog_state`
- `update_dialog_stack()`: Función para manejar la pila de diálogos
- Modelos Pydantic:
  - `CompleteOrEscalate`: Señal de que un agente completó su tarea
  - `ToFlightBookingAssistant`: Transferir al agente de vuelos
  - `ToHotelBookingAssistant`: Transferir al agente de hoteles
  - `ToCarRentalAssistant`: Transferir al agente de coches
  - `ToExcursionAssistant`: Transferir al agente de excursiones

**Ejemplo de uso:**
```python
from graph.state import State, ToFlightBookingAssistant

state = {
    "messages": [...],
    "user_info": [...],
    "dialog_state": ["primary_assistant"]
}
```

---

### `nodes.py`
Contiene nodos auxiliares reutilizables para el grafo.

**Funciones principales:**

#### `_process_messages_for_llm(state: State) -> list[AnyMessage]`
Preprocesa mensajes para el LLM, convirtiendo contenido no-string a JSON.

```python
# Antes: ToolMessage con dict/list
# Después: ToolMessage con string JSON
processed = _process_messages_for_llm(state)
```

#### `create_entry_node(assistant_name: str, new_dialog_state: str) -> callable`
Crea un nodo de entrada para un asistente específico.

```python
entry_node = create_entry_node("Vuelos", "flight_assistant")
# Retorna una función que actualiza el dialog_state
```

#### `leave_skill_node(state: State) -> dict`
Nodo para regresar del asistente especializado al asistente principal.

```python
# Hace "pop" en el dialog_stack
return {"dialog_state": "pop", "messages": [...]}
```

---

### `routing.py`
Contiene toda la lógica de enrutamiento condicional del grafo.

**Funciones principales:**

#### `route_primary_assistant(state: State)`
Decide a qué agente especializado transferir desde el asistente principal.

**Retorna:**
- `"enter_flight_assistant"` → Si el usuario pregunta sobre vuelos
- `"enter_hotel_assistant"` → Si pregunta sobre hoteles
- `"enter_car_rental_assistant"` → Si pregunta sobre coches
- `"enter_excursion_assistant"` → Si pregunta sobre excursiones
- `"primary_tools_node"` → Si usa herramientas del asistente principal
- `END` → Si la conversación termina

#### `create_skill_router(safe_tools: list) -> callable`
Crea un router dinámico para un asistente especializado.

**Retorna una función que decide:**
- `"leave_skill"` → Si usa `CompleteOrEscalate` (tarea completada)
- `"safe_tools"` → Si usa herramientas seguras (búsqueda, consulta)
- `"sensitive_tools"` → Si usa herramientas sensibles (reservar, cancelar)
- `END` → Si termina

#### `route_to_workflow(state: State)`
Determina el flujo inicial basado en el `dialog_state`.

```python
# Si dialog_state está vacío → "primary_assistant"
# Si no → retorna el último estado en la pila
```

---

### `travel_graph.py`
**El archivo más importante**: construye y compila el grafo completo.

#### Checkpointer (Persistencia)
```python
# Conexión a PostgreSQL para persistir conversaciones
connection_string = get_connection_string()
checkpointer = PostgresSaver(
    Connection.connect(connection_string, autocommit=True)
)
```

**¿Por qué esto funciona?**
- `Connection.connect()` crea una conexión directa (no un context manager)
- `autocommit=True` asegura que cada checkpoint se guarde inmediatamente
- `PostgresSaver` envuelve la conexión para manejar el estado del grafo

#### Construcción del Grafo

**Nodos principales:**
1. `fetch_user_info`: Obtiene información del usuario al inicio
2. `primary_assistant`: Asistente principal (punto de entrada)
3. `{skill}_assistant`: Asistentes especializados (flights, hotels, cars, excursions)
4. `{skill}_safe_tools`: Herramientas de solo lectura (búsqueda)
5. `{skill}_sensitive_tools`: Herramientas que modifican datos (reservar, cancelar)
6. `leave_skill`: Nodo para regresar al asistente principal

**Edges (conexiones):**
```python
START → fetch_user_info → primary_assistant
                              ↓
              ┌───────────────┴───────────────┐
              ↓                               ↓
      flight_assistant                hotel_assistant
              ↓                               ↓
        safe_tools / sensitive_tools    safe_tools / sensitive_tools
              ↓                               ↓
        leave_skill ──────────→ primary_assistant
```

#### Compilación
```python
graph = builder.compile(
    checkpointer=checkpointer,  # Persistencia con PostgreSQL
    interrupt_before=[          # Pausar antes de acciones sensibles
        "flight_sensitive_tools",
        "hotel_sensitive_tools",
        "car_rental_sensitive_tools",
        "excursion_sensitive_tools",
    ],
)
```

**`interrupt_before`**: Pausa el grafo antes de ejecutar herramientas sensibles, permitiendo:
- Confirmación del usuario
- Logging de acciones críticas
- Auditoría de cambios

---

### `agents/` (Carpeta)

Cada archivo define un agente especializado con su prompt y lógica.

#### Patrón común:
```python
# 1. Definir el prompt del agente
prompt = ChatPromptTemplate.from_messages([
    ("system", "Eres un asistente experto en..."),
    ("placeholder", "{messages}")
])

# 2. Crear el runnable con herramientas
runnable = prompt | llm.bind_tools(safe_tools + sensitive_tools + [CompleteOrEscalate])

# 3. Definir el nodo del agente
def agent_node(state: State):
    temp_state = state.copy()
    temp_state["messages"] = _process_messages_for_llm(state)
    result = runnable.invoke(temp_state)
    return {"messages": [result]}
```

#### `primary.py`
**Responsabilidad:** Punto de entrada, analiza la intención del usuario y delega a agentes especializados.

**Prompt clave:**
- Identifica categoría (vuelos, hoteles, coches, excursiones)
- Responde brevemente si no está relacionado con viajes
- Usa emojis y lenguaje natural

#### `flights.py`
**Responsabilidad:** Gestionar reservas de vuelos, cambios de billetes, registros.

**Tools:**
- Safe: `search_flights`, `lookup_policy`
- Sensitive: `update_ticket_to_new_flight`, `cancel_ticket`, `register_new_flight`

#### `hotels.py`, `cars.py`, `excursions.py`
Similar patrón, cada uno con sus propias herramientas especializadas.

---

## 🔄 Flujo de Ejecución

### 1. Usuario envía mensaje
```
Usuario: "Quiero reservar un vuelo a París"
```

### 2. Grafo inicia en `primary_assistant`
```python
primary_assistant_node(state)
# Analiza: "Esta es una consulta sobre VUELOS"
# Llama a tool: ToFlightBookingAssistant
```

### 3. Routing decide transferir
```python
route_primary_assistant(state)
# Retorna: "enter_flight_assistant"
```

### 4. Entry node actualiza dialog_state
```python
{"dialog_state": ["primary_assistant", "flight_assistant"]}
```

### 5. Flight assistant procesa
```python
flight_assistant_node(state)
# Usa search_flights para buscar opciones
```

### 6. Usuario confirma reserva
```
Usuario: "Sí, reserva el vuelo AA100"
```

### 7. Grafo llega a interrupt
```python
# Se pausa en "flight_sensitive_tools"
# Espera aprobación
```

### 8. Confirmación y ejecución
```python
# Ejecuta: register_new_flight(...)
# Luego: CompleteOrEscalate
```

### 9. Regresa al primary assistant
```python
leave_skill_node(state)
{"dialog_state": ["primary_assistant"]}  # Pop del stack
```

---

## 🔑 Conceptos Clave

### Dialog State (Pila de Estados)
Mantiene el historial de navegación entre asistentes:
```python
["primary_assistant"]  # Inicio
["primary_assistant", "flight_assistant"]  # En vuelos
["primary_assistant"]  # Regresó (después de pop)
```

### Safe vs Sensitive Tools
- **Safe**: Solo lectura, sin efectos secundarios (búsqueda, consulta)
- **Sensitive**: Modifican datos, requieren confirmación (reservar, cancelar)

### CompleteOrEscalate
Señal para que un agente especializado indique que:
1. Completó su tarea exitosamente
2. No puede continuar y necesita escalar al primary assistant

---

## 📊 Persistencia con PostgreSQL

El checkpointer guarda automáticamente:
- **Historial de mensajes** por `thread_id`
- **Estado del grafo** en cada paso
- **Interrupciones pendientes**

**Tablas creadas:**
- `checkpoints`: Estados del grafo
- `checkpoint_writes`: Escrituras pendientes
- `checkpoint_blobs`: Contenido grande (opcional)

**Uso:**
```python
# En handlers/telegram_handlers.py
config = {
    "configurable": {
        "thread_id": "uuid-unico-por-usuario",
        "passenger_id": "3442 587242"
    }
}

# El grafo automáticamente:
# 1. Recupera el historial de esta conversación
# 2. Continúa desde donde quedó
# 3. Guarda el nuevo estado
events = graph.stream({"messages": [...]}, config)
```

---

## 🚀 Uso desde otros módulos

```python
# En handlers/telegram_handlers.py
from graph import graph

# Ejecutar el grafo
config = {"configurable": {"thread_id": "...", "passenger_id": "..."}}
events = graph.stream({"messages": [HumanMessage(content="...")]}, config)

for event in events:
    if "messages" in event:
        response = event["messages"][-1]
```

---

## 🛠️ Debugging

### Ver el estado actual del grafo
```python
snapshot = graph.get_state(config)
print(snapshot.values)  # Estado actual
print(snapshot.next)    # Próximos nodos a ejecutar
```

### Visualizar el grafo
```python
from IPython.display import Image, display
display(Image(graph.get_graph().draw_mermaid_png()))
```

---

## ⚠️ Consideraciones Importantes

1. **Orden de imports**: Importar `agents` después de definir `State` para evitar imports circulares
2. **Connection.connect()**: No usar `with`, crear conexión directa para persistencia
3. **autocommit=True**: Necesario para que PostgresSaver funcione correctamente
4. **thread_id único**: Cada conversación debe tener su propio ID único
5. **Procesamiento de mensajes**: Siempre usar `_process_messages_for_llm()` antes de invocar al LLM

---

## 📚 Referencias

- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [PostgresSaver](https://langchain-ai.github.io/langgraph/reference/checkpoints/#langgraph.checkpoint.postgres.PostgresSaver)
- [StateGraph](https://langchain-ai.github.io/langgraph/reference/graphs/#langgraph.graph.StateGraph)