from src.util import util_keyvault as key
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as grequests

from src.util import util_schemas as sch
from src.util import util_base_de_datos as db_utils
from src.auth import security
from src.crud import crud_users

router = APIRouter()

@router.post("/google/login", response_model=sch.Token)
async def google_login(
    request: sch.GoogleLoginRequest,
    db: Session = Depends(db_utils.obtener_bd),
):
    google_client_id = key.getkeyapi("GOOGLE-CLIENT-ID")
    if not google_client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID no configurado")

    try:
        id_info = id_token.verify_oauth2_token(
            request.id_token, grequests.Request(), google_client_id
        )
        if id_info.get("iss") not in (
            "accounts.google.com",
            "https://accounts.google.com",
        ):
            raise HTTPException(status_code=401, detail="Issuer inválido")
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Token de Google inválido: {e}")

    persona = crud_users.get_or_create_from_external(db_session=db, id_info=id_info)
    external_info = (
        db.query(db_utils.External)
        .filter(db_utils.External.id_persona == persona.id_persona)
        .first()
    )
    if not external_info:
        raise HTTPException(
            status_code=500,
            detail="No se encontró información externa asociada a la persona.",
        )

    colaborador = (
        db.query(db_utils.Colaborador)
        .filter(db_utils.Colaborador.id_persona == persona.id_persona)
        .first()
    )
    if colaborador:
        cliente = (
            db.query(db_utils.Cliente)
            .filter(db_utils.Cliente.id_cliente == colaborador.id_cliente)
            .first()
        )
        servicios_contratados_db = (
            db.query(db_utils.Servicio)
            .join(db_utils.ClienteServicio)
            .filter(db_utils.ClienteServicio.id_cliente == colaborador.id_cliente)
            .all()
        )
        servicios_para_token = [
            sch.ServicioInfo(id_servicio=str(s.id_servicio), nombre=s.nombre)
            for s in servicios_contratados_db
        ]
        token_data_payload = sch.TokenData(
            correo=external_info.correo,
            nombre=external_info.nombre,
            persona_id=str(persona.id_persona),
            colaborador_id=str(colaborador.id_colaborador),
            cliente_id=str(colaborador.id_cliente),
            cliente_nombre=cliente.nombre if cliente else "Cliente Desconocido",
            servicios_contratados=servicios_para_token
        )
        access_token = security.create_access_token(data=token_data_payload)
        return {"access_token": access_token, "token_type": "bearer"}

    analista = (
        db.query(db_utils.Analista)
        .filter(db_utils.Analista.id_persona == persona.id_persona)
        .first()
    )
    if analista:
        token_data_payload = sch.TokenData(
            correo=external_info.correo,
            nombre=external_info.nombre,
            persona_id=str(persona.id_persona),
            colaborador_id="00000000-0000-0000-0000-000000000000",
            cliente_id="00000000-0000-0000-0000-000000000000",
            cliente_nombre="ANALYTICS",
            servicios_contratados=[]
        )
        access_token = security.create_access_token(data=token_data_payload)
        return {"access_token": access_token, "token_type": "bearer"}

    raise HTTPException(
        status_code=403,
        detail="Acceso denegado. Este usuario no está registrado como colaborador ni como analista.",
    )