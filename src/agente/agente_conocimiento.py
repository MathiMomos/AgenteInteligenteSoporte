# src/agente/agente_conocimiento.py
from langchain.chains import RetrievalQA
from src.util.util_llm import get_llm
from src.util.util_agente import build_rag_prompt, extract_invoke_result
from src.util.util_base_conocimientos import get_retriever

def get_agente_conocimiento_chain() -> RetrievalQA:
    """
    Construye y retorna el RetrievalQA conectado al retriever de Azure AISearch.
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

    qa = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        chain_type_kwargs={"prompt": prompt},
        return_source_documents=False
    )
    return qa

# Instancia global (se crea al importar el módulo).
_agente_conocimiento_chain = get_agente_conocimiento_chain()

def handle_query(query: str) -> str:
    """
    Ejecuta el RAG y devuelve string. Usa .invoke() (no .run()) y normaliza el resultado.
    """
    # invoke devuelve un dict; normalizamos con extract_invoke_result
    result = _agente_conocimiento_chain.invoke({"query": query})
    return extract_invoke_result(result)
