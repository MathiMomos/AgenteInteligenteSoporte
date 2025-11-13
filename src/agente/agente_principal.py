# src/agente/agente_principal.py

from langchain.agents import create_agent
from src.util.util_memory import memory
from src.util.util_llm import obtener_llm
from src.util import util_schemas as sch

from src.tool.tool_creacion import ToolCreacion
from src.tool.tool_conocimiento import get_conocimiento_tool


def get_agent_executor(user_info: sch.TokenData, thread_id: str):
    """
    Construye un agente ReAct que orquesta las herramientas.
    YA NO RECIBE db: Session.
    """
    llm = obtener_llm()

    tool_creacion = ToolCreacion(user_info=user_info, thread_id=thread_id)

    tools_personalizadas = [
        tool_creacion.get_tool(),
        get_conocimiento_tool()
    ]

    # --- NUEVO PROMPT SIMPLIFICADO ---
    # Este prompt se enfoca solo en GLPI y la Base de Conocimiento.
    system_prompt = """
    ## Identidad y Objetivo
    - Eres un Agente Inteligente de Soporte Técnico.
    - Tu objetivo es ayudar a los usuarios resolviendo sus dudas o creando un ticket de soporte en el sistema GLPI.
    - Trata al usuario siempre de usted, con amabilidad y profesionalismo.

    ## Contexto del Usuario
    - En cada petición, recibes un "CONTEXTO DEL USUARIO ACTUAL".
    - Este bloque contiene el nombre del usuario, su email y su ID de GLPI.
    - YA CONOCES AL USUARIO. Nunca le preguntes su nombre, email o ID.
    - Dirígete a él por su nombre (ej. "Hola, Juan").

    ## Flujo de Trabajo Obligatorio
    Tu proceso de razonamiento debe seguir estrictamente estas dos prioridades:

    ### Prioridad 1: Base de Conocimiento (agente_conocimiento)
    - Para CUALQUIER duda, consulta técnica o pregunta sobre "cómo hacer algo", DEBES usar SIEMPRE PRIMERO la herramienta `agente_conocimiento`.
    - Esta herramienta consulta la base de conocimientos oficial (FAQs, manuales).
    - Responde al usuario basándote en la información que te devuelve la herramienta.
    - Si la herramienta no encuentra nada útil o la respuesta no soluciona el problema, informa al usuario que no encontraste una solución en la base de conocimientos y ofrécele crear un ticket.

    ### Prioridad 2: Creación de Tickets (crear_ticket)
    - Solo debes usar la herramienta `crear_ticket` si la base de conocimientos no fue suficiente o si el usuario solicita explícitamente crear un ticket.
    - Antes de llamar a `crear_ticket`, DEBES haber recolectado 3 datos del usuario:
        1. `asunto`: Un título corto para el ticket (ej. "Falla al exportar reporte").
        2. `descripcion`: Un detalle completo del problema que está experimentando.
        3. `urgencia`: La urgencia que el usuario percibe. Debes clasificarla como: MUY_BAJA (1), BAJA (2), MEDIA (3), ALTA (4), o MUY_ALTA (5).
    - Una vez tengas estos 3 datos, confirma con el usuario (ej. "Entendido, crearé un ticket con urgencia ALTA...") y llama a la herramienta `crear_ticket`.
    - Informa al usuario el número de ticket que te devolvió la herramienta (ej. "He generado el ticket #123").
    """

    agent_executor = create_agent(
        model=llm,
        tools=tools_personalizadas,
        system_prompt=system_prompt,
        checkpointer=memory,
    )
    return agent_executor


# ¡IMPORTANTE! Esta función ahora debe ser 'async'
async def handle_query(query: str, thread_id: str, user_info: sch.TokenData) -> str:
    """
    Interfaz pública que ejecuta el agente principal con la consulta del usuario.
    YA NO RECIBE db: Session.
    """
    # Ya no recibe 'db'
    agent_with_tools = get_agent_executor(user_info=user_info, thread_id=thread_id)

    # Actualizamos el contexto para que coincida con el nuevo sch.TokenData
    contextual_query = f"""
    CONTEXTO DEL USUARIO ACTUAL:
    - Nombre del usuario: {user_info.nombre}
    - Email: {user_info.correo}
    - ID de Usuario en GLPI: {user_info.glpi_id}
    - Username de GLPI: {user_info.glpi_username}
    """

    inputs = {"messages": [("system", contextual_query), ("user", query)]}
    config = {"configurable": {"thread_id": thread_id}}

    # ¡CAMBIO! Usamos 'ainvoke' (asíncrono) porque 'tool_creacion' es 'async'
    result = await agent_with_tools.ainvoke(inputs, config)

    return result["messages"][-1].content