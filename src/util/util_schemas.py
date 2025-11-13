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
    glpi_id: int  # ID de usuario en GLPI
    nombre: str  # Nombre completo (ej. "Juan Pérez")
    correo: str
    glpi_username: str  # El 'login' de GLPI (ej. 'jperez')

    # 'sub' (correo) y 'exp' (expiración) se añaden por separado


### Esquemas para el Chat
# (Se mantienen exactamente igual)

class ChatRequest(BaseModel):
    """
    Define la estructura de una petición al endpoint de chat.
    """
    query: str = Field(..., description="El mensaje enviado por el usuario.")
    thread_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="El ID único de la conversación para mantener el historial."
    )


class ChatResponse(BaseModel):
    """
    Define la estructura de la respuesta del endpoint de chat.
    """
    response: str = Field(..., description="La respuesta generada por el agente.")
    thread_id: str = Field(..., description="El ID de la conversación para seguir el hilo.")

# (TODOS los demás esquemas de Analyst, Servicio, Cliente, etc., han sido eliminados)