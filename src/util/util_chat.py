## #######################################################################################################
## @section Librerías
# #######################################################################################################
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory


## #######################################################################################################
## @section Funciones
# #######################################################################################################
def crear_cadena_conversacional_rag(llm, retriever):
    """
    Crea una cadena de RAG conversacional, diseñada para funcionar con memoria.
    """
    memoria_conversacional = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )

    cadena = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memoria_conversacional,
        return_source_documents=False
    )
    return cadena


def ejecutar_cadena_rag(cadena: ConversationalRetrievalChain, pregunta: str):
    """
    Ejecuta la cadena de RAG conversacional y extrae la respuesta.
    """
    resultado = cadena.invoke({"question": pregunta})
    return resultado["answer"]