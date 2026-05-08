# app/routers/auth_router.py
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel, EmailStr
from typing import Optional
import httpx, os, secrets
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import User, RoleEnum

router = APIRouter(prefix="/auth", tags=["Autenticación"])

# Rate limiter: limita las peticiones por IP
limiter = Limiter(key_func=get_remote_address)


# ── Schemas (modelos de datos de entrada y salida) ────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    recaptcha_token: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    nombre: str

class RegisterRequest(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    role: str
    empresa_id: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# ── Función auxiliar ─────────────────────────────────────────────

async def validar_recaptcha(token: str) -> bool:
    """
    Valida el token reCAPTCHA con la API de Google.
    Retorna True si es válido, False si no.
    En desarrollo se puede omitir con ENVIRONMENT=development.
    """
    if os.getenv("ENVIRONMENT") == "development":
        return True  # omitir validación en desarrollo local

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={
                "secret": os.getenv("RECAPTCHA_SECRET_KEY"),
                "response": token
            }
        )
        return response.json().get("success", False)


# ── Endpoints ────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    datos: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Recibe email y contraseña, verifica credenciales
    y retorna un token JWT si son correctas.
    Máximo 5 intentos por minuto por IP.
    """
    # 1. Validar reCAPTCHA
    if not await validar_recaptcha(datos.recaptcha_token):
        raise HTTPException(status_code=400, detail="reCAPTCHA inválido")

    # 2. Buscar usuario por email
    user = db.query(User).filter(
        User.email == datos.email,
        User.activo == True
    ).first()

    # 3. Verificar contraseña
    # Nota: el mensaje es genérico para no revelar si el email existe
    if not user or not verify_password(datos.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    # 4. Crear y retornar el JWT
    token = create_access_token({
        "sub": str(user.id),
        "role": user.role.value
    })

    return LoginResponse(
        access_token=token,
        role=user.role.value,
        nombre=user.nombre
    )


@router.post("/register", status_code=201)
def register(
    datos: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo usuario en el sistema.
    Verifica que el email no esté duplicado.
    Hashea la contraseña antes de guardarla.
    """
    # Verificar que el email no existe
    if db.query(User).filter(User.email == datos.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    # Crear el usuario con la contraseña hasheada
    nuevo_usuario = User(
        nombre=datos.nombre,
        email=datos.email,
        password_hash=get_password_hash(datos.password),
        role=datos.role,
        empresa_id=datos.empresa_id
    )
    db.add(nuevo_usuario)
    db.commit()
    return {"mensaje": "Usuario creado exitosamente"}


@router.post("/forgot-password")
def forgot_password(
    datos: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Genera un token de recuperación y lo guarda en la BD.
    En producción enviaría el correo con el enlace de reset.
    """
    user = db.query(User).filter(User.email == datos.email).first()

    # Siempre retornar el mismo mensaje para no revelar
    # si el email existe o no en el sistema
    if not user:
        return {"mensaje": "Si el correo existe recibirás un enlace de recuperación"}

    # Generar token aleatorio seguro
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expira = datetime.utcnow() + timedelta(minutes=30)
    db.commit()

    # TODO Sprint 2: enviar correo con SendGrid
    # Por ahora retornamos el token directo para pruebas
    return {
        "mensaje": "Token de recuperación generado",
        "token": token  # quitar esto en producción
    }


@router.post("/reset-password")
def reset_password(
    datos: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Recibe el token de recuperación y la nueva contraseña.
    Valida que el token no haya expirado y actualiza el hash.
    """
    user = db.query(User).filter(
        User.reset_token == datos.token
    ).first()

    if not user:
        raise HTTPException(status_code=400, detail="Token inválido")

    if user.reset_token_expira < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token expirado")

    # Actualizar la contraseña
    user.password_hash = get_password_hash(datos.new_password)
    user.reset_token = None
    user.reset_token_expira = None
    db.commit()

    return {"mensaje": "Contraseña actualizada exitosamente"}