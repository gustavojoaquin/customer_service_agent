"""
Crea las tablas necesarias para la memoria de LangGraph (checkpoints)
Ejecutar UNA SOLA VEZ al iniciar el proyecto
"""
import sys
from pathlib import Path

# Agregar la raíz del proyecto al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from langgraph.checkpoint.postgres import PostgresSaver
from config.database import get_connection_string

def setup_langgraph_memory():
    """Crea tablas de checkpoints para LangGraph"""
    conn_string = get_connection_string()
    
    # LangGraph crea automáticamente las tablas
    with PostgresSaver.from_conn_string(conn_string) as checkpointer:
        checkpointer.setup()
    
    print("✅ Tablas de memoria LangGraph creadas correctamente")

if __name__ == "__main__":
    setup_langgraph_memory()