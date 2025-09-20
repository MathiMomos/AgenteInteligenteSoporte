from langchain.tools import tool
from sqlalchemy.orm import Session
from src.util import util_schemas as sch
from src.crud import crud_tickets


class ToolBusqueda:
    def __init__(self, db: Session, user_info: sch.TokenData):
        self.db = db
        self.user_info = user_info

    def get_tools(self) -> list:
        """
        Fábrica que construye y devuelve una LISTA de todas las herramientas de búsqueda.
        """

        @tool
        def buscar_ticket_por_id(ticket_id: int) -> str:
            """Busca un ticket específico por su número de ID. Úsalo cuando el usuario te dé un número."""
            ticket = crud_tickets.get_ticket_by_id_db(self.db, ticket_id, self.user_info)
            if ticket:
                return f"El ticket #{ticket.id_ticket} ('{ticket.asunto}') fue encontrado. Su estado actual es: '{ticket.estado}'."
            return f"No encontré el ticket #{ticket_id} o no tienes permiso para verlo."

        @tool
        def listar_tickets_abiertos() -> str:
            """Lista todos los tickets abiertos (no finalizados) del colaborador actual. Úsalo si el usuario pregunta por 'mis tickets'."""
            tickets = crud_tickets.get_all_open_tickets(self.db, self.user_info)
            if not tickets:
                return "Usted no tiene tickets abiertos actualmente."
            return "\n".join([f"- Ticket #{t.id_ticket}: {t.asunto} (Estado: {t.estado})" for t in tickets])

        @tool
        def buscar_tickets_por_asunto(asunto: str) -> str:
            """Busca tickets cuyo asunto coincida parcialmente con un texto."""
            tickets = crud_tickets.get_tickets_by_subject(self.db, asunto, self.user_info)
            if not tickets:
                return f"No encontré tickets cuyo asunto contenga '{asunto}'."
            return "\n".join([f"- Ticket #{t.id_ticket}: {t.asunto} (Estado: {t.estado})" for t in tickets])

        return [buscar_ticket_por_id, listar_tickets_abiertos, buscar_tickets_por_asunto]