from platform import system

from langgraph.prebuilt import create_react_agent
from src.util.util_memory import memory
from sqlalchemy.orm import Session
from src.util.util_llm import obtener_llm
from src.util import util_schemas as sch

from src.tool.tool_creacion import ToolCreacion
from src.tool.tool_busqueda import ToolBusqueda
from src.tool.tool_conocimiento import get_conocimiento_tool
from src.util.util_prompt import PROMPT_CACHE


def get_agent_executor(db: Session, user_info: sch.TokenData, thread_id: str):
    """
    Construye un agente ReAct que orquesta las herramientas personalizadas.
    """
    llm = obtener_llm()

    tool_creacion = ToolCreacion(db, user_info, thread_id)
    tool_busqueda = ToolBusqueda(db, user_info)

    tools_personalizadas = [
        *tool_busqueda.get_tools(),
        tool_creacion.get_tool(),
        get_conocimiento_tool()
    ]


    agent_executor = create_react_agent(
        model=llm,
        tools=tools_personalizadas,
        prompt=PROMPT_CACHE["prompt"],
        checkpointer=memory,
    )
    return agent_executor


def handle_query(query: str, thread_id: str, user_info: sch.TokenData, db: Session) -> str:
    """
    Interfaz pública que ejecuta el agente principal con la consulta del usuario.
    """
    agent_with_tools = get_agent_executor(db=db, user_info=user_info, thread_id=thread_id)

    nombres_servicios = [s.nombre for s in user_info.servicios_contratados]
    servicios_texto = ", ".join(nombres_servicios) if nombres_servicios else "Ninguno"

    contextual_query = f"""
    CONTEXTO DEL USUARIO ACTUAL:
    - Nombre del usuario: {user_info.nombre}
    - Empresa del usuario: {user_info.cliente_nombre}
    - Servicios contratados por la empresa: {servicios_texto}
    """

    inputs = {"messages": [("system", contextual_query), ("user", query)]}
    config = {"configurable": {"thread_id": thread_id}}
    result = agent_with_tools.invoke(inputs, config)
    return result["messages"][-1].content
