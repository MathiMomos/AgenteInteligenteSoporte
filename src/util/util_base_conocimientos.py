# src/util/util_base_conocimientos.py
from langchain_community.retrievers.azure_ai_search import AzureAISearchRetriever
from src.util import util_env as key

def get_retriever() -> AzureAISearchRetriever:
    """
    Devuelve un retriever usando Azure AI Search (AzureAISearchRetriever).
    """
    retriever = AzureAISearchRetriever(
        service_name=key.require("CONF_AZURE_SEARCH_SERVICE_NAME"),
        index_name=key.require("CONF_AZURE_INDEX"),
        api_key=key.require("CONF_AZURE_SEARCH_KEY"),
        top_k=5
    )
    return retriever
