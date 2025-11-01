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
    return db_session.query(db.Prompt).filter(db.Prompt.id_prompt == prompt_id).first()


def update_prompt_by_id(db_session: Session, prompt_id: int, new_content: str) -> db.Prompt:
    prompt_row = get_prompt_by_id(db_session, prompt_id)
    if not prompt_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prompt with ID {prompt_id} not found.")
    prompt_row.contenido = new_content
    return prompt_row


# =========================================
# Funciones CRUD para Servicios
# =========================================
def get_all_servicios(db_session: Session) -> List[db.Servicio]:
    return db_session.query(db.Servicio).order_by(db.Servicio.nombre).all()


def create_servicio(db_session: Session, servicio_data: sch.ServicioCreate) -> db.Servicio:
    existing_servicio = db_session.query(db.Servicio).filter(
        func.lower(db.Servicio.nombre) == servicio_data.nombre.lower()
    ).first()
    if existing_servicio:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A service with this name already exists.")

    new_servicio = db.Servicio(nombre=servicio_data.nombre)
    db_session.add(new_servicio)
    db_session.flush()
    return new_servicio


# =========================================
# Funciones CRUD para Clientes
# =========================================
def get_all_clientes(db_session: Session) -> List[db.Cliente]:
    return db_session.query(db.Cliente).order_by(db.Cliente.nombre).all()


def create_cliente_completo(db_session: Session, cliente_data: sch.ClienteCreate) -> db.Cliente:
    """
    Función transaccional para crear un cliente, asignarle servicios Y su dominio único.
    """

    # 0. Convertir IDs de servicio y limpiar el dominio
    try:
        servicio_uuids = [uuid.UUID(sid) for sid in cliente_data.servicios_ids]
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="One or more service IDs are not valid UUIDs.")

    dominio_limpio = cliente_data.dominio.lower().strip()
    if not dominio_limpio:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El dominio no puede estar vacío.")

    try:
        # 1. Validación de Servicios (que existan)
        count_query = select(func.count(db.Servicio.id_servicio)).where(db.Servicio.id_servicio.in_(servicio_uuids))
        found_count = db_session.execute(count_query).scalar_one()
        if found_count != len(servicio_uuids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="One or more provided service IDs do not exist.")

        # 2. Validación de Cliente (nombre duplicado)
        existing_cliente = db_session.query(db.Cliente).filter(
            func.lower(db.Cliente.nombre) == cliente_data.nombre_cliente.lower()
        ).first()
        if existing_cliente:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="A client with this name already exists.")

        # 3. VALIDACIÓN DE DOMINIO (que no esté en uso)
        existing_domain = db_session.query(db.ClienteDominio).filter(
            db.ClienteDominio.dominio == dominio_limpio
        ).first()
        if existing_domain:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"El dominio '{dominio_limpio}' ya está registrado por otro cliente.")

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

        # 6. ASIGNAR EL DOMINIO ÚNICO
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"An internal error occurred: {e}")