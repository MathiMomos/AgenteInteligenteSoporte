# Agente Principal (agents-as-tools)
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import Tool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.util.util_llm import get_llm
from src.agente import agente_busqueda, agente_creacion, agente_conocimiento

def get_agente_principal() -> AgentExecutor:
    llm = get_llm()

    tools = [
        Tool(
            name="AgenteBusqueda",
            func=agente_busqueda.handle_query,
            description="Buscar tickets en la base de datos. Devuelve resultados en JSON (mock)."
        ),
        Tool(
            name="AgenteCreacion",
            func=agente_creacion.handle_query,
            description="Crear un ticket nuevo en la base de datos. Devuelve el ticket creado (mock)."
        ),
        Tool(
            name="AgenteConocimiento",
            func=agente_conocimiento.handle_query,
            description="Responder dudas usando la base de conocimientos (RAG)."
        ),
    ]

    system_text = (
        "Eres el Agente Principal de soporte. Tienes 3 herramientas:\n"
        "- AgenteBusqueda: buscar tickets\n"
        "- AgenteCreacion: crear tickets\n"
        "- AgenteConocimiento: responder con la base de conocimientos\n\n"
        "Decide cuál usar según la intención del usuario. Responde en español claro."
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_text),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_openai_functions_agent(
        llm=llm,
        tools=tools,
        prompt=prompt,
    )

    executor = AgentExecutor(agent=agent, tools=tools, verbose=False)
    return executor

_agente_principal_executor = get_agente_principal()

def handle_query(query: str) -> str:
    """
    Interfaz pública usada por main.py.
    Ejecuta el agente principal y devuelve la respuesta como string.
    """
    result = _agente_principal_executor.invoke({"input": query})   # invoke en vez de run
    return result.get("output", "")

