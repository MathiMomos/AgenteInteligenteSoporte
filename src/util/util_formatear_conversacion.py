from langchain_core.messages import AIMessage, HumanMessage
def format_conversation(messages: list) -> list[dict]:
    """
    Convierte una lista de mensajes de LangChain en un JSON serializable.
    """
    formatted = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            role = "user"
        elif isinstance(msg, AIMessage):
            role = "agent"
        else:
            continue

        formatted.append({
            "role": role,
            "content": msg.content,
        })
    return formatted
