from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.prebuilt import create_react_agent
from langchain.agents import tool
from sqlalchemy.orm import Session
from src.util import util_schemas as sch
from src.util.util_llm import get_llm
from src.crud import crud_tickets


def get_agente_busqueda(db: Session, user_info: sch.TokenData):
    """
    Devuelve un tool que encapsula un mini-agente ReAct encargado de la
    búsqueda de tickets. Este mini-agente puede:
      1. Buscar ticket por ID
      2. Listar tickets abiertos
      3. Buscar tickets por asunto
    """

    # --- Tools internas del mini-agente ---
    def buscar_por_id(ticket_id: int) -> str:
        """Busca un ticket específico por su número de ID."""
        ticket = crud_tickets.get_ticket_by_id_db(db, ticket_id, user_info)
        if ticket:
            return f"Ticket #{ticket.id_ticket} - {ticket.asunto} (estado: {ticket.estado})"
        return f"No encontré el ticket #{ticket_id} o no pertenece a este colaborador."

    def listar_abiertos() -> str:
        """Lista todos los tickets abiertos (no finalizados) del colaborador actual."""
        tickets = crud_tickets.get_all_open_tickets(db, user_info)
        if not tickets:
            return "No tienes tickets abiertos actualmente."
        return "\n".join(
            [f"#{t.id_ticket} - {t.asunto} (estado: {t.estado})" for t in tickets]
        )

    def buscar_por_asunto(subject: str) -> str:
        """Busca tickets cuyo asunto coincida parcialmente con el texto dado."""
        tickets = crud_tickets.get_tickets_by_subject(db, subject, user_info)
        if not tickets:
            return f"No encontré tickets relacionados con: '{subject}'."
        return "\n".join(
            [f"#{t.id_ticket} - {t.asunto} (estado: {t.estado})" for t in tickets]
        )

    tools = [buscar_por_id, listar_abiertos, buscar_por_asunto]

    # --- Prompt del mini-agente ---
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
        Eres un asistente especializado en búsqueda de tickets.
        Debes decidir si el usuario quiere:
        1. Consultar un ticket por ID (ej: "ticket 5").
        2. Listar todos los tickets abiertos.
        3. Buscar tickets relacionados a un asunto.

        Siempre responde en español, claro y conciso.
        """),
        MessagesPlaceholder(variable_name="messages"),
    ])

    # --- Construcción del mini-agente ---
    llm = get_llm()
    mini_agente = create_react_agent(model=llm, tools=tools, prompt=prompt)

    # --- Wrapper como tool ---
    @tool
    def agente_busqueda(query: str) -> str:
        """Usa esta herramienta para consultar tickets (por ID, listar abiertos o por asunto)."""
        result = mini_agente.invoke({"messages": [("user", query)]})
        return result["messages"][-1].content

    return agente_busqueda
