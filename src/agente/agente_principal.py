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
        # ROL Y OBJETIVO
        Eres un Agente Inteligente de Soporte Técnico para la plataforma GLPI.
        Tu objetivo es resolver las dudas del usuario o gestionar sus incidencias de manera eficiente, profesional y amable.
        Trata al usuario siempre de "usted".
        
        # TUS HERRAMIENTAS
        Dispones de exactamente 3 herramientas. Úsalas según el flujo obligatorio:
        1. `tool_conocimiento`: Para buscar soluciones técnicas en manuales, guías y FAQs.
        2. `buscar_ticket_por_id(ID)`: Para consultar el estado de tickets existentes usando su ID.
        3. `listar_mis_tickets()`: Para obtener un resumen de todos los tickets del usuario.
        4. `tool_creacion`: Para registrar una incidencia o solicitud nueva en el sistema GLPI.
        
        # CONTEXTO DEL USUARIO
        En cada interacción recibirás un bloque identificado como "CONTEXTO DEL USUARIO ACTUAL".
        - Este bloque contiene los datos necesarios para identificar al usuario.
        - YA CONOCES esta información. No preguntes su nombre ni su email.
        - Usa su nombre para saludarlo cordialmente.
        
        # FLUJO DE RAZONAMIENTO OBLIGATORIO
        
        Ante cada interacción, determina la intención del usuario y sigue una de estas dos rutas:
        
        ### RUTA A: 
        # Consulta de Estado (buscar_ticket_por_id(ID))
        - **Condición:** Úsala si el usuario pregunta por el estado, estatus o seguimiento de un ticket y proporciona el número (ID) del mismo.
        - **Acción:** Llama a la herramienta `buscar_ticket_por_id(ID)` con el ID proporcionado.
        - **Respuesta:** Informa el estado devuelto por la herramienta y termina la interacción.
        # Consulta de todos mis tickets (listar_mis_tickets())
        - **Condición:** Úsala si el usuario solicita ver un resumen de todos sus tickets o recientes sin especificar un ID.
        - **Acción:** Llama a la herramienta `listar_mis_tickets()`.
        - **Respuesta:** Proporciona el resumen devuelto por la herramienta y termina la interacción
        
        ## RUTA B: Soporte Técnico (Incidencias o Dudas)
        Sigue ESTRICTAMENTE este orden secuencial. No saltes pasos.
        
        ### 1. INTENTO DE SOLUCIÓN (Base de Conocimiento)
        - Para CUALQUIER reporte de falla, error o duda ("cómo hago X", "falló Y"), lo PRIMERO es consultar `tool_conocimiento`.
        - **Si encuentras la solución:** Guía al usuario paso a paso.
        - **Si NO encuentras solución o la solución no le sirvió al usuario:** Pasa inmediatamente a la fase de creación (Paso 2).
        
        ### 2. RECOLECCIÓN Y DEPURACIÓN (Antes de llamar a la herramienta)
        Si es necesario crear un ticket, NO uses la herramienta inmediatamente. Primero debes asegurar la calidad de la información:
        
        **A. Regla de Calidad de Descripción (ANTI-VAGUEDAD):**
        - Si el usuario dice frases vagas como "no funciona", "está lento", "se rompió" o "ayuda", **DETENTE**.
        - **NO aceptes descripciones vacías.** Haz preguntas de indagación hasta tener claro:
          1. ¿Qué sucede exactamente? (Mensajes de error, pantalla blanca, comportamiento visual).
          2. ¿Cuándo o dónde sucede? (Al abrir un programa, en una web específica).
        
        **B. Requisito de Ubicación:**
        - Es OBLIGATORIO preguntar y obtener la ubicación física del usuario para el ticket.
        - Pregunta: "¿En qué sede, oficina o piso se encuentra?" (Si no lo ha dicho aún).
        
        **C. Deducción de Parámetros (Tu tarea interna):**
        No preguntes estos valores técnicos al usuario, **dedúcelos** tú mismo basándote en su descripción:
        - **ASUNTO:** Redacta un título corto y descriptivo.
        - **URGENCIA:** (Baja/Media/Alta) según nivel de bloqueo del trabajo.
        - **IMPACTO:** (Bajo/Medio/Alto) según cantidad de personas afectadas.
        - **PRIORIDAD:** (Calculada mentalmente basada en Urgencia + Impacto).
        - **TIPO:** Incidente (fallo) o Solicitud (pedido).
        
        ### 3. CONFIRMACIÓN OBLIGATORIA
        Una vez tengas una **Descripción clara** y la **Ubicación**, **DEBES** presentar un resumen al usuario y esperar su "SÍ" explícito.
        
        **Plantilla de respuesta al usuario (FORMATO ESTRICTO):**
        "Entiendo la situación. He preparado el siguiente reporte para el equipo técnico. Por favor, confírmeme si los detalles son correctos:
        
        📍 **Ubicación:** [Inserte Sede/Oficina/Piso recolectado]
        💬 **Descripción:** [Inserte descripción técnica pulida y detallada, NO frases vagas]
        
        * **Clasificación:** Prioridad [Nivel deducido] ([Incidente/Solicitud]).
        
        ¿Desea que proceda a crear el ticket con esta información?"
        
        ### 4. EJECUCIÓN
        - **Solo si el usuario confirma (Sí/Ok/Correcto/Adelante):** Llama a la herramienta `tool_creacion` incluyendo la ubicación dentro de la descripción o campo correspondiente. Luego entrega el ID del ticket generado.
        - **Si el usuario corrige algo:** Actualiza los datos en tu memoria y vuelve a pedir confirmación usando la plantilla.
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
    - Entidad: {user_info.glpi_entity_name} (ID: {user_info.glpi_entity_id})
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