from langchain.tools.retriever import create_retriever_tool
from src.util.util_base_conocimientos import obtener_bc


def get_conocimiento_tool():
    """
    Fábrica que construye la herramienta de conocimiento (RAG).

    Usa la función 'create_retriever_tool' de LangChain para encapsular
    nuestro retriever de la base de conocimientos de una manera optimizada.
    """
    # 1. Obtenemos nuestro retriever (el que se conecta a Azure AI Search)
    retriever = obtener_bc()

    # 2. Usamos la fábrica de LangChain para crear la herramienta
    conocimiento_tool = create_retriever_tool(
        retriever,
        "agente_conocimiento",  # El nombre que el LLM usará para llamar a la herramienta
        (
            "Usa esta herramienta para responder dudas generales y preguntas frecuentes "
            "basándote en la base de conocimientos interna (documentos de soporte, FAQs, etc.). "
            "Pásale la pregunta exacta del usuario a esta herramienta."
        )
    )

    return conocimiento_tool