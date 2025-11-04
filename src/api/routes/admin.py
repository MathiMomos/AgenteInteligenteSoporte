# src/api/routes/admin.py

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.util import util_schemas as sch
from src.util import util_base_de_datos as db_utils
from src.crud import crud_admin
from src.auth import security
from src.util.util_prompt import PROMPT_CACHE
import uuid

# =======================================================================
# @section DEPENDENCIA DE SEGURIDAD PARA ADMIN
# =======================================================================
ADMIN_DEPENDENCY = Depends(security.get_current_admin_user)

router = APIRouter(
    prefix="/api/admin",
    tags=["Administración"],
    dependencies=[ADMIN_DEPENDENCY]
)
# =======================================================================


# =======================================================================
# @section GESTIÓN DE PROMPT
# =======================================================================

@router.get("/prompt", response_model=sch.Prompt)
def get_main_prompt(db: Session = Depends(db_utils.obtener_bd)):
    """
    Obtiene el prompt principal del sistema (ID 1).
    """
    prompt_db = crud_admin.get_prompt_by_id(db, 1)
    if not prompt_db:
        raise HTTPException(
            status_code=404,
            detail="Prompt principal (ID 1) no encontrado."
        )

    return sch.Prompt(
        id_prompt=prompt_db.id_prompt,
        descripcion=prompt_db.descripcion
    )


@router.put("/prompt", response_model=sch.PromptUpdate)
def update_main_prompt(
    payload: sch.PromptUpdate,
    db: Session = Depends(db_utils.obtener_bd)
):
    """
    Actualiza el prompt principal del sistema (ID 1).
    """
    try:
        crud_admin.update_prompt_by_id(db, 1, payload.nuevo_texto)
        db.commit()
        # Actualizar el caché en memoria
        PROMPT_CACHE["prompt"] = payload.nuevo_texto
        return payload
    except HTTPException as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {e}"
        )


# =======================================================================
# @section GESTIÓN DE SERVICIOS
# =======================================================================

@router.get("/servicios", response_model=List[sch.Servicio])
def get_servicios_list(db: Session = Depends(db_utils.obtener_bd)):
    """
    Obtiene la lista de todos los servicios.
    """
    servicios_db = crud_admin.get_all_servicios(db)
    return [
        sch.Servicio(id_servicio=str(s.id_servicio), nombre=s.nombre)
        for s in servicios_db
    ]


@router.post("/servicios", response_model=sch.Servicio, status_code=status.HTTP_201_CREATED)
def create_nuevo_servicio(
    servicio_data: sch.ServicioCreate,
    db: Session = Depends(db_utils.obtener_bd)
):
    """
    Crea un nuevo servicio.
    """
    try:
        new_servicio = crud_admin.create_servicio(db, servicio_data)
        db.commit()
        db.refresh(new_servicio)
        return sch.Servicio(
            id_servicio=str(new_servicio.id_servicio),
            nombre=new_servicio.nombre
        )
    except HTTPException as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {e}"
        )


@router.put("/servicios/{id_servicio}", response_model=sch.Servicio)
def update_existing_servicio(
    id_servicio: uuid.UUID,
    servicio_data: sch.ServicioCreate,
    db: Session = Depends(db_utils.obtener_bd)
):
    """
    Actualiza el nombre de un servicio existente.
    """
    try:
        updated_servicio = crud_admin.update_servicio(db, id_servicio, servicio_data)
        db.commit()
        db.refresh(updated_servicio)
        return sch.Servicio(
            id_servicio=str(updated_servicio.id_servicio),
            nombre=updated_servicio.nombre
        )
    except HTTPException as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {e}"
        )


@router.delete("/servicios/{id_servicio}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_servicio(
    id_servicio: uuid.UUID,
    db: Session = Depends(db_utils.obtener_bd)
):
    """
    Elimina un servicio (si no está en uso).
    """
    try:
        crud_admin.delete_servicio(db, id_servicio)
        db.commit()
    except HTTPException as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {e}"
        )

    return None  # Devuelve 204 No Content


# =======================================================================
# @section GESTIÓN DE CLIENTES
# =======================================================================

@router.get("/clientes", response_model=List[sch.Cliente])
def get_clientes_list(db: Session = Depends(db_utils.obtener_bd)):
    """
    Obtiene la lista de todos los clientes.
    """
    clientes_db = crud_admin.get_all_clientes(db)
    return [
        sch.Cliente(id_cliente=str(c.id_cliente), nombre=c.nombre)
        for c in clientes_db
    ]


@router.post("/clientes", response_model=sch.Cliente, status_code=status.HTTP_201_CREATED)
def create_nuevo_cliente(
    cliente_data: sch.ClienteCreate,
    db: Session = Depends(db_utils.obtener_bd)
):
    """
    Crea un nuevo cliente con sus servicios y dominio.
    """
    new_cliente = crud_admin.create_cliente_completo(db, cliente_data)
    return sch.Cliente(
        id_cliente=str(new_cliente.id_cliente),
        nombre=new_cliente.nombre
    )


@router.get("/clientes/{id_cliente}", response_model=sch.ClienteDetail)
def get_cliente_detail(
    id_cliente: uuid.UUID,
    db: Session = Depends(db_utils.obtener_bd)
):
    """
    Obtiene la información completa de un cliente (incl. dominio y servicios).
    """
    try:
        detalle_dict = crud_admin.get_cliente_detalle(db, id_cliente)
        return sch.ClienteDetail(**detalle_dict)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {e}"
        )


@router.put("/clientes/{id_cliente}", response_model=sch.ClienteDetail)
def update_existing_cliente(
    id_cliente: uuid.UUID,
    cliente_data: sch.ClienteCreate,
    db: Session = Depends(db_utils.obtener_bd)
):
    """
    Actualiza la información completa de un cliente (nombre, dominio y servicios).
    """
    try:
        crud_admin.update_cliente_completo(db, id_cliente, cliente_data)
        db.commit()

        # Después de hacer commit, volvemos a pedir los datos actualizados
        detalle_dict = crud_admin.get_cliente_detalle(db, id_cliente)
        return sch.ClienteDetail(**detalle_dict)
    except HTTPException as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {e}"
        )


@router.delete("/clientes/{id_cliente}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_cliente(
    id_cliente: uuid.UUID,
    db: Session = Depends(db_utils.obtener_bd)
):
    """
    Elimina un cliente y sus asociaciones.
    """
    try:
        crud_admin.delete_cliente(db, id_cliente)
        db.commit()
    except HTTPException as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {e}"
        )

    return None  # Devuelve 204 No Content