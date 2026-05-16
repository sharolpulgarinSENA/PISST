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
from app.core.deps import require_role
from app.models.user import User, RoleEnum

router = APIRouter(prefix="/auth", tags=["Autenticación"])

limiter = Limiter(key_func=get_remote_address)


# ── Schemas ──────────────────────────────────────────────────────

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
    if os.getenv("ENVIRONMENT") == "development":
        return True

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
    Verifica credenciales y retorna JWT.
    Máximo 5 intentos por minuto por IP.
    """
    if not await validar_recaptcha(datos.recaptcha_token):
        raise HTTPException(status_code=400, detail="reCAPTCHA inválido")

    user = db.query(User).filter(
        User.email == datos.email,
        User.activo == True
    ).first()

    if not user or not verify_password(datos.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst"))  # ✅ Fix Bug #2
):
    """
    Crea un nuevo usuario. Solo el Encargado SST puede registrar usuarios.
    """
    if db.query(User).filter(User.email == datos.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    try:
        role = RoleEnum(datos.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Rol inválido: {datos.role}")

    nuevo_usuario = User(
        nombre=datos.nombre,
        email=datos.email,
        password_hash=get_password_hash(datos.password),
        role=role,  # ✅ Fix enum correcto
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
    Genera un token de recuperación y envía el correo via Resend.
    Siempre retorna el mismo mensaje para no revelar si el email existe.
    """
    from app.services.email_service import enviar_correo_reset

    mensaje_generico = {
        "mensaje": "Si el correo existe recibirás un enlace de recuperación en los próximos minutos"
    }

    user = db.query(User).filter(
        User.email == datos.email,
        User.activo == True
    ).first()

    if not user:
        return mensaje_generico

    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expira = datetime.utcnow() + timedelta(minutes=30)
    db.commit()

    enviado = enviar_correo_reset(
        email_destino=user.email,
        nombre=user.nombre,
        token=token
    )

    # ✅ Fix Bug #4 — Siempre retornar mensaje genérico aunque falle el correo
    if not enviado:
        print(f"⚠️ Error enviando correo a {user.email} — token generado pero no enviado")

    return mensaje_generico


@router.post("/reset-password")
def reset_password(
    datos: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Valida el token y actualiza la contraseña.
    El token expira en 30 minutos.
    """
    # ✅ Fix — Validar que la contraseña no esté vacía
    if not datos.new_password or len(datos.new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="La contraseña debe tener al menos 6 caracteres"
        )

    user = db.query(User).filter(
        User.reset_token == datos.token
    ).first()

    if not user:
        raise HTTPException(status_code=400, detail="Token inválido")

    if user.reset_token_expira < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token expirado")

    user.password_hash = get_password_hash(datos.new_password)
    user.reset_token = None
    user.reset_token_expira = None
    db.commit()

    return {"mensaje": "Contraseña actualizada exitosamente"}
