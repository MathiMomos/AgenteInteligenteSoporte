from langchain_core.tools import tool
import httpx
import re
from src.util import util_schemas as sch, util_keyvault as key

# Mapeo de Estados de GLPI
GLPI_STATUS_MAP = {
    1: "Nuevo",
    2: "En curso (Asignado)",
    3: "En curso (Planificado)",
    4: "En espera",
    5: "Resuelto",
    6: "Cerrado"
}

class ToolBusqueda:
    def __init__(self, user_info: sch.TokenData, thread_id: str):
        self.user_info = user_info
        self.thread_id = thread_id
        self.GLPI_URL = key.get_glpi_url()
        self.APP_TOKEN = key.get_glpi_app_token()
        self.SYSTEM_USER_TOKEN = key.get_glpi_system_user_token()

    # --- HELPER 1: Gestión Centralizada de Peticiones (Auth -> Request -> Kill) ---
    async def _glpi_request(self, endpoint: str, params: dict) -> dict:
        """
        Maneja el ciclo de vida completo: Login -> Petición -> Logout.
        Recibe el endpoint parcial (ej: 'Ticket/1') y los parámetros.
        """
        session_token = None
        async with httpx.AsyncClient() as client:
            try:
                # 1. Iniciar Sesión
                headers_init = {
                    "App-Token": self.APP_TOKEN,
                    "Authorization": f"user_token {self.SYSTEM_USER_TOKEN}"
                }
                resp_init = await client.get(f"{self.GLPI_URL}/initSession", headers=headers_init)
                resp_init.raise_for_status()
                session_token = resp_init.json()["session_token"]

                # 2. Ejecutar la petición real
                headers_req = {
                    "App-Token": self.APP_TOKEN,
                    "Session-Token": session_token,
                    "Content-Type": "application/json"
                }
                
                resp = await client.get(
                    f"{self.GLPI_URL}/{endpoint}",
                    headers=headers_req,
                    params=params
                )
                    
                resp.raise_for_status()
                return resp.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise Exception("Error de autenticación en GLPI (System Token).")
                raise Exception(f"Error GLPI ({e.response.status_code}): {e.response.text}")
            except Exception as e:
                raise Exception(f"Error de conexión o inesperado: {str(e)}")
            finally:
                # 3. Matar sesión (Siempre ocurre)
                if session_token:
                    headers_kill = {"App-Token": self.APP_TOKEN, "Session-Token": session_token}
                    await client.get(f"{self.GLPI_URL}/killSession", headers=headers_kill)

    # --- HELPER 2: Utilidades de Formato ---
    def _get_status_label(self, status_code) -> str:
        """Devuelve el texto del estado de forma segura."""
        try:
            return GLPI_STATUS_MAP.get(int(status_code), f"Desconocido ({status_code})")
        except (ValueError, TypeError):
            return f"Desconocido ({status_code})"

    def _clean_html(self, raw_html: str) -> str:
        if not raw_html: return "Sin contenido"
        clean_text = re.sub(r'<[^>]+>', '', raw_html)
        return clean_text.replace('&nbsp;', ' ').strip()

    def _format_single_ticket(self, ticket: dict) -> str:
        return (
            f"🎟️ **Ticket #{ticket.get('id')}**\n"
            f"📌 **Asunto:** {ticket.get('name')}\n"
            f"📅 **Fecha:** {ticket.get('date_creation', 'N/A')}\n"
            f"🚦 **Estado:** {self._get_status_label(ticket.get('status'))}\n"
            f"📝 **Descripción:** {self._clean_html(ticket.get('content', ''))}\n"
        )

    # --- TOOLS ---
    def get_tools(self):
        
        @tool
        async def buscar_ticket_por_id(ticket_id: int) -> str:
            """Busca un ticket en GLPI por su ID numérico."""
            try:
                # Llamada simplificada
                ticket = await self._glpi_request(f"Ticket/{ticket_id}", params={})

                if not ticket:
                    return f"No encontré el ticket #{ticket_id}."

                # Validación de seguridad
                requester_id = ticket.get('_users_id_requester')
                if str(requester_id) != str(self.user_info.glpi_id):
                    return f"No tienes permisos para ver el ticket #{ticket_id}."

                return self._format_single_ticket(ticket)

            except Exception as e:
                return f"Error buscando ticket: {e}"

        @tool
        async def listar_mis_tickets() -> str:
            """Muestra los últimos tickets del usuario actual."""
            try:
                # Llamada simplificada con parámetros
                params = {"with_tickets": "true", "expand_dropdowns": "true"}
                user_data = await self._glpi_request(f"User/{self.user_info.glpi_id}", params=params)

                tickets = user_data.get("_tickets", [])
                if not tickets:
                    return "No tienes tickets registrados."

                # Ordenar y cortar
                tickets = sorted(tickets, key=lambda x: x.get('id', 0), reverse=True)[:7]

                lines = ["📋 **Tus últimos tickets:**\n"]
                for t in tickets:
                    lines.append(
                        f"- **#{t.get('id')}**: {t.get('name', 'S/A')}\n"
                        f"  Estado: {self._get_status_label(t.get('status'))} | Fecha: {t.get('date', '-')}\n"
                    )
                
                return "\n".join(lines)

            except Exception as e:
                return f"Error listando tickets: {e}"

        return [buscar_ticket_por_id, listar_mis_tickets]