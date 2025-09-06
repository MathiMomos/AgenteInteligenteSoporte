# src/agente/agente_creacion.py
import json
from uuid import uuid4
from langchain.tools import tool

@tool
def crear_ticket(descripcion: str) -> str:
    """
    Crea un nuevo ticket de soporte. Úsalo cuando el usuario quiera registrar un nuevo problema.
    El argumento 'descripcion' debe contener un resumen claro del problema del usuario.
    """
    ticket_id = f"TCK-{uuid4().hex[:8].upper()}"
    ticket = {
        "ticket_id": ticket_id,
        "description": descripcion,
        "status": "abierto"
    }
    return json.dumps({
        "source": "mock_creacion_v2",
        "ticket": ticket
    }, ensure_ascii=False)