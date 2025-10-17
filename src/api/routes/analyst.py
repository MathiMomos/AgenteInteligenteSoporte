from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.util import util_schemas as sch
from src.util import util_base_de_datos as db_utils
from src.auth import security
from src.crud import crud_analista, crud_tickets, crud_escalados

# =======================================================================
# @section 1: AÑADIMOS EL DICCIONARIO DE TRADUCCIÓN
# =======================================================================
UI_TO_DB_STATUS = {
    "abierto": "aceptado",
    "en atención": "en atención",
    "en atencion": "en atención", # Por si llega sin acento
    "cerrado": "finalizado",
    "finalizado": "finalizado",   # Por si ya envía el valor correcto
    "cancelado": "cancelado",
    "rechazado": "cancelado"
}

# =======================================================================
# @section 1: AÑADIMOS DICCIONARIO PARA NIVELES
# =======================================================================
UI_TO_DB_LEVEL = {
    "bajo": "bajo",
    "medio": "medio",
    "alto": "alto",
    "crítico": "crítico",
    "critico": "crítico" # Por si llega sin acento
}
# =======================================================================

router = APIRouter()


@router.get("/conversaciones", response_model=sch.AnalystTicketPage)
def listar_conversaciones_analista(
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
        status: Optional[str] = Query(None,
                                      description="Filtro por estado: Abierto, En Atención, Cerrado, etc."),
        db: Session = Depends(db_utils.obtener_bd),
        current_user: sch.TokenData = Depends(security.get_current_user),
):
    analyst_id = crud_analista.get_analyst_id_for_current_user_or_default(db, current_user)
    if not analyst_id:
        return sch.AnalystTicketPage(items=[], total=0, limit=limit, offset=offset)

    # =======================================================================
    # @section CORRECCIÓN AÑADIDA - Lógica de traducción para el filtro
    # =======================================================================
    estados_bd = None
    if status and status.lower() != "todos":
        # Limpiamos y traducimos el estado que viene de la URL
        status_from_ui = status.lower().strip()
        db_status = UI_TO_DB_STATUS.get(status_from_ui)

        if not db_status:
            raise HTTPException(status_code=400, detail=f"Estado de filtro '{status}' no es válido.")

        estados_bd = [db_status]
    # =======================================================================

    rows, total = crud_analista.get_tickets_by_analyst(
        db, analyst_id, limit=limit, offset=offset, estados=estados_bd
    )
    infos = crud_analista.hydrate_ticket_page(db, rows)
    items = [sch.AnalystTicketItem(**info) for info in infos]
    return sch.AnalystTicketPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/conversaciones/{id_ticket}", response_model=sch.AnalystTicketDetail)
def detalle_conversacion_analista(
        id_ticket: int,
        db: Session = Depends(db_utils.obtener_bd),
        current_user: sch.TokenData = Depends(security.get_current_user),
):
    t = crud_analista.get_ticket_admin_by_id(db, id_ticket)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    info = crud_analista.hydrate_ticket_info(db, t)
    conv = crud_analista.get_conversation_by_ticket(db, id_ticket)
    conversation = [sch.AnalystMessage(**m) for m in (conv.contenido or [])]

    return sch.AnalystTicketDetail(**info, conversation=conversation)


