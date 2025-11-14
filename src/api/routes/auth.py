# src/auth/auth.py
import httpx
import base64
from fastapi import APIRouter, Depends, HTTPException, status

# Importamos los schemas y utilidades que ya modificamos
from src.util import util_schemas as sch
from src.util import util_keyvault as key
from src.auth import security

router = APIRouter()

FAKE_USER_AGENT = {"User-Agent": "python-requests/2.28.1"}


async def get_glpi_profile(username: str, password: str) -> dict:
    """
    Función auxiliar interna.
    Valida credenciales contra GLPI y devuelve el perfil del usuario.
    """
    GLPI_URL = key.get_glpi_url()
    APP_TOKEN = key.get_glpi_app_token()

    # Preparamos el header de Basic Auth (codificado en Base64)
    auth_string = f"{username}:{password}"
    auth_bytes = auth_string.encode('utf-8')
    auth_header_value = f"Basic {base64.b64encode(auth_bytes).decode('utf-8')}"

    session_token = None
    async with httpx.AsyncClient() as client:
        try:
            # --- PASO 1: Iniciar sesión con Basic Auth (usuario/pass) ---
            headers_init = {
                "App-Token": APP_TOKEN,
                "Authorization": auth_header_value,
                **FAKE_USER_AGENT
            }
            resp_init = await client.get(f"{GLPI_URL}/initSession", headers=headers_init)

            # Si el login (usuario/pass) es incorrecto, GLPI devuelve 401
            resp_init.raise_for_status()
            session_token = resp_init.json()["session_token"]

            # --- PASO 2: Obtener el Perfil del Usuario ---
            headers_profile = {
                "App-Token": APP_TOKEN,
                "Session-Token": session_token,
                **FAKE_USER_AGENT
            }
            resp_profile = await client.get(
                f"{GLPI_URL}/getActiveProfile",
                headers=headers_profile
            )
            resp_profile.raise_for_status()

            return resp_profile.json()  # ¡Éxito! Devuelve el perfil

        except httpx.HTTPStatusError as e:
            # Error de credenciales
            if e.response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuario o contraseña de GLPI incorrectos."
                )
            # Otro error de la API de GLPI
            print(f"Error API GLPI: {e.response.text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error al contactar la API de GLPI: {e.response.text}"
            )
        except Exception as e:
            # Error de conexión (ej. no se puede resolver el dominio)
            print(f"Error HTTPX: {e}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Error de conexión con el servidor GLPI."
            )
        finally:
            # --- PASO 3: Cerrar Sesión (importante) ---
            if session_token:
                headers_kill = {
                    "App-Token": APP_TOKEN,
                    "Session-Token": session_token,
                    **FAKE_USER_AGENT
                }
                # Usamos 'await' también para la llamada de cierre
                await client.get(f"{GLPI_URL}/killSession", headers=headers_kill)


@router.post("/login", response_model=sch.Token, tags=["Auth"])
async def login_con_usuario_y_pass(
        form_data: sch.UserPassLoginRequest
):
    # 1. Validar contra GLPI y obtener perfil
    glpi_profile = await get_glpi_profile(form_data.username, form_data.password)

    # 2. Extraer datos del perfil
    # (Los nombres de campo pueden variar, ajústalos según la respuesta de tu /getActiveProfile)
    user_id = glpi_profile.get("id")
    user_name = glpi_profile.get("name")  # ej: 'jperez'
    first_name = glpi_profile.get("firstname", "")
    last_name = glpi_profile.get("lastname", "")
    email = glpi_profile.get("email")

    if not user_id or not email or not user_name:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="El perfil de GLPI devuelto no contiene 'id', 'name' o 'email'."
        )

    # 3. Crear el "pasaporte" (TokenData) con los datos de GLPI
    token_data_payload = sch.TokenData(
        glpi_id=user_id,
        nombre=f"{first_name} {last_name}".strip() or user_name,
        correo=email,
        glpi_username=user_name
    )

    # 4. Crear y devolver nuestro JWT usando la función de security.py
    access_token = security.create_access_token(data=token_data_payload)

    return {"access_token": access_token, "token_type": "bearer"}
