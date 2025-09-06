# src/util/util_agente.py
from langchain.prompts import ChatPromptTemplate

def build_system_prompt(role: str, instructions: str) -> ChatPromptTemplate:
    """
    Prompt genérico: usa {input} como placeholder para la entrada del usuario.
    """
    system_text = (
        f"Rol: {role}\n"
        f"Instrucciones: {instructions}\n\n"
        "Responde en español, claro y directo."
    )
    return ChatPromptTemplate.from_messages([
        ("system", system_text),
        ("user", "{input}")
    ])

def build_rag_prompt(role: str, instructions: str) -> ChatPromptTemplate:
    """
    Prompt para RAG: espera {context} y {input}. Usar con cadenas RAG de LCEL.
    """
    system_text = (
        f"Rol: {role}\n"
        f"Instrucciones: {instructions}\n\n"
        "Usa exclusivamente el contexto recuperado para responder. Si no está la respuesta, dilo honestamente."
    )
    return ChatPromptTemplate.from_messages([
        ("system", system_text),
        ("user", "Contexto:\n{context}\n\nPregunta: {input}\n\nResponde basándote únicamente en el contexto.")
    ])