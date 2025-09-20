from langchain.tools import tool
from sqlalchemy.orm import Session
from enum import Enum
from typing import List

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
        Este metodo es una fábrica: construye y devuelve la herramienta funcional.
        """

        # Definimos la herramienta como una función INTERNA
        @tool
        def crear_ticket(asunto: str, tipo: TipoTicket, nivel: NivelTicket, nombre_servicio: str) -> str:
            """
            Usa esta herramienta para crear un nuevo ticket de soporte. Debes haber inferido
            previamente el 'asunto', 'tipo', 'nivel' y 'nombre_servicio' a partir de la conversación completa.
            """
            # Esta función interna tiene acceso a self.db, self.user_info, etc.,
            # pero no tiene 'self' en su propia firma, evitando el error.
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

                return (
                    f"He generado el ticket **#{ticket.id_ticket}** con su solicitud. "
                    "Nuestro equipo de soporte se pondrá en contacto con usted a través de su correo."
                )
            except Exception as e:
                print(f"[crear_ticket] Error: {e}")
                return "Lo siento, ocurrió un error inesperado al intentar crear su ticket."

        # La fábrica devuelve la herramienta recién creada
        return crear_ticket