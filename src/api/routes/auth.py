from src.util import util_keyvault as key
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.auth.security import verify_google_token

from src.util import util_schemas as sch
from src.util import util_base_de_datos as db_utils
from src.auth import security
from src.crud import crud_users

router = APIRouter()

@router.post("/google/login/colaborador", response_model=sch.Token, tags=["Auth"])
async def google_login_colaborador(
        request: sch.GoogleLoginRequest,
        db: Session = Depends(db_utils.obtener_bd),
):
    """Endpoint de login exclusivo para Colaboradores."""
    id_info = verify_google_token(request.id_token)

    # Busca o crea al usuario. Esta función ya maneja la creación de colaboradores nuevos.
    persona = crud_users.get_or_create_from_external(db_session=db, id_info=id_info)

    colaborador = db.query(db_utils.Colaborador).filter_by(id_persona=persona.id_persona).first()

    if not colaborador:
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado. Este usuario no está registrado como colaborador.",
        )

    # Si es un colaborador válido, procedemos a generar su token
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
    """Endpoint de login exclusivo para Analistas."""
    id_info = verify_google_token(request.id_token)

    # Busca o crea la 'Persona' base. Un analista ya debe tener su rol asignado manualmente.
    persona = crud_users.get_or_create_from_external(db_session=db, id_info=id_info)

    analista = db.query(db_utils.Analista).filter_by(id_persona=persona.id_persona).first()

    if not analista:
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado. No tienes permisos de analista.",
        )

    # Si es un analista válido, generamos su token
    token_data_payload = sch.TokenData(
        correo=id_info.get("email"),
        nombre=id_info.get("name"),
        persona_id=str(persona.id_persona),
        # IDs de colaborador/cliente vacíos o genéricos para analistas
        colaborador_id="00000000-0000-0000-0000-000000000000",
        cliente_id="00000000-0000-0000-0000-000000000000",
        cliente_nombre="ANALYTICS",  # Nombre interno para la empresa
        servicios_contratados=[]
    )
    access_token = security.create_access_token(data=token_data_payload)
    return {"access_token": access_token, "token_type": "bearer"}