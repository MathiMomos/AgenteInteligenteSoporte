from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound

# Importamos las clases de la BD desde nuestro archivo de conexión
from src.util import util_base_de_datos as db


def get_or_create_from_external(db_session: Session, id_info: dict) -> db.Persona:
    """
    Busca un usuario por su login de Google. Si no existe, lo crea.
    Añade un caso especial para asignar usuarios @gmail.com al cliente "Gmail".
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

        # --- LÓGICA MODIFICADA PARA ASIGNAR CLIENTE ---
        target_cliente = None

        # Metodo 1: Búsqueda por dominio corporativo (como antes)
        if hosted_domain:
            cliente_dominio = db_session.query(db.ClienteDominio).filter(
                db.ClienteDominio.dominio == hosted_domain
            ).first()
            if cliente_dominio:
                target_cliente = cliente_dominio.cliente

        # Metodo 2: Caso especial para usuarios @gmail.com
        elif email and email.lower().endswith("@gmail.com"):
            gmail_cliente = db_session.query(db.Cliente).filter(
                db.Cliente.nombre == "Gmail"
            ).first()
            if gmail_cliente:
                target_cliente = gmail_cliente

        # Si se encontró un cliente por cualquiera de los dos métodos, se crea el colaborador
        if target_cliente:
            print(f"Dominio reconocido. Asignando al cliente: {target_cliente.nombre}")
            new_colaborador = db.Colaborador(
                id_persona=new_persona.id_persona,
                id_cliente=target_cliente.id_cliente
            )
            db_session.add(new_colaborador)
        # --- FIN DE LA LÓGICA MODIFICADA ---

        db_session.commit()
        db_session.refresh(new_persona)

        return new_persona