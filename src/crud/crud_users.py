from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound

# Importamos las clases de la BD desde nuestro archivo de conexión
from src.util import util_base_de_datos as db


def get_or_create_from_external(db_session: Session, id_info: dict) -> db.Persona:
    """
    Busca una persona por su login de Google. Si no existe, la crea.
    Su única responsabilidad es gestionar los registros de Persona y External.
    No se encarga de asignar roles.
    """
    provider = "google"
    provider_id = id_info.get("sub")
    email = id_info.get("email")
    name = id_info.get("name")
    hosted_domain = id_info.get("hd")

    try:
        # 1. Busca si la identidad externa (la cuenta de Google) ya existe
        external_identity = db_session.query(db.External).filter(
            db.External.provider == provider,
            db.External.id_provider == provider_id
        ).one()

        # Si existe, actualizamos sus datos por si cambiaron y devolvemos la persona
        print(f"Usuario encontrado en la BD: {email}")
        external_identity.correo = email
        external_identity.nombre = name
        external_identity.hd = hosted_domain
        # NO hacemos commit aquí. La función que llama es la responsable de la transacción.
        return external_identity.persona

    except NoResultFound:
        # 2. Si no existe, creamos la Persona y el External
        print(f"Usuario nuevo. Creando perfil para: {email}")

        new_persona = db.Persona()
        db_session.add(new_persona)
        db_session.flush()

        new_external = db.External(
            id_persona=new_persona.id_persona,
            provider=provider,
            id_provider=provider_id,
            correo=email,
            nombre=name,
            hd=hosted_domain
        )
        db_session.add(new_external)

        # El commit será manejado por la función que llama a esta.
        return new_persona