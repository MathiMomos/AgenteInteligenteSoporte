from langchain_core.tools import Tool
from src.util.util_base_conocimientos import obtener_bc


def get_conocimiento_tool():
    """
    Fábrica que construye la herramienta de conocimiento (RAG).

    Usa la función 'create_retriever_tool' de LangChain para encapsular
    nuestro retriever de la base de conocimientos de una manera optimizada.
    """
    def buscar_documentos_wrapper(query: str) -> str:
        docs = retriever.invoke(query)
        return "\n\n".join([d.page_content for d in docs])
    # 1. Obtenemos nuestro retriever (el que se conecta a Azure AI Search)
    retriever = obtener_bc()

    return Tool.from_function(
        func=buscar_documentos_wrapper,
        name="BaseDeConocimientos",
        description=(
            "Eres BC_Tool. Sólo puedes buscar y devolver fragmentos de la base de conocimiento."
            "No inventes contenido. Devuelve texto y metadatos de la fuente."
            "Si no encuentras resultados relevantes, responde vacío."
        ),
    )