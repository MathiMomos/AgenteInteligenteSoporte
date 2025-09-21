# src/util_schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid

### Esquemas para Autenticación

class GoogleLoginRequest(BaseModel):
    """
    Define la estructura que esperamos del frontend con el token de id de Google.
    """
    id_token: str


class Token(BaseModel):
    """
    Define la estructura de la respuesta que nuestra API envía al frontend
    después de un login exitoso. Contiene nuestro propio token JWT.
    """
    access_token: str
    token_type: str


class ServicioInfo(BaseModel):
    """
    Una representación simple de un servicio contratado.
    """
    id_servicio: str
    nombre: str


class TokenData(BaseModel):
    """
    Define los datos que guardamos dentro de nuestro JWT.
    Es el "pasaporte" completo de un usuario Colaborador.
    """
    # --- IDs para la Lógica del Backend y las Herramientas ---
    persona_id: str
    colaborador_id: str
    cliente_id: str

    # --- Datos para la Conversación y Contexto del Agente ---
    nombre: str  # Viene de la tabla External
    correo: str  # Viene de la tabla External
    cliente_nombre: str  # Viene de la tabla Cliente

    servicios_contratados: List[ServicioInfo]


### Esquemas para el Chat

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

# === Esquemas para Analista (Bandeja & Detalle) ===

class AnalystMessage(BaseModel):
    role: str
    content: str

class AnalystTicketItem(BaseModel):
    id_ticket: int
    subject: str
    user: Optional[str] = None
    service: Optional[str] = None
    status: Optional[str] = None
    date: Optional[str] = None  # ISO o dd/mm/aaaa

class AnalystTicketPage(BaseModel):
    items: List[AnalystTicketItem]
    total: int
    limit: int
    offset: int

class AnalystTicketDetail(BaseModel):
    id_ticket: int
    subject: str
    type: Optional[str] = None
    user: Optional[str] = None
    company: Optional[str] = None
    service: Optional[str] = None
    email: Optional[str] = None
    date: Optional[str] = None
    status: Optional[str] = None
    conversation: List[AnalystMessage]

# En src/util/util_schemas.py

class DerivarTicketRequest(BaseModel):
    motivo: str = Field(..., min_length=10, description="El motivo por el cual se deriva el ticket.")
