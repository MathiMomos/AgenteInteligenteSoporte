# src/crud/crud_admin.py

import uuid
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from fastapi import HTTPException, status

from src.util import util_base_de_datos as db
from src.util import util_schemas as sch


# =========================================
# Funciones CRUD para el Prompt
# =========================================
def get_prompt_by_id(db_session: Session, prompt_id: int) -> db.Prompt | None:
    """Obtiene un prompt por su ID."""
    return db_session.query(db.Prompt).filter(db.Prompt.id_prompt == prompt_id).first()


def update_prompt_by_id(db_session: Session, prompt_id: int, new_content: str) -> db.Prompt:
    """
    Actualiza el contenido del prompt.
    CORREGIDO: Usa 'descripcion' en lugar de 'contenido'
    """
    prompt_row = get_prompt_by_id(db_session, prompt_id)
    if not prompt_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with ID {prompt_id} not found."
        )
    prompt_row.descripcion = new_content
    return prompt_row


# =========================================
# Funciones CRUD para Servicios
# =========================================
def get_all_servicios(db_session: Session) -> List[db.Servicio]:
    """Obtiene todos los servicios ordenados por nombre."""
    return db_session.query(db.Servicio).order_by(db.Servicio.nombre).all()


def get_servicio_by_id(db_session: Session, id_servicio: uuid.UUID) -> db.Servicio | None:
    """Obtiene un servicio por su UUID."""
    return db_session.query(db.Servicio).filter(db.Servicio.id_servicio == id_servicio).first()


def create_servicio(db_session: Session, servicio_data: sch.ServicioCreate) -> db.Servicio:
    """Crea un nuevo servicio."""
    # Validar nombre duplicado
    existing_servicio = db_session.query(db.Servicio).filter(
        func.lower(db.Servicio.nombre) == servicio_data.nombre.lower()
    ).first()
    if existing_servicio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A service with this name already exists."
        )

    new_servicio = db.Servicio(nombre=servicio_data.nombre)
    db_session.add(new_servicio)
    db_session.flush()
    return new_servicio


def update_servicio(db_session: Session, id_servicio: uuid.UUID, servicio_data: sch.ServicioCreate) -> db.Servicio:
    """Actualiza el nombre de un servicio."""
    servicio_db = get_servicio_by_id(db_session, id_servicio)
    if not servicio_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado"
        )

    # Validar nombre duplicado (ignorando el servicio actual)
    existing_servicio = db_session.query(db.Servicio).filter(
        func.lower(db.Servicio.nombre) == servicio_data.nombre.lower(),
        db.Servicio.id_servicio != id_servicio
    ).first()
    if existing_servicio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un servicio con ese nombre"
        )

    servicio_db.nombre = servicio_data.nombre
    return servicio_db


def delete_servicio(db_session: Session, id_servicio: uuid.UUID):
    """
    Elimina un servicio.
    Valida que el servicio NO esté en uso antes de eliminarlo.
    """
    servicio_db = get_servicio_by_id(db_session, id_servicio)
    if not servicio_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado"
        )

    # Validar que el servicio no esté en uso
    asociacion = db_session.query(db.ClienteServicio).filter(
        db.ClienteServicio.id_servicio == id_servicio
    ).first()
    if asociacion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar: El servicio está asignado a uno o más clientes."
        )

    db_session.delete(servicio_db)


# =========================================
# Funciones CRUD para Clientes
# =========================================
def get_all_clientes(db_session: Session) -> List[db.Cliente]:
    """Obtiene todos los clientes ordenados por nombre."""
    return db_session.query(db.Cliente).order_by(db.Cliente.nombre).all()


def get_cliente_by_id(db_session: Session, id_cliente: uuid.UUID) -> db.Cliente | None:
    """Obtiene un cliente por su UUID."""
    return db_session.query(db.Cliente).filter(db.Cliente.id_cliente == id_cliente).first()


def get_cliente_detalle(db_session: Session, id_cliente: uuid.UUID) -> dict:
    """
    Obtiene el detalle completo de un cliente.
    Retorna un diccionario con: id_cliente, nombre, dominio y servicios.
    """
    cliente_db = get_cliente_by_id(db_session, id_cliente)
    if not cliente_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado"
        )

    # 1. Obtener dominio
    dominio_db = db_session.query(db.ClienteDominio).filter(
        db.ClienteDominio.id_cliente == id_cliente
    ).first()

    # 2. Obtener servicios
    servicios_db = db_session.query(db.Servicio).join(
        db.ClienteServicio, db.ClienteServicio.id_servicio == db.Servicio.id_servicio
    ).filter(
        db.ClienteServicio.id_cliente == id_cliente
    ).order_by(db.Servicio.nombre).all()

    # 3. Formatear la respuesta
    return {
        "id_cliente": str(cliente_db.id_cliente),
        "nombre": cliente_db.nombre,
        "dominio": dominio_db.dominio if dominio_db else "",
        "servicios": [
            sch.Servicio(id_servicio=str(s.id_servicio), nombre=s.nombre)
            for s in servicios_db
        ]
    }


