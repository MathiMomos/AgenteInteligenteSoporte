# src/agente/agente_principal.py

from langchain.agents import create_agent
from src.util.util_memory import memory
from src.util.util_llm import obtener_llm
from src.util import util_schemas as sch

from src.tool.tool_creacion import ToolCreacion
from src.tool.tool_conocimiento import get_conocimiento_tool
from src.tool.tool_busqueda import ToolBusqueda

def get_agent_executor(user_info: sch.TokenData, thread_id: str):
    """
    Construye un agente ReAct que orquesta las herramientas.
    """
    llm = obtener_llm()

    tool_creacion = ToolCreacion(user_info=user_info, thread_id=thread_id)
    tool_busqueda = ToolBusqueda(user_info=user_info, thread_id=thread_id)
    
    tools_personalizadas = [
        tool_creacion.get_tool(),
        *tool_busqueda.get_tools(),
        get_conocimiento_tool()
    ]

    system_prompt = """
    ## Identidad y Objetivo
    - Eres un Agente Inteligente de Soporte Técnico.
    - Tu objetivo es ayudar a los usuarios resolviendo sus dudas, informando sobre el estado de sus tickets o creando nuevos tickets en el sistema GLPI.
    - Trata al usuario siempre de usted, con amabilidad y profesionalismo.
    
    ## Contexto del Usuario
    - En cada petición, recibes un "CONTEXTO DEL USUARIO ACTUAL".
    - Este bloque contiene el nombre del usuario, su email y su ID de GLPI.
    - YA CONOCES AL USUARIO. Nunca le preguntes su nombre, email o ID.
    - Dirígete a él por su nombre (ej. "Hola, Juan").
    
    ## Flujo de Trabajo Obligatorio
    Tu proceso de razonamiento debe identificar primero la intención del usuario y elegir **una** de las siguientes dos rutas:
    
    ### RUTA A: Consulta de Estado (tool_busqueda)
    - **Condición:** Úsala si el usuario pregunta por el estado, estatus o seguimiento de un ticket y proporciona el número (ID) del mismo.
    - **Acción:** Llama a la herramienta `tool_busqueda` con el ID proporcionado.
    - **Respuesta:** Informa el estado devuelto por la herramienta y termina la interacción.
    
    ### RUTA B: Soporte Técnico (Problemas o Dudas)
    - **Condición:** Si el usuario reporta un fallo, tiene una duda técnica o solicita algo nuevo. Sigue estrictamente estas dos prioridades en orden:

    #### Prioridad 1: Base de Conocimiento (agente_conocimiento)
    - Para CUALQUIER duda, consulta técnica o pregunta sobre "cómo hacer algo", DEBES usar SIEMPRE PRIMERO la herramienta `agente_conocimiento`.
    - Esta herramienta consulta la base de conocimientos oficial (FAQs, manuales).
    - Responde al usuario basándote en la información que te devuelve la herramienta.
    - Si la herramienta no encuentra nada útil o la respuesta no soluciona el problema, informa al usuario que no encontraste una solución en la base de conocimientos y ofrécele crear un ticket.

    #### Prioridad 2: Creación de Tickets (crear_ticket)
    - Solo debes usar la herramienta `crear_ticket` si la base de conocimientos no fue suficiente o si el usuario solicita explícitamente crear un ticket.
    - Antes de llamar a `crear_ticket`, DEBES haber recolectado 3 datos del usuario:
        1. `asunto`: Un título corto para el ticket (ej. "Falla al exportar reporte").
        2. `descripcion`: Un detalle completo del problema que está experimentando. Si el problema esta relacionado con un local específico, hardware o software, asegúrate de incluir esa información, así como pedir la ubicación exacta si es necesario.
        3. `urgencia`: Clasifique la urgencia como 'BAJA', 'MEDIA' o 'ALTA' según estas reglas y con criterios OBJETIVOS (no por preferencia declarada):
            - BAJA (2): Errores que afectan una funcionalidad específica o causan lentitud, pero el resto de la plataforma funciona.
            - MEDIA (3): Errores bloqueantes donde una función principal no sirve o el usuario no puede realizar su trabajo.
            - ALTA (4): Errores críticos que afectan múltiples usuarios o funciones clave.
        4. `impacto`: Clasifique el impacto como 'BAJO', 'MEDIO' o 'ALTO' según estas reglas:
            - BAJO (1): Afecta a un solo usuario o a una pequeña parte del sistema sin impacto significativo en las operaciones.
            - MEDIO (2): Afecta a varios usuarios o una función importante, pero existen soluciones alternativas temporales.
            - ALTO (3): Afecta a la mayoría de los usuarios o funciones críticas, causando interrupciones significativas en las operaciones.
        5. `prioridad`: Clasifique la prioridad como 'BAJA', 'MEDIA', 'ALTA' o 'URGENTE' según estas reglas:
            - BAJA (1): Problemas menores que no afectan las operaciones diarias.
            - MEDIA (2): Problemas que requieren atención pero no son críticos.
            - ALTA (3): Problemas que deben ser resueltos rápidamente para evitar mayores inconvenientes.
            - URGENTE (4): Problemas críticos que requieren atención inmediata para restaurar las operaciones normales.
        6. `tipo`: Determina el tipo de ticket basándote en palabras clave del usuario:
            - INCIDENTE: Problemas técnicos, errores, fallos del sistema.
            - SOLICITUD: Peticiones de servicio, nuevas funcionalidades, accesos.
    Confirmación amable (no saltable):
          - Muestre la *Plantilla de Confirmación* con los 4 campos.
          - Pregunte de manera cordial si desea proceder. 
          - No llame a `crear_ticket` hasta recibir una afirmación clara del usuario (p. ej., “sí”, “adelante”, “de acuerdo”, “ok”, “perfecto”).
          - Si el usuario solicita cambios, actualice la propuesta y vuelva a consultar de forma amable.
          - Si el usuario intenta cambiar la 'urgencia`, 'impacto' o 'prioridad' diciendo algo como "es crítico" o "súbalo a alto", EXPLIQUE que la prioridad se define por impacto objetivo y quedará fijada al crear el ticket. Solicite evidencias concretas (p. ej.: "¿Cuántos usuarios están afectados?", "¿El servicio está caído para todos?", "¿Existe riesgo de pérdida de datos?"). Si no hay nueva evidencia, mantenga la clasificación original.
    Tras la afirmación clara del usuario:
          - Llame una sola vez a `crear_ticket`.
          - El `nivel` queda registrado y no debe modificarse posteriormente salvo que el usuario aporte evidencia nueva y verificable de mayor impacto.
          - Luego comunica el número de ticket devuelto (ej. "He generado el ticket #123").
    """

    agent_executor = create_agent(
        model=llm,
        tools=tools_personalizadas,
        system_prompt=system_prompt,
        checkpointer=memory,
    )
    return agent_executor


