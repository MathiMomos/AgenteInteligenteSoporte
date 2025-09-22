from langchain.tools import tool
from sqlalchemy.orm import Session
from src.util import util_schemas as sch
from src.crud import crud_tickets
from src.util import util_base_de_datos as db


class ToolBusqueda:
    def __init__(self, db: Session, user_info: sch.TokenData):
        self.db = db
        self.user_info = user_info

    def _format_ticket_details(self, ticket: db.Ticket) -> str:
        """
        Función auxiliar para formatear los detalles de un ticket en un texto legible.
        """
        try:
            nombre_servicio = ticket.cliente_servicio.servicio.nombre
        except Exception:
            nombre_servicio = "No disponible"
        
        fecha_creacion = "-"
        if hasattr(ticket, "created_at") and ticket.created_at:
            try:
                fecha_creacion = ticket.created_at.strftime("%d/%m/%Y")
            except Exception:
                fecha_creacion = "-"

        details = (
            f"  - **ID:** #{ticket.id_ticket}\n"
            f"  - **Asunto:** {ticket.asunto}\n"
            f"  - **Servicio:** {nombre_servicio}\n"
            f"  - **Nivel:** {ticket.nivel}\n"
            f"  - **Tipo:** {ticket.tipo}\n"
            f"  - **Estado:** {ticket.estado}"
            f"  - **Fecha de Creación:** {fecha_creacion}"
        )

        if ticket.estado == 'finalizado' and ticket.diagnostico:
            details += f"\n  - **Diagnóstico:** {ticket.diagnostico}"

        return details

    def get_tools(self) -> list:
        """
        Fábrica que construye y devuelve una LISTA de todas las herramientas de búsqueda.
        """

        @tool
        def buscar_ticket_por_id(ticket_id: int) -> str:
            """Busca un ticket específico por su número de ID. Úsalo cuando el usuario te dé un número."""
            ticket = crud_tickets.get_ticket_by_id_db(self.db, ticket_id, self.user_info)
            if ticket:
                formatted_details = self._format_ticket_details(ticket)
                return f"He encontrado los detalles del ticket solicitado:\n{formatted_details}"
            return f"No encontré el ticket #{ticket_id} o no tienes permiso para verlo."

        @tool
        def listar_tickets_abiertos() -> str:
            """Lista todos los tickets abiertos (no finalizados) del colaborador actual. Úsalo si el usuario pregunta por 'mis tickets'."""
            tickets = crud_tickets.get_all_open_tickets(self.db, self.user_info)
            if not tickets:
                return "Usted no tiene tickets abiertos actualmente."

            tickets_formateados = [self._format_ticket_details(t) for t in tickets]
            respuesta_final = "\n\n".join(tickets_formateados)
            return f"He encontrado los siguientes tickets abiertos:\n{respuesta_final}"

        @tool
        def buscar_tickets_por_asunto(asunto: str) -> str:
            """Busca tickets cuyo asunto coincida parcialmente con un texto."""
            tickets = crud_tickets.get_tickets_by_subject(self.db, asunto, self.user_info)
            if not tickets:
                return f"No encontré tickets cuyo asunto contenga '{asunto}'."

            tickets_formateados = [self._format_ticket_details(t) for t in tickets]
            respuesta_final = "\n\n".join(tickets_formateados)
            return f"He encontrado los siguientes tickets relacionados con '{asunto}':\n{respuesta_final}"

        return [buscar_ticket_por_id, listar_tickets_abiertos, buscar_tickets_por_asunto]