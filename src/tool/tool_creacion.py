from langchain_core.tools import tool
from sqlalchemy.orm import Session
from enum import Enum

from datetime import datetime, date

from src.util import util_schemas as sch, util_formatear_conversacion
from src.util.util_memory import memory
from src.crud import crud_tickets


class TipoTicket(str, Enum):
    INCIDENCIA = "incidencia"
    SOLICITUD = "solicitud"


class NivelTicket(str, Enum):
    BAJO = "bajo"
    MEDIO = "medio"
    ALTO = "alto"
    CRITICO = "crítico"


class ToolCreacion:
    def __init__(self, db: Session, user_info: sch.TokenData, thread_id: str):
        self.db = db
        self.user_info = user_info
        self.thread_id = thread_id

    def get_tool(self):
        """
        Este método es una fábrica: construye y devuelve la herramienta funcional.
        """

        @tool
        def crear_ticket(asunto: str, tipo: TipoTicket, nivel: NivelTicket, nombre_servicio: str) -> str:
            """
            Crea un nuevo ticket de soporte. Debe llamarse sólo cuando el asistente
            ya haya inferido 'asunto', 'tipo', 'nivel' y 'nombre_servicio' a partir
            de la conversación completa.
            """
            try:
                ticket = crud_tickets.create_ticket_db(
                    db_session=self.db,
                    user_info=self.user_info,
                    asunto=asunto,
                    tipo=tipo.value,
                    nivel=nivel.value,
                    nombre_servicio=nombre_servicio
                )

                state = memory.get({"configurable": {"thread_id": self.thread_id}})
                messages = state["channel_values"]["messages"] if state else []
                conversation = util_formatear_conversacion.format_conversation(messages)
                crud_tickets.save_conversation_db(
                    db_session=self.db, ticket_id=ticket.id_ticket, conversation=conversation,
                )

                # Fecha/hora exacta de creación del ticket
                fc = getattr(ticket, "created_at", None)
                if isinstance(fc, datetime):
                    fecha_creacion = fc.strftime("%d/%m/%Y %H:%M:%S")
                elif isinstance(fc, date):
                    fecha_creacion = fc.strftime("%d/%m/%Y 00:00:00")
                else:
                    fecha_creacion = datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S")

                # Devuelve sólo un texto breve + fecha exacta para que el LLM la use
                return (
                    f"He generado el ticket **#{ticket.id_ticket}** con su solicitud. "
                    f"Fecha de creación del ticket: {fecha_creacion}."
                )

            except Exception as e:
                print(f"[crear_ticket] Error: {e}")
                return "Lo siento, ocurrió un error inesperado al intentar crear su ticket."

        # Devolvemos la herramienta (objeto Tool) decorada correctamente
        return crear_ticket
