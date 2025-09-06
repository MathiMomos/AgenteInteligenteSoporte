# src/agente/agente_busqueda.py
import json
from typing import Optional
from src.util.util_agente import build_system_prompt
from src.util.util_llm import get_llm

def get_agente_busqueda_chain() -> Optional[None]:
    """
    Placeholder/factory (mock). Si quisieras construir un LLMChain para validar input, hazlo aquí.
    """
    llm = get_llm()
    _ = build_system_prompt(
        role="Agente de Búsqueda",
        instructions="Busca tickets por criterios dados. (mock)"
    )
    return None


def handle_query(query: str) -> str:
    """
    Función expuesta a la Tool. Devuelve string (JSON) con resultados mock.
    """
    tickets = [
        {"id": "TCK-1001", "summary": "Usuario no puede loguearse", "status": "abierto"},
        {"id": "TCK-1002", "summary": "Error al pagar con tarjeta", "status": "resuelto"},
        {"id": "TCK-1003", "summary": "Consulta formas de pago", "status": "abierto"},
    ]

    q = (query or "").lower()
    filtered = [t for t in tickets if q in t["summary"].lower() or q in t["id"].lower()]

    result = filtered if filtered else tickets
    return json.dumps({
        "source": "mock_busqueda",
        "query": query,
        "results": result
    }, ensure_ascii=False)
