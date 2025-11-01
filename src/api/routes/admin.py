# src/api/routes/admin.py

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.util import util_schemas as sch
from src.util import util_base_de_datos as db_utils
from src.crud import crud_admin
from src.auth import security # Importamos nuestro módulo de seguridad
from src.util.util_prompt import PROMPT_CACHE

# =======================================================================
# @section DEPENDENCIA DE SEGURIDAD PARA ADMIN
# =======================================================================
# Ahora, en lugar de una dependencia genérica, usamos nuestra nueva barrera
ADMIN_DEPENDENCY = Depends(security.get_current_admin_user)

router = APIRouter(
    prefix="/api/admin",
    tags=["Administración"],
    dependencies=[ADMIN_DEPENDENCY] # Aplicamos la barrera a TODAS las rutas de este archivo
)
# =======================================================================


# --- Endpoints (El resto del código no cambia) ---

@router.get("/servicios", response_model=List[sch.Servicio])
def get_servicios_list(db: Session = Depends(db_utils.obtener_bd)):
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
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")

@router.get("/clientes", response_model=List[sch.Cliente])
def get_clientes_list(db: Session = Depends(db_utils.obtener_bd)):
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
    new_cliente = crud_admin.create_cliente_completo(db, cliente_data)
    return sch.Cliente(
        id_cliente=str(new_cliente.id_cliente),
        nombre=new_cliente.nombre
    )

@router.put("/prompt", response_model=sch.PromptUpdate)
def update_main_prompt(
    payload: sch.PromptUpdate, 
    db: Session = Depends(db_utils.obtener_bd)
):
    try:
        crud_admin.update_prompt_by_id(db, 1, payload.nuevo_texto)
        db.commit()
        PROMPT_CACHE["prompt"] = payload.nuevo_texto
        return payload
    except HTTPException as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")