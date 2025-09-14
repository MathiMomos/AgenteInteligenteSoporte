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

# Lee la clave secreta del archivo ..env
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("No se encontró SECRET_KEY en las variables de entorno.")

# Algoritmo y tiempo de vida del token
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 horas

# Esta es una dependencia de FastAPI para extraer el "Bearer Token" del header.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/google/login")


### Funciones Principales

def create_access_token(data: sch.TokenData) -> str:
    to_encode = data.dict()
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