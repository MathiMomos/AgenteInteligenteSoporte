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

GLPI_PRIORITY_MAP = {
    1: "Baja",
    2: "Media",
    3: "Alta",  
    4: "Urgente"
}

FAKE_USER_AGENT = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

class ToolBusqueda:
    def __init__(self, user_info: sch.TokenData, thread_id: str):
        self.user_info = user_info
        self.thread_id = thread_id
        self.GLPI_URL = key.get_glpi_url().rstrip('/')
        self.APP_TOKEN = key.get_glpi_app_token()
        self.SYSTEM_USER_TOKEN = key.get_glpi_system_user_token()

    async def _glpi_request(self, endpoint: str, params: dict) -> dict:
        """
        Maneja el ciclo de vida completo: Login -> Petición -> Logout.
        """
        session_token = None
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            try:
                # 1. Iniciar Sesión
                headers_init = {
                    "App-Token": self.APP_TOKEN,
                    "Authorization": f"user_token {self.SYSTEM_USER_TOKEN}",
                    **FAKE_USER_AGENT
                }
                resp_init = await client.get(f"{self.GLPI_URL}/initSession", headers=headers_init)
                resp_init.raise_for_status()
                session_token = resp_init.json()["session_token"]

                # 2. Ejecutar la petición real
                headers_req = {
                    "App-Token": self.APP_TOKEN,
                    "Session-Token": session_token,
                    "Content-Type": "application/json",
                    **FAKE_USER_AGENT
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
                if e.response.status_code == 403:
                    raise Exception("Permisos insuficientes en GLPI para esta consulta.")
                raise Exception(f"Error GLPI ({e.response.status_code}): {e.response.text}")
            except Exception as e:
                raise Exception(f"Error de conexión: {str(e)}")
            finally:
                if session_token:
                    try:
                        headers_kill = {
                            "App-Token": self.APP_TOKEN, 
                            "Session-Token": session_token,
                            **FAKE_USER_AGENT
                        }
                        await client.get(f"{self.GLPI_URL}/killSession", headers=headers_kill)
                    except Exception:
                        pass

    def _get_status_label(self, status_code) -> str:
        try:
            return GLPI_STATUS_MAP.get(int(status_code), f"Estado {status_code}")
        except:
            return str(status_code)

    def _get_priority_label(self, priority_code) -> str:
        try:
            return GLPI_PRIORITY_MAP.get(int(priority_code), f"Prioridad {priority_code}")
        except:
            return str(priority_code)
    
    def _clean_html(self, raw_html: str) -> str:
        if not raw_html: return "Sin contenido"
        clean_text = re.sub(r'<[^>]+>', '', raw_html)
        return clean_text.replace('&nbsp;', ' ').strip()

    def _format_single_ticket(self, ticket: dict) -> str:
        # Aquí puedes añadir más campos si los agregas al forcedisplay
        return (
            f"🎟️ **Ticket #{ticket.get('id')}**\n"
            f"📌 **Asunto:** {ticket.get('name')}\n"
            f"📅 **Fecha:** {ticket.get('date_creation', 'N/A')}\n"
            f"🚦 **Estado:** {self._get_status_label(ticket.get('status'))}\n"
            f"📝 **Descripción:** {self._clean_html(ticket.get('content', ''))}\n"
            F"⚡ **Prioridad:** {self._get_priority_label(ticket.get('priority'))}\n"
        )

    def get_tools(self):
        
        @tool
        async def buscar_ticket_por_id(ticket_id: int) -> str:
            """Busca un ticket en GLPI por su ID numérico."""
            try:
                params = {
                    "criteria[0][field]": 2, # ID
                    "criteria[0][searchtype]": "equals",
                    "criteria[0][value]": ticket_id,
                    
                    "criteria[1][link]": "AND",
                    "criteria[1][field]": 4, # Requester
                    "criteria[1][searchtype]": "equals",
                    "criteria[1][value]": self.user_info.glpi_id,

                    # Campos a mostrar
                    "forcedisplay[0]": 2,  # ID
                    "forcedisplay[1]": 1,  # Name/Title
                    "forcedisplay[2]": 12, # Status
                    "forcedisplay[3]": 3,  # Priority
                    "forcedisplay[4]": 15, # Date creation
                    "forcedisplay[5]": 21, # Content (Descripción)
                }

                search_result = await self._glpi_request("search/Ticket", params=params)
                data = search_result.get("data", [])

                if not data:
                    return f"No se encontró el ticket #{ticket_id} o no tienes permisos para verlo."

                raw_t = data[0]
                
                ticket_dict = {
                    'id': raw_t.get("2"),
                    'name': raw_t.get("1"),
                    'status': raw_t.get("12"),
                    'date_creation': raw_t.get("15"),
                    'content': raw_t.get("21"),
                    'priority': raw_t.get("3")
                }

                if str(ticket_dict['status']).isdigit():
                     ticket_dict['status'] = int(ticket_dict['status'])

                if str(ticket_dict['priority']).isdigit():
                     ticket_dict['priority'] = int(ticket_dict['priority'])
                     
                return self._format_single_ticket(ticket_dict)

            except Exception as e:
                return f"Error buscando ticket: {e}"

        @tool
        async def listar_mis_tickets() -> str:
            """Muestra los últimos tickets del usuario actual."""
            try:
                params = {
                    "criteria[0][field]": 4,
                    "criteria[0][searchtype]": "equals",
                    "criteria[0][value]": self.user_info.glpi_id,
                    "sort": 19, 
                    "order": "DESC",
                    "range": "0-7",
                    "forcedisplay[0]": 2,  # ID
                    "forcedisplay[1]": 1,  # Name/Title
                    "forcedisplay[2]": 12, # Status
                    "forcedisplay[3]": 15,  # Date creation
                    "forcedisplay[4]": 3  # Priority
                }
                
                search_result = await self._glpi_request("search/Ticket", params=params)
                tickets_data = search_result.get("data", [])

                if not tickets_data:
                    return "No tienes tickets registrados."

                lines = ["📋 **Tus últimos tickets:**\n"]
                for t in tickets_data:
                    t_id = t.get("2")
                    t_name = t.get("1")
                    t_status = t.get("12")
                    t_date = t.get("15")
                    t_priority = t.get("3")

                    if str(t_status).isdigit():
                        t_status = self._get_status_label(t_status)
                    if str(t_priority).isdigit():
                        t_priority = self._get_priority_label(t_priority)

                    lines.append(f"- **#{t_id}**: {t_name}\n  Estado: {t_status} | Fecha: {t_date} | Prioridad: {t_priority}\n")
                
                return "\n".join(lines)

            except Exception as e:
                return f"Error al listar tickets: {e}"

        return [buscar_ticket_por_id, listar_mis_tickets]