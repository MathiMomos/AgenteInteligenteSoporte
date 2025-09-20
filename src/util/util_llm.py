from langchain_openai import AzureChatOpenAI
from src.util import util_env as key

def obtener_llm():
    return AzureChatOpenAI(
        azure_endpoint=key.require("CONF_AZURE_ENDPOINT"),
        api_key=key.require("CONF_OPENAI_API_KEY"),
        api_version=key.require("CONF_API_VERSION"),
        deployment_name=key.require("CONF_AZURE_DEPLOYMENT"),
        temperature=0.6
    )