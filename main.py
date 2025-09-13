# src/main.py

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
import os

# --- Importaciones de nuestros módulos ---
from src.util import util_schemas as sch
from src.util import util_base_de_datos as db_utils
from src.agente import agente_principal
from src.auth import security
from src.crud import crud_users

# --- Importaciones de Google ---
from google.oauth2 import id_token
from google.auth.transport import requests as grequests

# --- Inicialización de la App ---
app = FastAPI(
    title="API de Agente Inteligente de Soporte",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:9002"],  # Añade todos los puertos que use tu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


### Endpoint de Autenticación con Google ###
@app.post("/api/auth/google/login", response_model=sch.Token, tags=["Auth"])
async def google_login(
        request: sch.GoogleLoginRequest,
        db: Session = Depends(db_utils.get_db)
):
    """
    Recibe un id_token de Google desde el frontend, lo verifica,
    gestiona al usuario en la BD y devuelve un token de sesión propio.
    """
    google_client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not google_client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID no configurado")

    try:
        id_info = id_token.verify_oauth2_token(request.id_token, grequests.Request(), google_client_id)
        if id_info.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
            raise HTTPException(status_code=401, detail="Issuer inválido")
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Token de Google inválido: {e}")

    # 1. Llama al CRUD para obtener o crear la Persona
    persona = crud_users.get_or_create_from_external(db_session=db, id_info=id_info)

    # 2. Reúne toda la información necesaria para el token
    colaborador = db.query(db_utils.Colaborador).filter(db_utils.Colaborador.id_persona == persona.id_persona).first()

    if not colaborador:
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado. Este usuario no está registrado como colaborador de un cliente activo."
        )

    # Obtenemos el cliente a través del colaborador
    cliente = db.query(db_utils.Cliente).filter(db_utils.Cliente.id_cliente == colaborador.id_cliente).first()

    # Obtenemos el nombre y correo de la tabla External, como aclaramos
    external_info = db.query(db_utils.External).filter(db_utils.External.id_persona == persona.id_persona).first()

    # 3. Prepara el "pasaporte" (TokenData) con todos los datos
    token_data_payload = sch.TokenData(
        email=external_info.correo,
        nombre=external_info.nombre,
        persona_id=str(persona.id_persona),
        colaborador_id=str(colaborador.id_colaborador),
        cliente_id=str(colaborador.id_cliente),
        cliente_nombre=cliente.nombre if cliente else "Cliente Desconocido"
    )

    # 4. Crea nuestro token de sesión
    access_token = security.create_access_token(data=token_data_payload)

    # 5. Devuelve el token al frontend
    return {"access_token": access_token, "token_type": "bearer"}


### Endpoints de la Aplicación ###
@app.post("/api/chat", response_model=sch.ChatResponse, tags=["Chatbot"])
async def chat_with_agent(
    request: sch.ChatRequest,
    db: Session = Depends(db_utils.get_db),
    current_user: sch.TokenData = Depends(security.get_current_user)
):
    print(f"Chat iniciado por: {current_user.nombre} de la empresa {current_user.cliente_nombre}")
    response_text = agente_principal.handle_query(
        query=request.query,
        thread_id=request.thread_id,
        user_info=current_user,
        db=db
    )
    return sch.ChatResponse(response=response_text, thread_id=request.thread_id)


@app.get("/", tags=["Root"])
def root():
    return {"message": "API del Agente Inteligente de Soporte funcionando."}