from src.util import util_keyvault as key
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as grequests

from src.util import util_schemas as sch
from src.util import util_base_de_datos as db_utils
from src.auth import security
from src.crud import crud_users
from src.crud import crud_roles

router = APIRouter()


# --- FUNCIÓN AUXILIAR PARA VERIFICAR TOKEN (EVITA REPETIR CÓDIGO) ---
def verify_google_token(id_token_str: str) -> dict:
    """Verifica el token de Google y devuelve la información del usuario."""
    google_client_id = key.getkeyapi("GOOGLE-CLIENT-ID")
    if not google_client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID no configurado")

    try:
        id_info = id_token.verify_oauth2_token(
            id_token_str, grequests.Request(), google_client_id
        )
        if id_info.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
            raise HTTPException(status_code=401, detail="Issuer inválido")
        return id_info
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Token de Google inválido: {e}")


@router.post("/google/login/colaborador", response_model=sch.Token, tags=["Auth"])
async def google_login_colaborador(
        request: sch.GoogleLoginRequest,
        db: Session = Depends(db_utils.obtener_bd),
):
    """Endpoint de login para Colaboradores. Crea el rol si no existe."""
    id_info = verify_google_token(request.id_token)

    persona = crud_users.get_or_create_from_external(db_session=db, id_info=id_info)

    colaborador = crud_roles.get_or_create_collaborator_role(db, persona)

    db.commit()

    cliente = db.query(db_utils.Cliente).filter_by(id_cliente=colaborador.id_cliente).first()
    servicios_contratados_db = (
        db.query(db_utils.Servicio)
        .join(db_utils.ClienteServicio)
        .filter(db_utils.ClienteServicio.id_cliente == colaborador.id_cliente)
        .all()
    )
    servicios_para_token = [sch.ServicioInfo(id_servicio=str(s.id_servicio), nombre=s.nombre) for s in
                            servicios_contratados_db]

    token_data_payload = sch.TokenData(
        correo=id_info.get("email"),
        nombre=id_info.get("name"),
        persona_id=str(persona.id_persona),
        colaborador_id=str(colaborador.id_colaborador),
        cliente_id=str(colaborador.id_cliente),
        cliente_nombre=cliente.nombre if cliente else "Cliente Desconocido",
        servicios_contratados=servicios_para_token
    )
    access_token = security.create_access_token(data=token_data_payload)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/google/login/analista", response_model=sch.Token, tags=["Auth"])
async def google_login_analista(
        request: sch.GoogleLoginRequest,
        db: Session = Depends(db_utils.obtener_bd),
):
    """Endpoint de login para Analistas. Crea el rol con nivel 1 si no existe."""
    id_info = verify_google_token(request.id_token)

    persona = crud_users.get_or_create_from_external(db_session=db, id_info=id_info)

    analista = crud_roles.get_or_create_analyst_role(db, persona)

    db.commit()

    token_data_payload = sch.TokenData(
        correo=id_info.get("email"),
        nombre=id_info.get("name"),
        persona_id=str(persona.id_persona),
        colaborador_id="00000000-0000-0000-0000-000000000000",
        cliente_id="00000000-0000-0000-0000-000000000000",
        cliente_nombre="ANALYTICS",
        servicios_contratados=[]
    )
    access_token = security.create_access_token(data=token_data_payload)
    return {"access_token": access_token, "token_type": "bearer"}