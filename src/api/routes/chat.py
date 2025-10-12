import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.util import util_schemas as sch
from src.util import util_base_de_datos as db_utils
from src.auth import security
from src.agente import agente_principal

router = APIRouter()

@router.post("", response_model=sch.ChatResponse)
async def chat_with_agent(
    request: sch.ChatRequest,
    db: Session = Depends(db_utils.obtener_bd),
    current_user: sch.TokenData = Depends(security.get_current_user),
):
    thread_id = request.thread_id or str(uuid.uuid4())
    print(
        f"[THREAD {thread_id}] Chat iniciado por: {current_user.nombre} de la empresa {current_user.cliente_nombre}"
    )
    print(f"DEBUG - colaborador_id en TokenData: {current_user.colaborador_id}")
    response_text = agente_principal.handle_query(
        query=request.query, thread_id=thread_id, user_info=current_user, db=db
    )
    return sch.ChatResponse(response=response_text, thread_id=thread_id)