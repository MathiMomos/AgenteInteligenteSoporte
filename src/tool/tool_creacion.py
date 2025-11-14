# src/tool/tool_creacion.py
from langchain_core.tools import tool
from enum import Enum
import httpx

# Importamos los schemas, el keyvault y el formateador
from src.util import util_schemas as sch, util_keyvault as key, util_formatear_conversacion

# Estas urgencias deben coincidir con los IDs numéricos de GLPI
class UrgenciaTicket(str, Enum):
    MUY_BAJA = "1"
    BAJA = "2"
    MEDIA = "3"
    ALTA = "4"
    MUY_ALTA = "5"

FAKE_USER_AGENT = {"User-Agent": "python-requests/2.28.1"}

class ToolCreacion:
    def __init__(self, user_info: sch.TokenData, thread_id: str):
        self.user_info = user_info
        self.thread_id = thread_id

        self.GLPI_URL = key.get_glpi_url()
        self.APP_TOKEN = key.get_glpi_app_token()
        self.SYSTEM_USER_TOKEN = key.get_glpi_system_user_token()

    async def _call_glpi_api(self, payload: dict) -> dict:
        """
        Función auxiliar interna (asíncrona) para crear el ticket en GLPI.
        Usa el token de "Sistema" para autenticarse.
        """
        session_token = None
        async with httpx.AsyncClient() as client:
            try:
                # --- PASO 1: Iniciar sesión como Sistema ---
                headers_init = {
                    "App-Token": self.APP_TOKEN,
                    "Authorization": f"user_token {self.SYSTEM_USER_TOKEN}",
                    **FAKE_USER_AGENT
                }
                resp_init = await client.get(f"{self.GLPI_URL}/initSession", headers=headers_init)
                resp_init.raise_for_status()
                session_token = resp_init.json()["session_token"]

                # --- PASO 2: Crear el Ticket ---
                headers_create = {
                    "App-Token": self.APP_TOKEN,
                    "Session-Token": session_token,
                    "Content-Type": "application/json",
                    **FAKE_USER_AGENT
                }

                resp_create = await client.post(
                    f"{self.GLPI_URL}/Ticket",
                    headers=headers_create,
                    json=payload
                )
                resp_create.raise_for_status()
                return resp_create.json()  # Devuelve el ticket creado

            except httpx.HTTPStatusError as e:
                print(f"[GLPI API Error] {e.response.text}")
                # Si el error es 401, es probable que el token de sistema sea inválido
                if e.response.status_code == 401:
                    raise Exception(f"Error de autenticación del sistema en GLPI. Revise el SYSTEM_USER_TOKEN.")
                raise Exception(f"Error en API GLPI al crear ticket: {e.response.text}")
            finally:
                # --- PASO 3: Cerrar sesión de Sistema ---
                if session_token:
                    headers_kill = {
                        "App-Token": self.APP_TOKEN,
                        "Session-Token": session_token,
                        **FAKE_USER_AGENT
                    }
                    await client.get(f"{self.GLPI_URL}/killSession", headers=headers_kill)

    def get_tool(self):

        # ¡IMPORTANTE! La herramienta debe ser 'async' porque usa httpx 'await'
        @tool
        async def crear_ticket(asunto: str, descripcion: str, urgencia: UrgenciaTicket) -> str:
            """
            Crea un nuevo ticket de soporte en GLPI. Debe llamarse sólo cuando
            se conozca 'asunto' (título), 'descripcion' (detalle del problema)
            y 'urgencia' (un valor de 1 a 5).
            """
            try:
                # Preparamos el payload para GLPI
                payload = {
                    "input": {
                        "name": asunto,
                        "content": descripcion,
                        "urgency": urgencia.value,

                        # --- ¡CAMBIO CLAVE! ---
                        # Asignamos el ticket al usuario que está logueado en el chatbot
                        "users_id_recipient": self.user_info.glpi_id,

                        "status": 1  # 1 = Nuevo
                        # "type": 1 (Opcional: 1=Incidencia, 2=Solicitud)
                    }
                }

                # Llamamos a la API de GLPI de forma asíncrona
                ticket_creado = await self._call_glpi_api(payload)

                id_ticket = ticket_creado.get('id', 'N/A')

                # (La lógica de guardar la conversación en tu DB local se elimina)

                return (
                    f"¡Perfecto! He generado el ticket **#{id_ticket}** en GLPI con su solicitud."
                )

            except Exception as e:
                print(f"[crear_ticket] Error: {e}")
                return f"Lo siento, ocurrió un error inesperado al intentar crear su ticket: {e}"

        return crear_ticket