import uuid
import datetime
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy.orm import aliased
from sqlalchemy import select
from sqlalchemy import func
from src.util import util_base_de_datos as db
from src.util import util_schemas as sch


def get_analyst_id_for_current_user_or_default(db_session: Session, user_info: sch.TokenData):
    """
    Si el usuario autenticado es Analista, devuelve su id_analista.
    Si no, devuelve el analista por defecto buscando por nombre "Ana Lytics".
    """
    # 1) Intentar con el usuario actual (si fuese analista)
    try:
        persona_uuid = uuid.UUID(user_info.persona_id)
    except Exception:
        persona_uuid = None

    if persona_uuid:
        analista = db_session.query(db.Analista).filter(db.Analista.id_persona == persona_uuid).first()
        if analista:
            return analista.id_analista

    # 2) Fallback: Analista por defecto (buscar por nombre insensible a mayúsculas)
    ext = db_session.query(db.External).filter(db.External.nombre.ilike("Ana Lytics")).first()
    if ext and getattr(ext, "persona", None):
        analista_def = db_session.query(db.Analista).filter(db.Analista.id_persona == ext.persona.id_persona).first()
        if analista_def:
            return analista_def.id_analista

    return None


def get_tickets_by_analyst(
    db_session: Session,
    analyst_id,
    limit: int = 20,
    offset: int = 0,
    estados: Optional[List[str]] = None,
):
    """
    Devuelve tickets asignados a un analista específico, paginados.
    (Solo Tickets; la hidratación masiva se hace con hydrate_ticket_page para evitar N+1).
    """
    base_q = db_session.query(db.Ticket).filter(db.Ticket.id_analista == analyst_id)
    if estados:
        base_q = base_q.filter(db.Ticket.estado.in_(estados))

    total = base_q.count()
    rows = base_q.order_by(db.Ticket.updated_at.desc()).limit(limit).offset(offset).all()
    return rows, total


def get_ticket_admin_by_id(db_session: Session, ticket_id: int):
    """
    Devuelve un Ticket por id (sin filtrar por colaborador).
    """
    return db_session.query(db.Ticket).filter(db.Ticket.id_ticket == ticket_id).first()


def get_conversation_by_ticket(db_session: Session, ticket_id: int):
    """
    Devuelve la fila de Conversacion asociada a un ticket (si existe).
    """
    return db_session.query(db.Conversacion).filter(db.Conversacion.id_ticket == ticket_id).first()


def hydrate_ticket_info(db_session: Session, ticket: db.Ticket):
    """
    Hidratación para un (1) ticket — útil para la pantalla de detalle.
    (Deja la versión original; para listas usa hydrate_ticket_page).
    """
    info = {
        "id_ticket": ticket.id_ticket,
        "subject": getattr(ticket, "asunto", None),
        "status": getattr(ticket, "estado", None),
        "type": getattr(ticket, "tipo", None),
        "date": None,
        "updated_at": getattr(ticket, "updated_at", None),
        "user": None,
        "email": None,
        "company": None,
        "service": None,
        "level": getattr(ticket, "nivel", None),  # <- nuevo
    }

    # Fecha (created_at)
    created_at = getattr(ticket, "created_at", None)
    if isinstance(created_at, (datetime.datetime, datetime.date)):
        info["date"] = created_at.strftime("%d/%m/%Y")

    # Usuario (colaborador -> persona -> external.nombre/correo) y Empresa (cliente)
    colaborador = db_session.query(db.Colaborador).filter(db.Colaborador.id_colaborador == ticket.id_colaborador).first()
    if colaborador:
        external = db_session.query(db.External).filter(db.External.id_persona == colaborador.id_persona).first()
        if external:
            info["user"] = getattr(external, "nombre", None)
            info["email"] = getattr(external, "correo", None)
        cliente = db_session.query(db.Cliente).filter(db.Cliente.id_cliente == colaborador.id_cliente).first()
        if cliente:
            info["company"] = getattr(cliente, "nombre", None)

    # Servicio
    cs = db_session.query(db.ClienteServicio).filter(
        db.ClienteServicio.id_cliente_servicio == ticket.id_cliente_servicio
    ).first()
    if cs:
        servicio = db_session.query(db.Servicio).filter(db.Servicio.id_servicio == cs.id_servicio).first()
        if servicio:
            info["service"] = getattr(servicio, "nombre", None)

    return info


