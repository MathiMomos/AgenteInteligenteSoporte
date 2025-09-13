from langchain.tools import tool
from sqlalchemy.orm import Session
from src.util import util_schemas as sch
from src.crud import crud_tickets

@tool
def buscar_ticket(ticket_id: int, db: Session, user_info: sch.TokenData) -> str:
    """
    Busca el estado de un ticket existente usando su número de ID.
    """
    ticket = crud_tickets.get_ticket_by_id_db(db, ticket_id=ticket_id, user_info=user_info)
    if ticket:
        return f"El ticket #{ticket_id} ('{ticket.asunto}') fue encontrado. Su estado actual es: '{ticket.estado}'."
    else:
        return f"No encontré el ticket #{ticket_id} o no tienes permiso para verlo."