from sqlalchemy.orm import Session
from src.util import util_base_de_datos as db

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