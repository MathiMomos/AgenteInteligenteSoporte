from langchain.tools import tool
from sqlalchemy.orm import Session
from src.util import util_schemas as sch
from src.crud import crud_tickets

# Variable global donde se inyecta el contexto
_agente_busqueda_callable = None

def get_agente_busqueda_callable(db: Session, user_info: sch.TokenData):
    """
    Construye un callable especializado en búsqueda de tickets con el contexto
    de la base de datos y el usuario autenticado.
    """
    def _buscar_ticket(ticket_id: int) -> str:
        ticket = crud_tickets.get_ticket_by_id_db(
            db_session=db,
            ticket_id=ticket_id,
            user_info=user_info
        )
        if ticket:
            return f"El ticket #{ticket_id} ('{ticket.asunto}') fue encontrado. Estado actual: '{ticket.estado}'."
        else:
            return f"No encontré el ticket #{ticket_id} o no tienes permiso para verlo."

    # 🔑 Aquí asignamos el callable a la variable global
    global _agente_busqueda_callable
    _agente_busqueda_callable = _buscar_ticket
    return _buscar_ticket

@tool
def buscar_ticket(ticket_id: int) -> str:
    """
    Usa esta herramienta para consultar el estado de un ticket por su número de ID.
    Debe inicializarse previamente con `get_agente_busqueda_callable`.
    """
    if _agente_busqueda_callable is None:
        return "El agente de búsqueda no fue inicializado con contexto."
    return _agente_busqueda_callable(ticket_id)