def create_cliente_completo(db_session: Session, cliente_data: sch.ClienteCreate) -> db.Cliente:
    """
    Función transaccional para crear un cliente, asignarle servicios Y su dominio único.
    """
    # 0. Convertir IDs de servicio y limpiar el dominio
    try:
        servicio_uuids = [uuid.UUID(sid) for sid in cliente_data.servicios_ids]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more service IDs are not valid UUIDs."
        )

    dominio_limpio = cliente_data.dominio.lower().strip()
    if not dominio_limpio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El dominio no puede estar vacío."
        )

    try:
        # 1. Validación de Servicios (que existan)
        count_query = select(func.count(db.Servicio.id_servicio)).where(
            db.Servicio.id_servicio.in_(servicio_uuids)
        )
        found_count = db_session.execute(count_query).scalar_one()
        if found_count != len(servicio_uuids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more provided service IDs do not exist."
            )

        # 2. Validación de Cliente (nombre duplicado)
        existing_cliente = db_session.query(db.Cliente).filter(
            func.lower(db.Cliente.nombre) == cliente_data.nombre_cliente.lower()
        ).first()
        if existing_cliente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A client with this name already exists."
            )

        # 3. Validación de Dominio (que no esté en uso)
        existing_domain = db_session.query(db.ClienteDominio).filter(
            db.ClienteDominio.dominio == dominio_limpio
        ).first()
        if existing_domain:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El dominio '{dominio_limpio}' ya está registrado por otro cliente."
            )

        # 4. Crear el Cliente
        new_cliente = db.Cliente(nombre=cliente_data.nombre_cliente)
        db_session.add(new_cliente)
        db_session.flush()  # Obtenemos el ID del nuevo cliente

        # 5. Asignar los Servicios
        for servicio_id in servicio_uuids:
            new_association = db.ClienteServicio(
                id_cliente=new_cliente.id_cliente,
                id_servicio=servicio_id
            )
            db_session.add(new_association)

        # 6. Asignar el Dominio Único
        new_domain = db.ClienteDominio(
            id_cliente=new_cliente.id_cliente,
            dominio=dominio_limpio
        )
        db_session.add(new_domain)

        db_session.commit()
        db_session.refresh(new_cliente)
        return new_cliente

    except Exception as e:
        db_session.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred: {e}"
        )


def update_cliente_completo(db_session: Session, id_cliente: uuid.UUID, cliente_data: sch.ClienteCreate) -> db.Cliente:
    """
    Función transaccional para ACTUALIZAR un cliente, sus servicios y su dominio.
    """
    cliente_db = get_cliente_by_id(db_session, id_cliente)
    if not cliente_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado"
        )

    # 0. Convertir IDs de servicio y limpiar el dominio
    try:
        servicio_uuids = [uuid.UUID(sid) for sid in cliente_data.servicios_ids]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more service IDs are not valid UUIDs."
        )

    dominio_limpio = cliente_data.dominio.lower().strip()
    if not dominio_limpio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El dominio no puede estar vacío."
        )

    # 1. Validación de Servicios (que existan)
    count_query = select(func.count(db.Servicio.id_servicio)).where(
        db.Servicio.id_servicio.in_(servicio_uuids)
    )
    found_count = db_session.execute(count_query).scalar_one()
    if found_count != len(servicio_uuids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more provided service IDs do not exist."
        )

    # 2. Validación de Cliente (nombre duplicado, ignorando el actual)
    existing_cliente = db_session.query(db.Cliente).filter(
        func.lower(db.Cliente.nombre) == cliente_data.nombre_cliente.lower(),
        db.Cliente.id_cliente != id_cliente
    ).first()
    if existing_cliente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A client with this name already exists."
        )

    # 3. Validación de Dominio (que no esté en uso por OTRO cliente)
    existing_domain = db_session.query(db.ClienteDominio).filter(
        db.ClienteDominio.dominio == dominio_limpio,
        db.ClienteDominio.id_cliente != id_cliente
    ).first()
    if existing_domain:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El dominio '{dominio_limpio}' ya está registrado por otro cliente."
        )

    # 4. Actualizar el Cliente
    cliente_db.nombre = cliente_data.nombre_cliente

    # 5. Actualizar Dominio
    dominio_db = db_session.query(db.ClienteDominio).filter(
        db.ClienteDominio.id_cliente == id_cliente
    ).first()
    if dominio_db:
        dominio_db.dominio = dominio_limpio
    else:
        # Si por alguna razón no tenía dominio, se lo creamos
        new_domain = db.ClienteDominio(id_cliente=id_cliente, dominio=dominio_limpio)
        db_session.add(new_domain)

    # 6. Actualizar Servicios (Método simple: borrar todos y re-añadir)
    db_session.query(db.ClienteServicio).filter(
        db.ClienteServicio.id_cliente == id_cliente
    ).delete(synchronize_session=False)

    for servicio_id in servicio_uuids:
        new_association = db.ClienteServicio(
            id_cliente=id_cliente,
            id_servicio=servicio_id
        )
        db_session.add(new_association)

    return cliente_db


def delete_cliente(db_session: Session, id_cliente: uuid.UUID):
    """
    Elimina un cliente y sus asociaciones directas (dominio y servicios).
    Asume que la BD tiene ON DELETE CASCADE para tickets y colaboradores.
    """
    cliente_db = get_cliente_by_id(db_session, id_cliente)
    if not cliente_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado"
        )

    # 1. Borrar asociaciones de servicios
    db_session.query(db.ClienteServicio).filter(
        db.ClienteServicio.id_cliente == id_cliente
    ).delete(synchronize_session=False)

    # 2. Borrar asociación de dominio
    db_session.query(db.ClienteDominio).filter(
        db.ClienteDominio.id_cliente == id_cliente
    ).delete(synchronize_session=False)

    # 3. Borrar cliente
    db_session.delete(cliente_db)