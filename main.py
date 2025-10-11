# src/main.py
import uuid
import os
from typing import List, Optional
import unicodedata

from fastapi import FastAPI, Depends, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.agente import agente_principal

# --- Módulos del proyecto ---
from src.util import util_schemas as sch
from src.util import util_base_de_datos as db_utils
from src.auth import security
from src.crud import crud_users
from src.crud import crud_tickets
from src.crud import crud_analista
from src.crud import crud_escalados

# --- Google ---
from google.oauth2 import id_token
from google.auth.transport import requests as grequests

# ------------------------------------------------------------------
# Estados que llegan desde la UI → mapeo a valores del ENUM en la BD
# ------------------------------------------------------------------
def _norm(s: str) -> str:
    import unicodedata
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower())
        if unicodedata.category(c) != "Mn"
    ).strip()

# UI → BD (tal como llegan desde el front, con o sin acentos)
UI_TO_DB_STATUS = {
    "abierto": "aceptado",
    "en atención": "en atención",
    "en atencion": "en atención",
    "cerrado": "finalizado",
    "rechazado": "cancelado",
    "cancelado": "cancelado",
}

# Versión normalizada del mapa (CLAVE!)
UI_TO_DB_STATUS_N = { _norm(k): v for k, v in UI_TO_DB_STATUS.items() }

# Para filtros (UI → lista de estados en BD)
STATUS_TO_DB = {
    "abierto": ["aceptado"],
    "en atencion": ["en atención"],
    "cerrado": ["finalizado"],
    "rechazado": ["cancelado"],
}

