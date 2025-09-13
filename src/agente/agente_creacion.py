# src/agente/agente_creacion.py

from langchain.tools import tool
from sqlalchemy.orm import Session
from src.util import util_schemas as sch
from src.crud import crud_tickets
from enum import Enum

# Definimos los tipos de ticket posibles para que el LLM los conozca
class TipoTicket(str, Enum):
    INCIDENCIA = "incidencia"
    SOLICITUD = "solicitud"

@tool
def crear_ticket(asunto: str, tipo: TipoTicket, db: Session, user_info: sch.TokenData) -> str:
    """
    Usa esta herramienta para crear un nuevo ticket de soporte cuando ya no puedas ayudar al usuario
    con la base de conocimientos. Debes analizar la conversación para inferir el 'asunto' y el 'tipo'.
    'asunto' debe ser un resumen breve y claro del problema.
    'tipo' debe ser 'incidencia' si algo está roto o no funciona, o 'solicitud' si el usuario pide algo.
    """
    try:
        # Llama a la función CRUD para hacer el trabajo en la base de datos
        ticket_creado = crud_tickets.create_ticket_db(
            db=db,
            asunto=asunto,
            tipo=tipo.value, # Pasamos el valor del enum ('incidencia' o 'solicitud')
            user_info=user_info
        )
        # Devuelve una respuesta amigable para el usuario
        return (f"He generado el ticket #{ticket_creado.id_ticket} con el asunto '{asunto}'. "
                "Nuestro equipo de soporte se pondrá en contacto con usted por correo electrónico. "
                "Gracias por su paciencia. ✨")
    except Exception as e:
        print(f"Error en la herramienta 'crear_ticket': {e}")
        return "Lo siento, ocurrió un error inesperado al intentar crear su ticket. Ya he notificado al equipo técnico."