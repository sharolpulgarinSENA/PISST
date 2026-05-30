# app/routers/auth_router.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer

_bearer = HTTPBearer()
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel, EmailStr
from typing import Optional
import httpx, os, secrets, logging

logger = logging.getLogger(__name__)
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token, decode_token, validar_fortaleza_password
from jose import JWTError
from app.core.deps import require_role, get_current_user
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
    refresh_token: str
    token_type: str = "bearer"
    role: str
    nombre: str

class RegisterRequest(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    role: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class CambiarPasswordRequest(BaseModel):
    password_actual: str
    nueva_password: str


# ── Funciones auxiliares ─────────────────────────────────────────

def manejar_intento_fallido(user, db: Session) -> None:
    intentos = int(user.intentos_fallidos or 0) + 1
    user.intentos_fallidos = intentos
    if intentos >= MAX_INTENTOS:
        user.bloqueado_hasta = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=BLOQUEO_MINUTOS)
        db.commit()
        raise HTTPException(
            status_code=429,
            detail=f"Cuenta bloqueada por {BLOQUEO_MINUTOS} minutos tras "
                   f"{MAX_INTENTOS} intentos fallidos consecutivos."
        )
    restantes = MAX_INTENTOS - intentos
    db.commit()
    raise HTTPException(
        status_code=401,
        detail=f"Credenciales incorrectas. Te quedan {restantes} intento(s) antes del bloqueo."
    )


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

MAX_INTENTOS = 5
BLOQUEO_MINUTOS = 5


@router.post("/login", response_model=LoginResponse)
@limiter.limit("20/minute")
async def login(
    request: Request,
    datos: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Verifica credenciales y retorna JWT.
    Bloquea la cuenta 5 minutos tras 5 intentos fallidos consecutivos.
    Sesión única: cada login invalida la sesión anterior.
    """
    if not await validar_recaptcha(datos.recaptcha_token):
        raise HTTPException(status_code=400, detail="reCAPTCHA inválido")

    user = db.query(User).filter(
        User.email == datos.email,
        User.activo == True
    ).first()

    # Si el usuario no existe, responder igual que si la contraseña fuera mala
    # (no revelar si el email existe)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    # Verificar si la cuenta está bloqueada
    bloqueado_hasta: Optional[datetime] = user.bloqueado_hasta  # type: ignore[assignment]
    if bloqueado_hasta is not None and bloqueado_hasta > datetime.now(timezone.utc).replace(tzinfo=None):
        minutos_restantes = int(
            (bloqueado_hasta - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds() / 60
        ) + 1
        raise HTTPException(
            status_code=429,
            detail=f"Cuenta bloqueada por demasiados intentos fallidos. "
                   f"Intenta de nuevo en {minutos_restantes} minuto(s)."
        )

    # Verificar contraseña
    if not verify_password(datos.password, str(user.password_hash)):
        manejar_intento_fallido(user, db)

    # Login exitoso — resetear contadores y generar nueva sesión
    user.intentos_fallidos = 0  # type: ignore[assignment]
    user.bloqueado_hasta = None  # type: ignore[assignment]
    nuevo_session_token = secrets.token_hex(32)
    user.session_token = nuevo_session_token  # type: ignore[assignment]

    nuevo_refresh_token = secrets.token_hex(40)
    user.refresh_token = nuevo_refresh_token  # type: ignore[assignment]
    user.refresh_token_expira = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)  # type: ignore[assignment]
    db.commit()

    token = create_access_token({
        "sub": str(user.id),
        "role": user.role.value,
        "sid": nuevo_session_token
    })

    return LoginResponse(
        access_token=token,
        refresh_token=nuevo_refresh_token,
        role=user.role.value,
        nombre=user.nombre
    )


@router.post("/register", status_code=201)
def register(
    datos: RegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    if db.query(User).filter(User.email == datos.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    try:
        role = RoleEnum(datos.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Rol inválido: {datos.role}")

    validar_fortaleza_password(datos.password)

    nuevo_usuario = User(
        nombre=datos.nombre,
        email=datos.email,
        password_hash=get_password_hash(datos.password),
        role=role,
        empresa_id=current_user.empresa_id
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
    user.reset_token_expira = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30)
    db.commit()

    enviado = enviar_correo_reset(
        email_destino=user.email,
        nombre=user.nombre,
        token=token
    )

    # ✅ Fix Bug #4 — Siempre retornar mensaje genérico aunque falle el correo
    if not enviado:
        logger.warning(f"Error enviando correo a {user.email} — token generado pero no enviado")

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

    if not user.reset_token_expira or user.reset_token_expira < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(status_code=400, detail="Token expirado")

    validar_fortaleza_password(datos.new_password)
    user.password_hash = get_password_hash(datos.new_password)
    user.reset_token = None
    user.reset_token_expira = None
    db.commit()

    return {"mensaje": "Contraseña actualizada exitosamente"}


@router.post("/cambiar-password")
def cambiar_password(
    datos: CambiarPasswordRequest,
    db: Session = Depends(get_db),
    credentials = Depends(_bearer)
):
    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    user = db.query(User).filter(User.id == user_id, User.activo == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    if not verify_password(datos.password_actual, user.password_hash):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")

    validar_fortaleza_password(datos.nueva_password)
    user.password_hash = get_password_hash(datos.nueva_password)
    user.debe_cambiar_password = False
    db.commit()

    return {"mensaje": "Contraseña cambiada exitosamente"}


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
def refresh_token(datos: RefreshRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.refresh_token == datos.refresh_token,
        User.activo == True
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Refresh token inválido")

    if not user.refresh_token_expira or user.refresh_token_expira < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(status_code=401, detail="Refresh token expirado")

    nuevo_access_token = create_access_token({
        "sub": str(user.id),
        "role": user.role.value,
        "sid": str(user.session_token)
    })

    return {"access_token": nuevo_access_token, "token_type": "bearer"}
