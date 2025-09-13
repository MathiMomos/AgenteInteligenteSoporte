from langchain.tools import tool
from sqlalchemy.orm import Session
from src.util import util_schemas as sch
from src.crud import crud_tickets
from enum import Enum

# Definimos los tipos de ticket posibles
class TipoTicket(str, Enum):
    INCIDENCIA = "incidencia"
    SOLICITUD = "solicitud"

# Variable global donde se inyecta el contexto
_agente_creacion_callable = None

def get_agente_creacion_callable(db: Session, user_info: sch.TokenData):
    """
    Construye un callable especializado en creación de tickets con el contexto
    de la base de datos y el usuario autenticado.
    """
    def _crear_ticket(asunto: str, tipo: TipoTicket) -> str:
        try:
            ticket_creado = crud_tickets.create_ticket_db(
                db_session=db,
                asunto=asunto,
                tipo=tipo.value,
                user_info=user_info
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
