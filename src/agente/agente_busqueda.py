# src/agente/agente_busqueda.py
import json
from langchain.tools import tool

@tool
def buscar_ticket(criterio_busqueda: str) -> str:
    """
    Busca tickets existentes por un criterio de búsqueda, como un número de ticket o palabras clave.
    Devuelve los resultados en formato JSON.
    """
    tickets = [
        {"id": "TCK-1001", "summary": "Usuario no puede loguearse", "status": "abierto"},
        {"id": "TCK-1002", "summary": "Error al pagar con tarjeta", "status": "resuelto"},
        {"id": "TCK-1003", "summary": "Consulta formas de pago", "status": "abierto"},
    ]

    q = (criterio_busqueda or "").lower()
    filtered = [t for t in tickets if q in t["summary"].lower() or q in t["id"].lower()]

    result = filtered if filtered else tickets
    return json.dumps({
        "source": "mock_busqueda_v2",
        "query": criterio_busqueda,
        "results": result
    }, ensure_ascii=False)