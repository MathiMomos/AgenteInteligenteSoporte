# src/util/util_agente.py
from langchain.prompts import ChatPromptTemplate
import json
from typing import Any

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
    Prompt para RAG: espera {context} y {question}. Usar con RetrievalQA via chain_type_kwargs={"prompt": prompt}
    """
    system_text = (
        f"Rol: {role}\n"
        f"Instrucciones: {instructions}\n\n"
        "Usa exclusivamente el contexto recuperado para responder. Si no está la respuesta, dilo honestamente."
    )
    # El template para RetrievalQA (chain_type='stuff') espera {context} y {question}
    return ChatPromptTemplate.from_messages([
        ("system", system_text),
        ("user", "Contexto:\n{context}\n\nPregunta: {question}\n\nResponde basándote únicamente en el contexto.")
    ])


def extract_invoke_result(result: Any) -> str:
    """
    Normaliza/extrae el texto final de distintas estructuras devueltas por .invoke().
    Busca keys comunes: 'output', 'result', 'text', 'answer', etc. Si no encuentra,
    intenta serializar el primer valor string o devuelve el JSON completo.
    """
    if isinstance(result, str):
        return result

    if isinstance(result, dict):
        for k in ("output", "result", "answer", "text", "response"):
            if k in result:
                v = result[k]
                if isinstance(v, str):
                    return v
                try:
                    return json.dumps(v, ensure_ascii=False)
                except Exception:
                    return str(v)
        # si no encontró keys conocidas, intentar extraer primer valor string
        for v in result.values():
            if isinstance(v, str):
                return v
        # fallback: serializar todo
        try:
            return json.dumps(result, ensure_ascii=False)
        except Exception:
            return str(result)

    # fallback genérico
    try:
        return str(result)
    except Exception:
        return ""
