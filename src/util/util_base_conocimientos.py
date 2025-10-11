from langchain_community.retrievers.azure_ai_search import AzureAISearchRetriever
from src.util import util_keyvault as key

def obtener_bc() -> AzureAISearchRetriever:
    """
    Devuelve un retriever usando Azure AI Search (AzureAISearchRetriever).
    """
    retriever = AzureAISearchRetriever(
        service_name=key.getkeyapi("CONF-AZURE-SEARCH-SERVICE-NAME"),
        index_name=key.getkeyapi("CONF-AZURE-INDEX"),
        api_key=key.getkeyapi("CONF-AZURE-SEARCH-KEY"),
        top_k=5
    )
    return retriever