@router.put("/tickets/{ticket_id}/status", response_model=sch.AnalystTicketDetail)
def update_ticket_status(
        ticket_id: int,
        payload: sch.UpdateTicketStatusRequest,
        db: Session = Depends(db_utils.obtener_bd),
        current_user: sch.TokenData = Depends(security.get_current_user),
):
    analyst_id = crud_analista.get_analyst_id_for_current_user_or_default(db, current_user)
    if not analyst_id:
        raise HTTPException(status_code=403, detail="No autorizado (no es analista).")

    ticket = crud_analista.get_ticket_admin_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado.")
    if ticket.id_analista != analyst_id:
        raise HTTPException(status_code=403, detail="No autorizado para modificar este ticket.")

    # =======================================================================
    # @section 2: LÓGICA DE TRADUCCIÓN AÑADIDA
    # =======================================================================
    # Limpiamos el estado que viene del frontend (minúsculas, sin espacios extra)
    status_from_ui = payload.status.lower().strip()
    # Usamos el diccionario para "traducir" el estado
    db_status = UI_TO_DB_STATUS.get(status_from_ui)

    # Si el estado enviado no está en nuestro diccionario, lanzamos un error
    if not db_status:
        raise HTTPException(status_code=400, detail=f"Estado '{payload.status}' no es válido.")

    # Llamamos a la función del CRUD con el valor YA TRADUCIDO
    updated_ticket = crud_analista.update_ticket_status_db(
        db_session=db,
        ticket_id=ticket_id,
        new_status=db_status,
        description=payload.description if db_status == "finalizado" else None,
    )
    # =======================================================================

    if not updated_ticket:
        raise HTTPException(status_code=500, detail="No se pudo actualizar el estado.")

    # =======================================================================
    # @section 2: LÓGICA DE TRADUCCIÓN AÑADIDA PARA EL NIVEL
    # =======================================================================
    if getattr(payload, 'level', None):
        level_from_ui = payload.level.lower().strip()
        db_level = UI_TO_DB_LEVEL.get(level_from_ui)

        if not db_level:
            raise HTTPException(status_code=400, detail=f"Nivel '{payload.level}' no es válido.")

        updated_ticket = crud_analista.update_ticket_level_db(
            db_session=db, ticket_id=ticket_id, new_level=db_level  # Usamos el valor traducido
        )
        if not updated_ticket:
            raise HTTPException(status_code=500, detail="No se pudo actualizar el nivel.")
    # =======================================================================

    info = crud_analista.hydrate_ticket_info(db, updated_ticket)
    conv = crud_analista.get_conversation_by_ticket(db, ticket_id)
    conversation = [sch.AnalystMessage(**m) for m in (conv.contenido or [])]
    return sch.AnalystTicketDetail(**info, conversation=conversation)


@router.put("/tickets/{ticket_id}/derivar", response_model=sch.AnalystTicketDetail)
def derivar_ticket(
        ticket_id: int,
        payload: sch.DerivarTicketRequest,
        db: Session = Depends(db_utils.obtener_bd),
        current_user: sch.TokenData = Depends(security.get_current_user),
):
    current_analyst = crud_analista.get_analyst_from_token(db, current_user)
    if not current_analyst:
        raise HTTPException(status_code=403, detail="No autorizado (no es analista).")
    if current_analyst.nivel >= 3:
        raise HTTPException(status_code=403, detail="Acción no permitida para analistas de nivel 3.")

    ticket = crud_analista.get_ticket_admin_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado.")
    if ticket.id_analista != current_analyst.id_analista:
        raise HTTPException(status_code=403, detail="No autorizado para derivar este ticket.")

    new_analyst = crud_analista.find_random_higher_level_analyst(db, current_analyst.id_analista)
    if not new_analyst:
        raise HTTPException(status_code=409, detail="No se encontraron analistas de nivel superior disponibles.")

    crud_tickets.reassign_ticket_db(db, ticket, new_analyst.id_analista)
    crud_escalados.log_escalation_db(
        db_session=db, ticket_id=ticket_id, solicitante_id=current_analyst.id_analista,
        derivado_id=new_analyst.id_analista, motivo=payload.motivo,
    )
    db.commit()
    db.refresh(ticket)

    info = crud_analista.hydrate_ticket_info(db, ticket)
    conv = crud_analista.get_conversation_by_ticket(db, ticket_id)
    conversation = [sch.AnalystMessage(**m) for m in (conv.contenido or [])]
    return sch.AnalystTicketDetail(**info, conversation=conversation)