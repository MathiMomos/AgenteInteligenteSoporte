# src/auth/auth.py
import httpx
import base64
from fastapi import APIRouter, Depends, HTTPException, status

# Importamos los schemas y utilidades
from src.util import util_schemas as sch
from src.util import util_keyvault as key
from src.auth import security

router = APIRouter()

# Mantenemos el User-Agent falso, ya que funcionó
FAKE_USER_AGENT = {"User-Agent": "python-requests/2.28.1"}


async def get_glpi_profile(username: str, password: str) -> dict:
    """
    Función auxiliar interna.
    Valida credenciales contra GLPI y devuelve LA SESIÓN COMPLETA.
    """
    GLPI_URL = key.get_glpi_url()
    APP_TOKEN = key.get_glpi_app_token()

    auth_string = f"{username}:{password}"
    auth_bytes = auth_string.encode('utf-8')
    auth_header_value = f"Basic {base64.b64encode(auth_bytes).decode('utf-8')}"

    session_token = None
    async with httpx.AsyncClient() as client:
        try:
            # --- PASO 1: Iniciar sesión (esto estaba bien) ---
            headers_init = {
                "App-Token": APP_TOKEN,
                "Authorization": auth_header_value,
                **FAKE_USER_AGENT
            }
            resp_init = await client.get(f"{GLPI_URL}/initSession", headers=headers_init)
            resp_init.raise_for_status()
            session_token = resp_init.json()["session_token"]

            # --- PASO 2: Obtener la Sesión Completa (esto estaba bien) ---
            headers_profile = {
                "App-Token": APP_TOKEN,
                "Session-Token": session_token,
                **FAKE_USER_AGENT
            }
            resp_profile = await client.get(
                f"{GLPI_URL}/getFullSession",
                headers=headers_profile
            )
            resp_profile.raise_for_status()

            return resp_profile.json()  # ¡Éxito! Devuelve el JSON de la sesión completa

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuario o contraseña de GLPI incorrectos."
                )
            print(f"Error API GLPI: {e.response.text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error al contactar la API de GLPI: {e.response.text}"
            )
        except Exception as e:
            print(f"Error HTTPX: {e}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Error de conexión con el servidor GLPI. {e}"
            )
        finally:
            if session_token:
                headers_kill = {
                    "App-Token": APP_TOKEN,
                    "Session-Token": session_token,
                    **FAKE_USER_AGENT
                }
                await client.get(f"{GLPI_URL}/killSession", headers=headers_kill)


@router.post("/login", response_model=sch.Token, tags=["Auth"])
async def login_con_usuario_y_pass(
        form_data: sch.UserPassLoginRequest
):
    # 1. Validar contra GLPI y obtener sesión completa
    session_data = await get_glpi_profile(form_data.username, form_data.password)

    # 2. Navegar la estructura JSON
    user_profile = session_data.get("session", {})

    if not user_profile:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La respuesta de GLPI no contenía datos de 'session'."
        )

    print(user_profile)

    # 3. Extraer datos del usuario
    user_id = user_profile.get("glpiID")
    user_name = user_profile.get("glpiname")
    email = user_profile.get("mail") or user_profile.get("email")

    # --- NUEVO: Extraer datos de la entidad ---
    # glpiactive_entity suele ser un string o int en el JSON, lo forzamos a int
    entity_id_raw = user_profile.get("glpiactive_entity", 0)
    entity_name = user_profile.get("glpiactive_entity_name", "")

    try:
        entity_id = int(entity_id_raw)
    except (ValueError, TypeError):
        entity_id = 0

    # Construir nombre
    first_name = user_profile.get("glpifirstname", "")
    last_name = user_profile.get("glpirealname", "")
    full_name = f"{first_name} {last_name}".strip()

    # 4. Validación
    if not user_id or not user_name:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="El perfil de usuario de GLPI no contiene 'glpiID' o 'glpiname'."
        )

    # 5. Crear el "pasaporte" (TokenData) CON LA ENTIDAD
    token_data_payload = sch.TokenData(
        glpi_id=user_id,
        nombre=full_name or user_name,
        correo=email or "",
        glpi_username=user_name,
        # Guardamos la entidad en el token
        glpi_entity_id=entity_id,
        glpi_entity_name=entity_name
    )

    # 6. Crear y devolver nuestro JWT
    access_token = security.create_access_token(data=token_data_payload)

    return {"access_token": access_token, "token_type": "bearer"}