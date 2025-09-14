# src/main.py
import uuid
import os
from typing import List

from fastapi import FastAPI, Depends, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# --- Módulos del proyecto ---
from src.util import util_schemas as sch
from src.util import util_base_de_datos as db_utils
from src.agente import agente_principal
from src.auth import security
from src.crud import crud_users
from src.crud import crud_tickets

# --- Google ---
from google.oauth2 import id_token
from google.auth.transport import requests as grequests

# ------------------------------------------------------------------
# Estados que llegan desde la UI → mapeo a valores del ENUM en la BD
# ------------------------------------------------------------------
UI_TO_DB_STATUS = {
    "abierto": "aceptado",
    "en atención": "en atención",
    "en atencion": "en atención",
    "rechazado": "rechazado",
    "cancelado": "cancelado",
    "cerrado": "finalizado",
}
ALLOWED_UI_STATUS = set(UI_TO_DB_STATUS.keys())

# -------------------------
# Inicialización de la app
# -------------------------
app = FastAPI(
    title="API de Agente Inteligente de Soporte",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:9002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Auth con Google (backend)
# -------------------------
@app.post("/api/auth/google/login", response_model=sch.Token, tags=["Auth"])
async def google_login(
    request: sch.GoogleLoginRequest,
    db: Session = Depends(db_utils.get_db),
):
    google_client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not google_client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID no configurado")

    # 1) Verificar id_token de Google
    try:
        id_info = id_token.verify_oauth2_token(
            request.id_token, grequests.Request(), google_client_id
        )
        if id_info.get("iss") not in (
            "accounts.google.com",
            "https://accounts.google.com",
        ):
            raise HTTPException(status_code=401, detail="Issuer inválido")
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Token de Google inválido: {e}")

    # 2) Persona / External
    persona = crud_users.get_or_create_from_external(db_session=db, id_info=id_info)
    external_info = (
        db.query(db_utils.External)
        .filter(db_utils.External.id_persona == persona.id_persona)
        .first()
    )
    if not external_info:
        raise HTTPException(
            status_code=500,
            detail="No se encontró información externa asociada a la persona.",
        )

    # 3) Colaborador → token normal
    colaborador = (
        db.query(db_utils.Colaborador)
        .filter(db_utils.Colaborador.id_persona == persona.id_persona)
        .first()
    )
    if colaborador:
        cliente = (
            db.query(db_utils.Cliente)
            .filter(db_utils.Cliente.id_cliente == colaborador.id_cliente)
            .first()
        )
        token_data_payload = sch.TokenData(
            correo=external_info.correo,
            nombre=external_info.nombre,
            persona_id=str(persona.id_persona),
            colaborador_id=str(colaborador.id_colaborador),
            cliente_id=str(colaborador.id_cliente),
            cliente_nombre=cliente.nombre if cliente else "Cliente Desconocido",
        )
        access_token = security.create_access_token(data=token_data_payload)
        return {"access_token": access_token, "token_type": "bearer"}

    # 4) Analista → token como analista
    analista = (
        db.query(db_utils.Analista)
        .filter(db_utils.Analista.id_persona == persona.id_persona)
        .first()
    )
    if analista:
        token_data_payload = sch.TokenData(
            correo=external_info.correo,
            nombre=external_info.nombre,
            persona_id=str(persona.id_persona),
            colaborador_id="00000000-0000-0000-0000-000000000000",
            cliente_id="00000000-0000-0000-0000-000000000000",
            cliente_nombre="ANALYTICS",
        )
        access_token = security.create_access_token(data=token_data_payload)
        return {"access_token": access_token, "token_type": "bearer"}

    # 5) Ni colaborador ni analista
    raise HTTPException(
        status_code=403,
        detail="Acceso denegado. Este usuario no está registrado como colaborador ni como analista.",
    )

# -------------------------
# Chat
# -------------------------
@app.post("/api/chat", response_model=sch.ChatResponse, tags=["Chatbot"])
async def chat_with_agent(
    request: sch.ChatRequest,
    db: Session = Depends(db_utils.get_db),
    current_user: sch.TokenData = Depends(security.get_current_user),
):
    thread_id = request.thread_id or str(uuid.uuid4())

    print(
        f"[THREAD {thread_id}] Chat iniciado por: {current_user.nombre} de la empresa {current_user.cliente_nombre}"
    )
    print(f"DEBUG - colaborador_id en TokenData: {current_user.colaborador_id}")

    response_text = agente_principal.handle_query(
        query=request.query, thread_id=thread_id, user_info=current_user, db=db
    )
    return sch.ChatResponse(response=response_text, thread_id=thread_id)

@app.get("/", tags=["Root"])
def root():
    return {"message": "API del Agente Inteligente de Soporte funcionando."}

# -------------------------
# Rutas para Analista
# -------------------------
@app.get("/api/analista/conversaciones", response_model=sch.AnalystTicketPage, tags=["Analista"])
def listar_conversaciones_analista(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(db_utils.get_db),
    current_user: sch.TokenData = Depends(security.get_current_user),
):
    """
    Lista paginada de tickets asignados al analista actual.
    Si el usuario no es analista, se usa el analista por defecto (Ana Lytics).
    """
    analyst_id = crud_tickets.get_analyst_id_for_current_user_or_default(db, current_user)
    if not analyst_id:
        return sch.AnalystTicketPage(items=[], total=0, limit=limit, offset=offset)

    rows, total = crud_tickets.get_tickets_by_analyst(db, analyst_id, limit=limit, offset=offset)

    items: List[sch.AnalystTicketItem] = []
    for t in rows:
        info = crud_tickets.hydrate_ticket_info(db, t)
        items.append(
            sch.AnalystTicketItem(
                id_ticket=info["id_ticket"],
                subject=info["subject"] or "",
                user=info["user"],
                service=info["service"],
                status=info["status"],
                date=info["date"],
            )
        )

    return sch.AnalystTicketPage(items=items, total=total, limit=limit, offset=offset)

@app.get("/api/analista/conversaciones/{id_ticket}", response_model=sch.AnalystTicketDetail, tags=["Analista"])
def detalle_conversacion_analista(
    id_ticket: int,
    db: Session = Depends(db_utils.get_db),
    current_user: sch.TokenData = Depends(security.get_current_user),
):
    """
    Devuelve el detalle del ticket y el hilo de conversación guardado.
    """
    t = crud_tickets.get_ticket_admin_by_id(db, id_ticket)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    info = crud_tickets.hydrate_ticket_info(db, t)

    conv = crud_tickets.get_conversation_by_ticket(db, id_ticket)
    conversation = []
    if conv and getattr(conv, "contenido", None):
        conversation = [sch.AnalystMessage(**m) for m in conv.contenido]

    return sch.AnalystTicketDetail(
        id_ticket=info["id_ticket"],
        subject=info["subject"] or "",
        type=info["type"],
        user=info["user"],
        company=info["company"],
        service=info["service"],
        email=info["email"],
        date=info["date"],
        status=info["status"],
        conversation=conversation,
    )

# -------------------------
# Cambiar estado de ticket
# -------------------------
@app.put("/api/analista/tickets/{ticket_id}/status", tags=["Analista"])
def update_ticket_status(
    ticket_id: int,
    payload: dict = Body(...),
    db: Session = Depends(db_utils.get_db),
    current_user: sch.TokenData = Depends(security.get_current_user),
):
    new_status_ui = (payload or {}).get("status")
    description = (payload or {}).get("description")  # obligatorio sólo si Cerrado

    if not isinstance(new_status_ui, str):
        raise HTTPException(status_code=400, detail="Falta 'status'.")

    new_status_norm = new_status_ui.strip().lower()
    if new_status_norm not in ALLOWED_UI_STATUS:
        raise HTTPException(status_code=400, detail="Estado no permitido.")

    if new_status_norm == "cerrado":
        if not isinstance(description, str) or not description.strip():
            raise HTTPException(status_code=400, detail="La descripción es obligatoria para cerrar el ticket.")

    db_status = UI_TO_DB_STATUS[new_status_norm]

    analyst_id = crud_tickets.get_analyst_id_for_current_user_or_default(db, current_user)
    if not analyst_id:
        raise HTTPException(status_code=403, detail="No autorizado (no es analista).")

    ticket = crud_tickets.get_ticket_admin_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado.")

    if ticket.id_analista != analyst_id:
        raise HTTPException(status_code=403, detail="No autorizado para modificar este ticket.")

    updated = crud_tickets.update_ticket_status_db(
        db_session=db,
        ticket_id=ticket_id,
        new_status=db_status,
        description=(description or "").strip() if new_status_norm == "cerrado" else None,
    )
    if not updated:
        raise HTTPException(status_code=500, detail="No se pudo actualizar el estado.")

    return {"ok": True, "status": updated.estado}
