# src/agente/agente_conocimiento.py
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.tools import tool
from langchain_core.runnables import Runnable

from src.util.util_llm import get_llm
from src.util.util_agente import build_rag_prompt
from src.util.util_base_conocimientos import get_retriever

def get_agente_conocimiento_chain() -> Runnable:
    """
    Construye y retorna una cadena de RAG moderna conectada al retriever.
    """
    llm = get_llm()
    prompt = build_rag_prompt(
        role="Agente de Conocimiento",
        instructions=(
            "Usa exclusivamente el contexto recuperado para responder. "
            "Si la respuesta no está en el contexto, di honestamente que no lo sabes."
        )
    )
    retriever = get_retriever()

    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    return rag_chain

_agente_conocimiento_chain = get_agente_conocimiento_chain()

@tool
def agente_conocimiento(query: str) -> str:
    """
    Usa esta herramienta para responder dudas generales y preguntas frecuentes
    basándote en la base de conocimientos interna (RAG).
    """
    result = _agente_conocimiento_chain.invoke({"input": query})
    return result.get("answer", "No se pudo obtener una respuesta de la base de conocimientos.")