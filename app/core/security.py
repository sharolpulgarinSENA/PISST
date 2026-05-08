# app/core/security.py
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
import os

load_dotenv()

# CryptContext: configura el algoritmo de hashing
# bcrypt es el estándar de la industria para contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))


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
    expire = datetime.utcnow() + timedelta(minutes=EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decodifica y valida un token JWT.
    Retorna los datos del token si es válido.
    Lanza JWTError si el token es inválido o expiró.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
