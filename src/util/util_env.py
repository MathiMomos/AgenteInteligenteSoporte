import os
from dotenv import load_dotenv

load_dotenv()

def require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise EnvironmentError(f"Falta la variable {name}")
    return value
