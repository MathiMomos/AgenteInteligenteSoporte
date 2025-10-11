from langchain_openai import AzureChatOpenAI
from src.util import util_keyvault as key

def obtener_llm():
    return AzureChatOpenAI(
        azure_endpoint=key.getkeyapi("CONF-AZURE-ENDPOINT"),
        api_key=key.getkeyapi("CONF-OPENAI-API-KEY"),
        api_version=key.getkeyapi("CONF-API-VERSION"),
        deployment_name=key.getkeyapi("CONF-AZURE-DEPLOYMENT"),
        temperature=0.6
    )