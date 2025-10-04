import uuid
import datetime

from sqlalchemy.orm import Session
from src.util import util_base_de_datos as db
from src.util import util_schemas as sch

def create_ticket_db(
    db_session: Session,
    user_info: sch.TokenData,
    asunto: str,
    tipo: str,
    nivel: str,
    nombre_servicio: str
    ) -> db.Ticket:
    """
    Crea un nuevo Ticket. Se asegura de tener la informacíón completa.
    Asigna por defecto al analista 'Ana Lytics' si existe.
    """

    cliente_servicio = (
        db_session.query(db.ClienteServicio)
        .join(db.Servicio)  # Hacemos un JOIN con la tabla Servicio para poder filtrar por nombre
        .filter(
            db.ClienteServicio.id_cliente == user_info.cliente_id,
            db.Servicio.nombre.ilike(f"%{nombre_servicio}%")  # Búsqueda flexible por nombre
        )
        .first()
    )

    if not cliente_servicio:
        # Si la IA infiere un servicio que el cliente no tiene, lanzamos un error claro.
        raise ValueError(
            f"No se pudo encontrar el servicio '{nombre_servicio}' entre los servicios contratados por el cliente.")

    # Asignación por defecto a 'Ana Lytics' (si existe)
    analyst_id = None
    try:
        default_ext = db_session.query(db.External).filter(
            db.External.nombre.ilike("Ana Lytics")
        ).first()
        if default_ext and getattr(default_ext, "persona", None):
            ana = db_session.query(db.Analista).filter(
                db.Analista.id_persona == default_ext.persona.id_persona
            ).first()
            if ana:
                analyst_id = ana.id_analista
    except Exception:
        analyst_id = None

    new_ticket = db.Ticket(
        asunto=asunto,
        tipo=tipo,
        id_colaborador=user_info.colaborador_id,
        id_cliente_servicio=cliente_servicio.id_cliente_servicio,
        nivel=nivel,
        estado="aceptado",
        id_analista=analyst_id,
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

def get_all_tickets(db_session: Session, user_info: sch.TokenData) -> list[db.Ticket]:
    """
    Devuelve todos los tickets del colaborador actual.
    """
    try:
        colaborador_uuid = uuid.UUID(user_info.colaborador_id)
    except Exception:
        return []

    return db_session.query(db.Ticket).filter(
        db.Ticket.id_colaborador == colaborador_uuid
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

# ... (resto de tus funciones CRUD de tickets)

def reassign_ticket_db(db_session: Session, ticket: db.Ticket, new_analyst_id: str) -> db.Ticket:
    """Actualiza el id_analista de un ticket existente."""
    ticket.id_analista = new_analyst_id
    return ticket