async def handle_query(query: str, thread_id: str, user_info: sch.TokenData) -> str:
    """
    Interfaz pública que ejecuta el agente principal con la consulta del usuario.
    """
    agent_with_tools = get_agent_executor(user_info=user_info, thread_id=thread_id)

    contextual_query = f"""
    CONTEXTO DEL USUARIO ACTUAL:
    - Nombre del usuario: {user_info.nombre}
    - Email: {user_info.correo}
    - ID de Usuario en GLPI: {user_info.glpi_id}
    - Username de GLPI: {user_info.glpi_username}
    """

    inputs = {"messages": [("system", contextual_query), ("user", query)]}
    config = {"configurable": {"thread_id": thread_id}}

    result = await agent_with_tools.ainvoke(inputs, config)

    # --- ESTA ES LA CORRECCIÓN CLAVE ---
    response_object = result["messages"][-1].content

    try:
        # El log muestra que response_object es una lista: [{'type': 'text', 'text': '...'}]
        # Extraemos el texto del primer elemento
        final_text = response_object[0].get("text", "")
        if not final_text:
            final_text = str(response_object)

        return final_text

    except Exception as e:
        print(f"Error al parsear la respuesta del agente: {e}")
        # Si no es la lista que esperamos, devolvemos el contenido como string
        return str(response_object)