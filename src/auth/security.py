# src/auth/security.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from pydantic import ValidationError

# Importamos nuestros esquemas desde su ubicación en 'util'
from src.util import util_schemas as sch

### Configuración de Seguridad
from src.util import util_keyvault as key

## Google
from google.oauth2 import id_token
from google.auth.transport import requests as grequests

SECRET_KEY = key.getkeyapi("SECRET-KEY")
if not SECRET_KEY:
    raise ValueError("No se pudo obtener la llave secreta de Google OAuth.")

# Algoritmo y tiempo de vida del token
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 horas

# Esta es una dependencia de FastAPI para extraer el "Bearer Token" del header.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/google/login")


### Funciones Principales

def create_access_token(data: sch.TokenData) -> str:
    to_encode = data.model_dump()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme)) -> sch.TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_data = sch.TokenData(**payload)
    except (JWTError, ValidationError):
        raise credentials_exception

    return token_data

# --- FUNCIÓN AUXILIAR PARA VERIFICAR TOKEN (EVITA REPETIR CÓDIGO) ---
def verify_google_token(id_token_str: str) -> dict:
    """Verifica el token de Google y devuelve la información del usuario."""
    google_client_id = key.getkeyapi("GOOGLE-CLIENT-ID")
    if not google_client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID no configurado")

    try:
        id_info = id_token.verify_oauth2_token(
            id_token_str, grequests.Request(), google_client_id
        )
        if id_info.get("iss") not in (
                "accounts.google.com",
                "https://accounts.google.com",
        ):
            raise HTTPException(status_code=401, detail="Issuer inválido")
        return id_info
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Token de Google inválido: {e}")

def get_current_admin_user(current_user: sch.TokenData = Depends(get_current_user)) -> sch.TokenData:
    """
    Una dependencia que verifica si el usuario actual es EL administrador hardcodeado.
    """
    ADMIN_EMAIL = "grupo2soporteadm@gmail.com"
    if not ADMIN_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ADMIN_EMAIL no está configurado en el servidor."
        )

    if current_user.correo.lower() != ADMIN_EMAIL.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de administrador para realizar esta acción."
        )

    # 3. Si es el admin, devolvemos sus datos
    return current_user