# ========= NUEVO =========
def hydrate_ticket_page(db_session: Session, tickets: List[db.Ticket]) -> List[dict]:
    """
    Hidratación masiva para una página de tickets (evita N+1).
    Hace 2 queries en bloque y luego arma los dicts.
    """
    if not tickets:
        return []

    # --- Recolectar ids a buscar en bloque ---
    colab_ids = {t.id_colaborador for t in tickets if getattr(t, "id_colaborador", None)}
    cs_ids = {t.id_cliente_servicio for t in tickets if getattr(t, "id_cliente_servicio", None)}

    # --- Mapa de colaborador -> (user, email, company) ---
    # outerjoin para no perder filas si algo faltase
    Col = db.Colaborador
    Ext = db.External
    Cli = db.Cliente

    colab_rows = (
        db_session.query(
            Col.id_colaborador,
            Ext.nombre.label("user"),
            Ext.correo.label("email"),
            Cli.nombre.label("company"),
        )
        .outerjoin(Ext, Ext.id_persona == Col.id_persona)
        .outerjoin(Cli, Cli.id_cliente == Col.id_cliente)
        .filter(Col.id_colaborador.in_(colab_ids)) if colab_ids else []
    )
    colab_map = {r.id_colaborador: {"user": r.user, "email": r.email, "company": r.company} for r in colab_rows}

    # --- Mapa de cliente_servicio -> service ---
    CS = db.ClienteServicio
    Srv = db.Servicio
    cs_rows = (
        db_session.query(
            CS.id_cliente_servicio,
            Srv.nombre.label("service"),
        )
        .outerjoin(Srv, Srv.id_servicio == CS.id_servicio)
        .filter(CS.id_cliente_servicio.in_(cs_ids)) if cs_ids else []
    )
    service_map = {r.id_cliente_servicio: r.service for r in cs_rows}

    # --- Armar respuesta final por ticket ---
    resp: List[dict] = []
    for t in tickets:
        info = {
            "id_ticket": t.id_ticket,
            "subject": getattr(t, "asunto", None),
            "status": getattr(t, "estado", None),
            "type": getattr(t, "tipo", None),
            "date": None,
            "updated_at": getattr(t, "updated_at", None),
            "user": None,
            "email": None,
            "company": None,
            "service": None,
        }

        created_at = getattr(t, "created_at", None)
        if isinstance(created_at, (datetime.datetime, datetime.date)):
            info["date"] = created_at.strftime("%d/%m/%Y")

        c = colab_map.get(getattr(t, "id_colaborador", None))
        if c:
            info["user"] = c.get("user")
            info["email"] = c.get("email")
            info["company"] = c.get("company")

        svc = service_map.get(getattr(t, "id_cliente_servicio", None))
        if svc:
            info["service"] = svc

        resp.append(info)

    return resp
# ======== FIN NUEVO ========


def update_ticket_status_db(
    db_session: Session,
    ticket_id: int,
    new_status: str,
    description: Optional[str] = None,
):
    """
    Actualiza el estado de un ticket. Si new_status == 'finalizado':
    - setea closed_at
    - guarda 'description' en ticket.diagnostico (si viene)
    """
    ticket = (
        db_session.query(db.Ticket)
        .filter(db.Ticket.id_ticket == ticket_id)
        .first()
    )
    if not ticket:
        return None

    ticket.estado = new_status
    ticket.updated_at = datetime.datetime.utcnow()

    if new_status == "finalizado":
        ticket.closed_at = datetime.datetime.utcnow()
        if description:
            ticket.diagnostico = description[:5000]

    db_session.commit()
    db_session.refresh(ticket)
    return ticket

def find_random_higher_level_analyst(db_session: Session, current_analyst_id: str):
    """
    Busca un analista aleatorio de un nivel superior al actual.
    """
    # 1. Obtener el nivel del analista actual
    current_analyst = db_session.query(db.Analista).filter(
        db.Analista.id_analista == current_analyst_id
    ).first()

    if not current_analyst:
        return None

    # 2. Pedir a la base de datos que busque candidatos de nivel superior,
    # los ordene aleatoriamente y nos dé el primero que encuentre.
    return db_session.query(db.Analista).filter(
        db.Analista.nivel > current_analyst.nivel
    ).order_by(func.random()).first()


# En src/crud/crud_analista.py

def get_analyst_from_token(db_session: Session, current_user: sch.TokenData) -> db.Analista | None:
    """
    Busca y devuelve el objeto Analista completo a partir de la información
    del token del usuario actual.
    """
    if not current_user.persona_id:
        return None

    # Buscamos en la tabla Analista usando el id_persona que está en el token
    analyst = db_session.query(db.Analista).filter(
        db.Analista.id_persona == current_user.persona_id
    ).first()

    return analyst
def update_ticket_level_db(
    db_session: Session,
    ticket_id: int,
    new_level: str,
):
    """
    Actualiza el nivel (prioridad) de un ticket.
    """
    ticket = (
        db_session.query(db.Ticket)
        .filter(db.Ticket.id_ticket == ticket_id)
        .first()
    )
    if not ticket:
        return None

    # Actualizamos el nivel y la fecha de modificación
    ticket.nivel = new_level
    ticket.updated_at = datetime.datetime.utcnow()

    db_session.commit()
    db_session.refresh(ticket)
    return ticket
