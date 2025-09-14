import uuid

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

    new_ticket = db.Ticket(
        asunto=asunto,
        tipo=tipo,
        id_colaborador=user_info.colaborador_id,
        id_cliente_servicio=cliente_servicio.id_cliente_servicio,
        nivel='medio',
        estado='aceptado'
    )
    db_session.add(new_ticket)
    db_session.commit()
    db_session.refresh(new_ticket)
    return new_ticket


def get_ticket_by_id_db(db_session: Session, ticket_id: int, user_info: sch.TokenData) -> db.Ticket | None:
    """
    Busca un ticket por su ID, asegurándose de que pertenezca al colaborador
    que realiza la consulta.
    """
    try:
        colaborador_uuid = uuid.UUID(user_info.colaborador_id)  # 👈 convertir str → UUID
    except Exception:
        return None

    ticket = db_session.query(db.Ticket).filter(
        db.Ticket.id_ticket == ticket_id,
        db.Ticket.id_colaborador == colaborador_uuid
    ).first()

    print(f"DEBUG - buscando ticket {ticket_id} con colaborador {colaborador_uuid}")

    return ticket