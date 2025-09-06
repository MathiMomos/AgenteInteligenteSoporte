# src/agente/agente_creacion.py
import json
from uuid import uuid4
from typing import Optional
from src.util.util_agente import build_system_prompt
from src.util.util_llm import get_llm

def get_agente_creacion_chain() -> Optional[None]:
    """
    Placeholder/factory (mock). Si quisieras validar campos con LLM, hazlo aquí.
    """
    llm = get_llm()
    _ = build_system_prompt(
        role="Agente de Creación",
        instructions="Registra tickets con los campos provistos. (mock)"
    )
    return None


def handle_query(input_text: str) -> str:
    """
    Función expuesta a la Tool. Crea un ticket mock y retorna JSON-string.
    """
    ticket_id = f"TCK-{uuid4().hex[:8].upper()}"
    ticket = {
        "ticket_id": ticket_id,
        "description": input_text,
        "status": "abierto"
    }
    return json.dumps({
        "source": "mock_creacion",
        "ticket": ticket
    }, ensure_ascii=False)
