# src/agente/agente_principal.py
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from src.util.util_llm import get_llm
from src.agente.agente_busqueda import buscar_ticket
from src.agente.agente_creacion import crear_ticket
from src.agente.agente_conocimiento import agente_conocimiento


def get_agente_langgraph():
    """
    Construye y retorna el agente ejecutor de LangGraph con memoria persistente.
    """
    llm = get_llm()

    tools = [
        buscar_ticket,
        crear_ticket,
        agente_conocimiento,
    ]

    system_text = (
        "Eres el Agente Principal de soporte. Tienes acceso a varias herramientas para ayudar al usuario.\n"
        "Dependiendo de la intención del usuario, debes elegir la herramienta más adecuada e invocarla con los parámetros correctos.\n"
        "Responde siempre en español de forma clara y amigable, utilizando el contexto de la conversación si es relevante."
    )

    memory = MemorySaver()

    app = create_react_agent(
        model=llm,
        tools=tools,
        prompt=system_text,
        checkpointer=memory
    )
    return app


_agente_langgraph_app = get_agente_langgraph()


def handle_query(query: str, thread_id: str) -> str:
    """
    Interfaz pública usada por main.py. Ejecuta el agente de LangGraph.
    """
    inputs = {"messages": [("user", query)]}
    config = {"configurable": {"thread_id": thread_id}}
    result = _agente_langgraph_app.invoke(inputs, config)
    return result["messages"][-1].content