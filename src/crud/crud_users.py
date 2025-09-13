from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound

# Importamos las clases de la BD desde nuestro archivo de conexión
from src.util import util_base_de_datos as db


def get_or_create_from_external(db_session: Session, id_info: dict) -> db.Persona:
    """
    Busca un usuario por su login de Google. Si no existe, lo crea.
    Esta versión está 100% alineada con el esquema de BD final.
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
        db_session.commit()
        return external_identity.persona

    except NoResultFound:
        # 2. Si no existe, creamos el usuario completo
        print(f"Usuario nuevo. Creando perfil para: {email}")

        # La tabla Persona no tiene campos, solo el ID que se genera automáticamente
        new_persona = db.Persona()
        db_session.add(new_persona)
        db_session.flush()  # Importante para obtener el id_persona generado

        # Guardamos el nombre y correo en la tabla External
        new_external = db.External(
            id_persona=new_persona.id_persona,
            provider=provider,
            id_provider=provider_id,
            correo=email,
            nombre=name,
            hd=hosted_domain
        )
        db_session.add(new_external)

        # La lógica para asignarlo como Colaborador sigue igual
        if hosted_domain:
            cliente_dominio = db_session.query(db.ClienteDominio).filter(
                db.ClienteDominio.dominio == hosted_domain
            ).first()
            if cliente_dominio:
                cliente = cliente_dominio.cliente
                print(f"Dominio '{hosted_domain}' reconocido. Asignando al cliente: {cliente.nombre}")
                new_colaborador = db.Colaborador(
                    id_persona=new_persona.id_persona,
                    id_cliente=cliente.id_cliente
                )
                db_session.add(new_colaborador)

        db_session.commit()
        db_session.refresh(new_persona)

        return new_persona