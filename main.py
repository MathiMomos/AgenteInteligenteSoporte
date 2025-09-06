from fastapi import FastAPI
from pydantic import BaseModel, Field
import uuid

# Importamos el middleware de CORS para permitir la conexión con el frontend
from fastapi.middleware.cors import CORSMiddleware

# Importamos la lógica de nuestro agente
from src.agente import agente_principal

# Creamos la instancia de la aplicación FastAPI
app = FastAPI(
    title="API de Agente Inteligente de Soporte",
    description="Un endpoint para interactuar con un agente conversacional basado en LangGraph.",
    version="1.0.0"
)

# --- Configuración de CORS ---
# Lista de orígenes permitidos (los dominios de tu frontend)
origins = [
    "http://localhost",
    "http://localhost:3000",  # Puerto común para desarrollo con React/Vue/etc.
    # En producción, añadirías aquí la URL de tu Azure Static Web App
    # "https://<TU_STATIC_WEB_APP>.azurestaticapps.net"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permite todas las cabeceras
)


# --- Modelos de Datos (Pydantic) ---
class ChatRequest(BaseModel):
    query: str = Field(..., description="El mensaje enviado por el usuario.")
    thread_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="El ID único de la conversación.")


class ChatResponse(BaseModel):
    response: str = Field(..., description="La respuesta generada por el agente.")
    thread_id: str = Field(..., description="El ID de la conversación para seguir el hilo.")


# --- Endpoints de la API ---
@app.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """
    Recibe un mensaje de un usuario y devuelve la respuesta del agente.
    Maneja el estado de la conversación usando el `thread_id`.
    """
    # Llamamos a la lógica del agente que ya está construida
    response_text = agente_principal.handle_query(request.query, request.thread_id)

    return ChatResponse(
        response=response_text,
        thread_id=request.thread_id
    )


@app.get("/")
async def root():
    """
    Endpoint raíz para verificar que el servidor está funcionando.
    """
    return {
        "message": "Bienvenido a la API del Agente Inteligente de Soporte. Usa el endpoint /docs para ver la documentación."}