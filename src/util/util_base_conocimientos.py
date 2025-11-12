from langchain_community.retrievers.azure_ai_search import AzureAISearchRetriever
from src.util import util_keyvault as key

def obtener_bc() -> AzureAISearchRetriever:
    """
    Devuelve un retriever usando Azure AI Search (AzureAISearchRetriever).
    """
    nombre_servicio = "bclumin" # CAMBIAR NOMBRE
    nombre_index = "utp" # CAMBIAR NOMBRE
    
    retriever = AzureAISearchRetriever(
        service_name=nombre_servicio,
        index_name=nombre_index,
        api_key=key.getkeyapi("CONF-AZURE-SEARCH-KEY"),
        top_k=5
    )
    
    return retriever