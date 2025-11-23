# src/auth/security.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from pydantic import ValidationError

# Importamos nuestros esquemas desde su ubicación en 'util'
from src.util import util_schemas as sch

### Configuración de Seguridad
from src.util import util_keyvault as key

SECRET_KEY = key.getkeyapi("SECRET-KEY")
if not SECRET_KEY:
    raise ValueError("No se pudo obtener la llave secreta (SECRET-KEY).")

# Algoritmo y tiempo de vida del token
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 horas

# ¡CAMBIO! Apunta a nuestro nuevo endpoint de login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


### Funciones Principales

def create_access_token(data: sch.TokenData) -> str:
    """
    Crea un JWT (nuestro "pase") con los datos del TokenData de GLPI.
    """
    to_encode = data.model_dump()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # 'sub' (subject) es el estándar para identificar al usuario, usamos el correo
    to_encode.update({"exp": expire, "sub": data.correo})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme)) -> sch.TokenData:
    """
    Dependencia de FastAPI.
    Valida nuestro JWT y devuelve los datos del usuario (TokenData).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Reconstruimos nuestro objeto TokenData desde el payload
        token_data = sch.TokenData(
            glpi_id=payload.get("glpi_id"),
            nombre=payload.get("nombre"),
            correo=payload.get("correo"),
            glpi_username=payload.get("glpi_username"),
            glpi_entity_id = payload.get("glpi_entity_id"),
            glpi_entity_name = payload.get("glpi_entity_name")
        )

        if token_data.correo is None:
            raise credentials_exception

    except (JWTError, ValidationError, AttributeError):
        # Captura si el token es inválido, los campos no coinciden, o faltan
        raise credentials_exception

    return token_data

# (Todas las funciones de Google y de Admin han sido eliminadas)