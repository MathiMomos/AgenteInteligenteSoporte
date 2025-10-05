from sqlalchemy.orm import Session
from src.util import util_base_de_datos as db
from sqlalchemy import desc

def log_escalation_db(
    db_session: Session,
    ticket_id: int,
    solicitante_id: str,
    derivado_id: str,
    motivo: str
) -> db.Escalado:
    """Crea un registro en la tabla 'escalado'."""
    new_escalado = db.Escalado(
        id_ticket=ticket_id,
        id_analista_solicitante=solicitante_id,
        id_analista_derivado=derivado_id,
        motivo=motivo
    )
    db_session.add(new_escalado)
    return new_escalado

def get_latest_escalation_reason(db_session: Session, ticket_id: int) -> str | None:
    """
    Obtiene el motivo de la última derivación de un ticket.
    Retorna None si el ticket no ha sido derivado.
    """
    escalado = (
        db_session.query(db.Escalado)
        .filter(db.Escalado.id_ticket == ticket_id)
        .order_by(desc(db.Escalado.id_escalado))  
        .first()
    )
    
    if escalado:
        return getattr(escalado, "motivo", None)
    return None