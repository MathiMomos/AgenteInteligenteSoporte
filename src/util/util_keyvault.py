from azure.identity import DefaultAzureCredential

from azure.keyvault.secrets import SecretClient

vault_name = "analytics-soporte-kv"
KVUri = f"https://{vault_name}.vault.azure.net"

credential = DefaultAzureCredential()
client = SecretClient(vault_url=KVUri, credential=credential)

def getkeyapi(name: str) -> str:

    secret = client.get_secret(name)
    if secret.value is None:
        raise ValueError(f"Secret '{name}' does not have a value.")
    return secret.value
