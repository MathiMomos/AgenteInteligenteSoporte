from azure.identity import DefaultAzureCredential

from azure.keyvault.secrets import SecretClient

vault_name = "keylumin"
KVUri = f"https://{vault_name}.vault.azure.net"

credential = DefaultAzureCredential()
client = SecretClient(vault_url=KVUri, credential=credential)

def getkeyapi(name: str) -> str:

    secret = client.get_secret(name)
    if secret.value is None:
        raise ValueError(f"Secret '{name}' does not have a value.")
    return secret.value

def get_glpi_url() -> str:
    """Devuelve la URL base de la API de GLPI"""
    return getkeyapi("GLPI-URL")

def get_glpi_app_token() -> str:
    """Devuelve el App-Token de GLPI."""
    return getkeyapi("GLPI-APP-TOKEN")

def get_glpi_system_user_token() -> str:
    """
    Devuelve el User-Token de un usuario de "Sistema" en GLPI.
    Este se usa para que el bot cree tickets en nombre de los usuarios.
    """
    return getkeyapi("GLPI-SYSTEM-USER-TOKEN")

