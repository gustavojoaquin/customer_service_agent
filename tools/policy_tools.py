
from langchain_core.tools import tool


@tool
def lookup_policy(query: str) -> str:
    """Consulta las políticas de la compañía."""
    if "cambio" in query or "modificar" in query:
        return "Los cambios están permitidos con una tarifa de $100 si se realizan más de 24 horas antes de la salida."
    return "No se encontró una política específica para su consulta."