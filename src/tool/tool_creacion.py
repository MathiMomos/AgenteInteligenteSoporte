# src/tool/tool_creacion.py
from langchain_core.tools import tool
from sqlalchemy.orm import Session  # <-- ELIMINADO
from enum import Enum
import httpx  # <-- ¡NUEVO!

from datetime import datetime, date

# Importamos los schemas, el keyvault y el formateador
from src.util import util_schemas as sch, util_keyvault as key, util_formatear_conversacion
from src.util.util_memory import memory


# from src.crud import crud_tickets <-- ELIMINADO

# Estas urgencias deben coincidir con los IDs numéricos de GLPI
class UrgenciaTicket(str, Enum):
    MUY_BAJA = "1"
    BAJA = "2"
    MEDIA = "3"
    ALTA = "4"
    MUY_ALTA = "5"

class ImpactoTicket(str, Enum):
    BAJO = "1"
    MEDIO = "2"
    ALTO = "3"

class PrioridadTicket(str, Enum):
    BAJA = "1"
    MEDIA = "2"
    ALTA = "3"
    URGENTE = "4"

class ToolCreacion:
    def __init__(self, user_info: sch.TokenData, thread_id: str):
        # self.db = db <-- ¡YA NO SE USA!
        self.user_info = user_info  # Este es el TokenData con el glpi_id del usuario
        self.thread_id = thread_id

        # Guardamos las credenciales del "Sistema" para crear tickets
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
                    "Authorization": f"user_token {self.SYSTEM_USER_TOKEN}"
                }
                resp_init = await client.get(f"{self.GLPI_URL}/initSession", headers=headers_init)
                resp_init.raise_for_status()
                session_token = resp_init.json()["session_token"]

                # --- PASO 2: Crear el Ticket ---
                headers_create = {
                    "App-Token": self.APP_TOKEN,
                    "Session-Token": session_token,
                    "Content-Type": "application/json"
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
                    headers_kill = {"App-Token": self.APP_TOKEN, "Session-Token": session_token}
                    await client.get(f"{self.GLPI_URL}/killSession", headers=headers_kill)

    def get_tool(self):

        # ¡IMPORTANTE! La herramienta debe ser 'async' porque usa httpx 'await'
        @tool
        async def crear_ticket(asunto: str, descripcion: str, urgencia: UrgenciaTicket, impacto: ImpactoTicket, prioridad: PrioridadTicket) -> str:
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
                        "impact": impacto.value,
                        "priority": prioridad.value,
                        
                        # --- ¡CAMBIO CLAVE! ---
                        # Asignamos el ticket al usuario que está logueado en el chatbot

                        "_users_id_requester": self.user_info.glpi_id,
                        "status": 1  # 1 = Nuevo
                        # "type": 1 (Opcional: 1=Incidencia, 2=Solicitud)
                    }
                }
                print(f'ID del usuario: {self.user_info.glpi_id}')
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