# Lo permitdo en UI (normalizado)
ALLOWED_UI_STATUS = set(UI_TO_DB_STATUS_N.keys())
UI_TO_DB_LEVEL = {
    "bajo": "bajo",
    "medio": "medio",
    "alto": "alto",
    "critico": "crítico",
    "crítico": "crítico",
}
UI_TO_DB_LEVEL_N = { _norm(k): v for k, v in UI_TO_DB_LEVEL.items() }
ALLOWED_UI_LEVELS = set(UI_TO_DB_LEVEL_N.keys())
app = FastAPI(
    title="API de Agente Inteligente de Soporte",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:9002", "https://soporte-pi.vercel.app"],
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
    db: Session = Depends(db_utils.obtener_bd),
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

        servicios_contratados_db = (
            db.query(db_utils.Servicio)
            .join(db_utils.ClienteServicio)
            .filter(db_utils.ClienteServicio.id_cliente == colaborador.id_cliente)
            .all()
        )

        servicios_para_token = [
            sch.ServicioInfo(id_servicio=str(s.id_servicio), nombre=s.nombre)
            for s in servicios_contratados_db
        ]

        token_data_payload = sch.TokenData(
            correo=external_info.correo,
            nombre=external_info.nombre,
            persona_id=str(persona.id_persona),
            colaborador_id=str(colaborador.id_colaborador),
            cliente_id=str(colaborador.id_cliente),
            cliente_nombre=cliente.nombre if cliente else "Cliente Desconocido",
            servicios_contratados=servicios_para_token
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
            servicios_contratados=[]
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
    db: Session = Depends(db_utils.obtener_bd),
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
    status: Optional[str] = Query(None, description="Abierto | En Atención | Cerrado | Rechazado | Todos"),
    db: Session = Depends(db_utils.obtener_bd),
    current_user: sch.TokenData = Depends(security.get_current_user),
):
    analyst_id = crud_analista.get_analyst_id_for_current_user_or_default(db, current_user)
    if not analyst_id:
        return sch.AnalystTicketPage(items=[], total=0, limit=limit, offset=offset)

    estados_bd = None
    if status:
        s = _norm(status)
        if s != "todos":
            if s not in STATUS_TO_DB:
                raise HTTPException(status_code=400, detail="Estado inválido.")
            estados_bd = STATUS_TO_DB[s]

    rows, total = crud_analista.get_tickets_by_analyst(
        db, analyst_id, limit=limit, offset=offset, estados=estados_bd
    )

    infos = crud_analista.hydrate_ticket_page(db, rows)

    items: List[sch.AnalystTicketItem] = [
        sch.AnalystTicketItem(
            id_ticket=info["id_ticket"],
            subject=info["subject"] or "",
            user=info["user"],
            service=info["service"],
            status=info["status"],
            date=info["date"],
        )
        for info in infos
    ]

    return sch.AnalystTicketPage(items=items, total=total, limit=limit, offset=offset)

@app.get("/api/analista/conversaciones/{id_ticket}", response_model=sch.AnalystTicketDetail, tags=["Analista"])
def detalle_conversacion_analista(
    id_ticket: int,
    db: Session = Depends(db_utils.obtener_bd),
    current_user: sch.TokenData = Depends(security.get_current_user),
):
    t = crud_analista.get_ticket_admin_by_id(db, id_ticket)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    info = crud_analista.hydrate_ticket_info(db, t)

    conv = crud_analista.get_conversation_by_ticket(db, id_ticket)
    conversation = []
    if conv and getattr(conv, "contenido", None):
        conversation = [sch.AnalystMessage(**m) for m in conv.contenido] if conv and conv.contenido else []

    return sch.AnalystTicketDetail(**info, conversation=conversation)

# -------------------------
# Cambiar estado y nivel de ticket
# -------------------------

# =======================================================================
# FUNCIÓN AÑADIDA PARA CORREGIR EL ERROR
# =======================================================================
@app.put("/api/analista/tickets/{ticket_id}/status", response_model=sch.AnalystTicketDetail, tags=["Analista"])
def update_ticket_status(
        ticket_id: int,
        payload: sch.UpdateTicketStatusRequest,  # status obligatorio; description/level opcionales
        db: Session = Depends(db_utils.obtener_bd),
        current_user: sch.TokenData = Depends(security.get_current_user),
):
    analyst_id = crud_analista.get_analyst_id_for_current_user_or_default(db, current_user)
    if not analyst_id:
        raise HTTPException(status_code=403, detail="No autorizado (no es analista).")

    ticket = crud_analista.get_ticket_admin_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado.")

    if ticket.id_analista != analyst_id:
        raise HTTPException(status_code=403, detail="No autorizado para modificar este ticket.")

    # 1) Actualizar ESTADO
    db_status = UI_TO_DB_STATUS_N.get(_norm(payload.status))
    if not db_status:
        raise HTTPException(status_code=400, detail="Estado no permitido.")
    updated_ticket = crud_analista.update_ticket_status_db(
        db_session=db,
        ticket_id=ticket_id,
        new_status=db_status,
        description=payload.description if db_status == "finalizado" else None,
    )
    if not updated_ticket:
        raise HTTPException(status_code=500, detail="No se pudo actualizar el estado.")

    # 2) (Opcional) Actualizar NIVEL si vino en el payload
    if payload.level:
        db_level = UI_TO_DB_LEVEL_N.get(_norm(payload.level))
        if not db_level:
            raise HTTPException(status_code=400, detail="Nivel no permitido. Use: Bajo, Medio, Alto o Crítico.")
        updated_ticket = crud_analista.update_ticket_level_db(
            db_session=db,
            ticket_id=ticket_id,
            new_level=db_level,
        )
        if not updated_ticket:
            raise HTTPException(status_code=500, detail="No se pudo actualizar el nivel.")

    # 3) Responder hidratado
    info = crud_analista.hydrate_ticket_info(db, updated_ticket)
    conv = crud_analista.get_conversation_by_ticket(db, ticket_id)
    conversation = [sch.AnalystMessage(**m) for m in conv.contenido] if conv and conv.contenido else []
    return sch.AnalystTicketDetail(**info, conversation=conversation)

# =======================================================================

@app.put("/api/analista/tickets/{ticket_id}/derivar", response_model=sch.AnalystTicketDetail, tags=["Analista"])
def derivar_ticket(
        ticket_id: int,
        payload: sch.DerivarTicketRequest,
        db: Session = Depends(db_utils.obtener_bd),
        current_user: sch.TokenData = Depends(security.get_current_user),
):
    current_analyst = crud_analista.get_analyst_from_token(db, current_user)
    if not current_analyst:
        raise HTTPException(status_code=403, detail="No autorizado (no es analista).")

    if current_analyst.nivel >= 3:
        raise HTTPException(
            status_code=403,
            detail="Acción no permitida. Los analistas de nivel 3 son el último nivel de escalado."
        )

    ticket = crud_analista.get_ticket_admin_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado.")
    if ticket.id_analista != current_analyst.id_analista:
        raise HTTPException(status_code=403,
                            detail="No está autorizado para derivar un ticket que no está asignado a usted.")

    new_analyst = crud_analista.find_random_higher_level_analyst(db, current_analyst.id_analista)
    if not new_analyst:
        raise HTTPException(status_code=409, detail="No se encontraron analistas de nivel superior disponibles.")

    crud_tickets.reassign_ticket_db(db, ticket, new_analyst.id_analista)

    crud_escalados.log_escalation_db(
        db_session=db,
        ticket_id=ticket_id,
        solicitante_id=current_analyst.id_analista,
        derivado_id=new_analyst.id_analista,
        motivo=payload.motivo,
    )

    db.commit()
    db.refresh(ticket)

    print(f"Ticket #{ticket_id} derivado por {current_user.nombre} a {new_analyst.id_analista} por motivo: {payload.motivo}")

    info = crud_analista.hydrate_ticket_info(db, ticket)
    conv = crud_analista.get_conversation_by_ticket(db, ticket_id)
    conversation = [sch.AnalystMessage(**m) for m in conv.contenido] if conv and conv.contenido else []

    return sch.AnalystTicketDetail(**info, conversation=conversation)