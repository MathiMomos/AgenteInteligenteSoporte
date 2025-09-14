import uuid
import datetime

from sqlalchemy.orm import Session
from src.util import util_base_de_datos as db
from src.util import util_schemas as sch


def create_ticket_db(db_session: Session, asunto: str, tipo: str, user_info: sch.TokenData) -> db.Ticket:
    """
    Crea un nuevo registro de Ticket en la base de datos.
    """
    # Lógica de negocio para determinar el servicio contratado por el cliente.
    # Para la demo, podemos asumir que el ticket se crea sobre el primer
    # servicio que encontremos para la empresa del colaborador.
    cliente_servicio = db_session.query(db.ClienteServicio).filter(
        db.ClienteServicio.id_cliente == user_info.cliente_id
    ).first()

    if not cliente_servicio:
        raise ValueError("El cliente asociado a este colaborador no tiene servicios contratados.")

    # --- Asignación por defecto al analista "Ana Lytics" (búsqueda por nombre, insensible a mayúsculas) ---
    analyst_id = None
    try:
        default_analyst = db_session.query(db.External).filter(
            db.External.nombre.ilike("Ana Lytics")
        ).first()
        if default_analyst and getattr(default_analyst, "persona", None):
            analista = db_session.query(db.Analista).filter(
                db.Analista.id_persona == default_analyst.persona.id_persona
            ).first()
            if analista:
                analyst_id = analista.id_analista
    except Exception:
        # Si algo falla, simplemente dejamos analyst_id = None (sin romper el flujo)
        analyst_id = None

    new_ticket = db.Ticket(
        asunto=asunto,
        tipo=tipo,
        id_colaborador=user_info.colaborador_id,
        id_cliente_servicio=cliente_servicio.id_cliente_servicio,
        nivel='medio',
        estado='aceptado',
        id_analista=analyst_id  # <-- asignación por defecto (si se encontró)
    )
    db_session.add(new_ticket)
    db_session.commit()
    db_session.refresh(new_ticket)
    return new_ticket


def save_conversation_db(db_session: Session, ticket_id: int, conversation: list[dict]):
    """
    Guarda la conversación en la tabla `conversacion` asociada a un ticket.
    """
    new_conversacion = db.Conversacion(
        id_ticket=ticket_id,
        contenido=conversation
    )
    db_session.add(new_conversacion)
    db_session.commit()
    db_session.refresh(new_conversacion)
    return new_conversacion


def get_ticket_by_id_db(db_session: Session, ticket_id: int, user_info: sch.TokenData) -> db.Ticket | None:
    """
    Busca un ticket por su ID, asegurándose de que pertenezca al colaborador
    que realiza la consulta.
    """
    try:
        colaborador_uuid = uuid.UUID(user_info.colaborador_id)  # convertir str → UUID
    except Exception:
        return None

    ticket = db_session.query(db.Ticket).filter(
        db.Ticket.id_ticket == ticket_id,
        db.Ticket.id_colaborador == colaborador_uuid
    ).first()

    # ✅ corregido: usar la variable correcta
    print(f"DEBUG - buscando ticket {ticket_id} con colaborador {colaborador_uuid}")

    return ticket

def get_all_open_tickets(db_session: Session, user_info: sch.TokenData) -> list[db.Ticket]:
    """
    Devuelve todos los tickets abiertos (no finalizados) del colaborador actual.
    """
    try:
        colaborador_uuid = uuid.UUID(user_info.colaborador_id)
    except Exception:
        return []

    return db_session.query(db.Ticket).filter(
        db.Ticket.id_colaborador == colaborador_uuid,
        db.Ticket.estado != "finalizado"
    ).all()


def get_tickets_by_subject(db_session: Session, subject: str, user_info: sch.TokenData) -> list[db.Ticket]:
    """
    Busca tickets por coincidencia parcial en el asunto, para el colaborador actual.
    """
    try:
        colaborador_uuid = uuid.UUID(user_info.colaborador_id)
    except Exception:
        return []

    return db_session.query(db.Ticket).filter(
        db.Ticket.id_colaborador == colaborador_uuid,
        db.Ticket.asunto.ilike(f"%{subject}%")
    ).all()


# ===================== HELPERS PARA EL MÓDULO DE ANALISTA =====================

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
