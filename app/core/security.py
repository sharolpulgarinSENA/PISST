# app/core/security.py
from datetime import datetime, timedelta, timezone
from jose import jwt
import warnings
import re
from passlib.context import CryptContext
from dotenv import load_dotenv
from fastapi import HTTPException
import os

load_dotenv()

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", ".*bcrypt.*")
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY no está configurada en .env")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))


def validar_fortaleza_password(password: str) -> None:
    errores = []
    if len(password) < 8:
        errores.append("mínimo 8 caracteres")
    if not re.search(r"[A-Z]", password):
        errores.append("al menos una mayúscula")
    if not re.search(r"[a-z]", password):
        errores.append("al menos una minúscula")
    if not re.search(r"\d", password):
        errores.append("al menos un número")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-]", password):
        errores.append("al menos un símbolo (!@#$%...)")
    if errores:
        raise HTTPException(
            status_code=400,
            detail=f"Contraseña débil. Requisitos: {', '.join(errores)}",
        )


def get_password_hash(password: str) -> str:
    """
    Convierte una contraseña en texto plano a su hash bcrypt.
    Ejemplo: "demo123" → "$2b$12$xxxxxxxxxxxxxxxxxxxxx"
    Este hash NO se puede revertir a la contraseña original.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña coincide con su hash.
    Retorna True si coinciden, False si no.
    Se usa en el login para validar la contraseña del usuario.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """
    Crea un token JWT con los datos del usuario y tiempo de expiración.
    El token contiene: id del usuario, rol y fecha de expiración.
    Se envía al frontend cuando el usuario hace login exitoso.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
        minutes=EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decodifica y valida un token JWT.
    Retorna los datos del token si es válido.
    Lanza JWTError si el token es inválido o expiró.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
