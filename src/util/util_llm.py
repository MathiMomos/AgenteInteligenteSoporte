from langchain_google_genai import ChatGoogleGenerativeAI
from src.util import util_keyvault as key

def obtener_llm() -> ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            api_key= key.getkeyapi("CONF-GOOGLE-API-KEY"),
        )