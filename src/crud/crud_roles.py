from sqlalchemy.orm import Session
from src.util import util_base_de_datos as db
from fastapi import HTTPException


def get_or_create_collaborator_role(db_session: Session, persona: db.Persona) -> db.Colaborador:
    """
    Busca el rol de colaborador para una persona asociado al cliente 'Gmail'.
    Si no existe, lo crea.
    """
    # Primero, asegurar que el cliente "Gmail" exista.
    gmail_client = db_session.query(db.Cliente).filter(db.Cliente.nombre == "Gmail").first()
    if not gmail_client:
        # Este es un error de configuración del servidor, por eso el status 500.
        raise HTTPException(status_code=500,
                            detail="Configuración de servidor incorrecta: El cliente 'Gmail' no existe.")

    # Buscar si ya existe el rol de colaborador para este cliente.
    collaborator_role = db_session.query(db.Colaborador).filter_by(
        id_persona=persona.id_persona,
        id_cliente=gmail_client.id_cliente
    ).first()

    if collaborator_role:
        return collaborator_role

    # Si no existe, lo creamos.
    print(f"Asignando rol de Colaborador (Cliente: Gmail) a la persona {persona.id_persona}")
    new_collaborator_role = db.Colaborador(
        id_persona=persona.id_persona,
        id_cliente=gmail_client.id_cliente
    )
    db_session.add(new_collaborator_role)
    # Hacemos flush para que el objeto tenga su ID antes del commit final
    db_session.flush()
    return new_collaborator_role


def get_or_create_analyst_role(db_session: Session, persona: db.Persona) -> db.Analista:
    """
    Busca el rol de analista para una persona.
    Si no existe, lo crea con nivel 1.
    """
    analyst_role = db_session.query(db.Analista).filter_by(id_persona=persona.id_persona).first()

    if analyst_role:
        return analyst_role

    # Si no existe, lo creamos con nivel 1.
    print(f"Asignando rol de Analista (Nivel 1) a la persona {persona.id_persona}")
    new_analyst_role = db.Analista(id_persona=persona.id_persona, nivel=1)
    db_session.add(new_analyst_role)
    # Hacemos flush para que el objeto tenga su ID antes del commit final
    db_session.flush()
    return new_analyst_role