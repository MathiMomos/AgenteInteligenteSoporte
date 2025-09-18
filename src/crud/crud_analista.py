import uuid
import datetime
from typing import Optional

from sqlalchemy.orm import Session
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


def get_tickets_by_analyst(db_session: Session, analyst_id, limit: int = 20, offset: int = 0):
    """
    Devuelve tickets asignados a un analista específico, paginados.
    """
    base_q = db_session.query(db.Ticket).filter(db.Ticket.id_analista == analyst_id)
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
    Devuelve un dict con campos listos para el front del analista:
    subject, user, email, company, service, status, date, type.
    """
    info = {
        "id_ticket": ticket.id_ticket,
        "subject": getattr(ticket, "asunto", None),
        "status": getattr(ticket, "estado", None),
        "type": getattr(ticket, "tipo", None),
        "date": None,
        "user": None,
        "email": None,
        "company": None,
        "service": None,
    }

    # Fecha (created_at)
    created_at = getattr(ticket, "created_at", None)
    if isinstance(created_at, (datetime.datetime, datetime.date)):
        info["date"] = created_at.strftime("%d/%m/%Y")

    # Usuario (colaborador -> persona -> external.nombre/correo)
    colaborador = db_session.query(db.Colaborador).filter(db.Colaborador.id_colaborador == ticket.id_colaborador).first()
    if colaborador:
        external = db_session.query(db.External).filter(db.External.id_persona == colaborador.id_persona).first()
        if external:
            info["user"] = getattr(external, "nombre", None)
            info["email"] = getattr(external, "correo", None)
        # Empresa (cliente)
        cliente = db_session.query(db.Cliente).filter(db.Cliente.id_cliente == colaborador.id_cliente).first()
        if cliente:
            info["company"] = getattr(cliente, "nombre", None)

    # Servicio (cliente_servicio -> servicio)
    cs = db_session.query(db.ClienteServicio).filter(
        db.ClienteServicio.id_cliente_servicio == ticket.id_cliente_servicio
    ).first()
    if cs:
        servicio = db_session.query(db.Servicio).filter(db.Servicio.id_servicio == cs.id_servicio).first()
        if servicio:
            info["service"] = getattr(servicio, "nombre", None)

    return info


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