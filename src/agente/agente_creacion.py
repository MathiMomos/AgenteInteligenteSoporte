from langchain.tools import tool
from sqlalchemy.orm import Session
from src.util import util_schemas as sch, util_formatear_conversacion
from src.crud import crud_tickets
from enum import Enum

from src.util.util_memory import memory

# Definimos los tipos de ticket posibles
class TipoTicket(str, Enum):
    INCIDENCIA = "incidencia"
    SOLICITUD = "solicitud"

# Variable global donde se inyecta el contexto
_agente_creacion_callable = None

def get_agente_creacion_callable(db: Session, user_info: sch.TokenData, thread_id: str):
    """
    Devuelve un callable para crear tickets con contexto de DB, usuario y conversación.
    """
    def _crear_ticket(asunto: str, tipo: TipoTicket) -> str:
        try:
            # 1. Crear ticket en DB
            ticket_creado = crud_tickets.create_ticket_db(
                db_session=db,
                asunto=asunto,
                tipo=tipo.value,
                user_info=user_info
            )

            # 2. Obtener historial de conversación desde MemorySaver
            state = memory.get({"configurable": {"thread_id": thread_id}})
            messages = state["channel_values"]["messages"] if state else []

            conversation_json = util_formatear_conversacion.format_conversation(messages)

            # 3. Guardar conversación en DB
            crud_tickets.save_conversation_db(
                db_session=db,
                ticket_id=ticket_creado.id_ticket,
                conversation=conversation_json
            )

            return (f"He generado el ticket #{ticket_creado.id_ticket} con el asunto '{asunto}'. "
                    "Nuestro equipo de soporte se pondrá en contacto con usted por correo electrónico. "
                    "Gracias por su paciencia. ✨")
        except Exception as e:
            print(f"Error en la herramienta 'crear_ticket': {e}")
            return "Lo siento, ocurrió un error inesperado al intentar crear su ticket."

    return _crear_ticket

@tool
def crear_ticket(asunto: str, tipo: TipoTicket) -> str:
    """
    Usa esta herramienta para crear un nuevo ticket de soporte.
    Debe inicializarse previamente con `get_agente_creacion_callable`.
    """
    if _agente_creacion_callable is None:
        return "El agente de creación no fue inicializado con contexto."
    return _agente_creacion_callable(asunto, tipo)
