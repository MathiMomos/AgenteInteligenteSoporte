# src/util/util_schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
import datetime


### Esquemas para Autenticación

# ¡NUEVO! Esquema para el login de usuario/contraseña
class UserPassLoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    """
    La respuesta de nuestro login: un JWT.
    (Se mantiene igual)
    """
    access_token: str
    token_type: str


# --- ¡NUEVO TOKEN DATA! ---
class TokenData(BaseModel):
    """
    Define los datos que guardamos dentro de nuestro JWT.
    Es el "pasaporte" de un usuario validado por GLPI.
    """
    # --- Datos de GLPI para el Contexto del Agente ---
    glpi_id: int
    nombre: str
    correo: str
    glpi_username: str
    glpi_entity_id: int
    glpi_entity_name: str

    # 'sub' (correo) y 'exp' (expiración) se añaden por separado


### Esquemas para el Chat
# (Se mantienen exactamente igual)

class ChatRequest(BaseModel):
    """
    Define la estructura de una petición al endpoint de chat.
    """
    message: str = Field(..., description="El mensaje enviado por el usuario.")

    # --- INICIO DE LA CORRECCIÓN ---
    # Cambiamos 'str = Field(default_factory...)'
    # por 'Optional[str] = Field(default=None...)'
    #
    # Esto le dice a Pydantic que 'thread_id' puede ser un string O puede ser nulo (None).
    thread_id: Optional[str] = Field(
        default=None,
        description="El ID único de la conversación. Enviar 'null' o 'None' si es el primer mensaje."
    )
    # --- FIN DE LA CORRECCIÓN ---


class ChatResponse(BaseModel):
    """
    Define la estructura de la respuesta del endpoint de chat.
    """
    response: str = Field(..., description="La respuesta generada por el agente.")
    thread_id: str = Field(..., description="El ID de la conversación para seguir el hilo.")

# (TODOS los demás esquemas de Analyst, Servicio, Cliente, etc., han sido eliminados)