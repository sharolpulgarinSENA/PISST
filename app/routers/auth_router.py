# app/routers/auth_router.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from jose import JWTError
from pydantic import BaseModel, EmailStr
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.core.security import decode_token
from app.models.user import User
from app.services import auth_service

_bearer = HTTPBearer()

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
    debe_cambiar_password: bool


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


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


# ── Endpoints ────────────────────────────────────────────────────


@router.post("/login", response_model=LoginResponse)
@limiter.limit("20/minute")
async def login(request: Request, datos: LoginRequest, db: Session = Depends(get_db)):
    return await auth_service.login(
        datos.email, datos.password, datos.recaptcha_token, db
    )


@router.post("/register", status_code=201)
def register(
    datos: RegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return auth_service.registrar_usuario(
        datos.nombre,
        datos.email,
        datos.password,
        datos.role,
        current_user.empresa_id,
        db,
    )


@router.post("/forgot-password")
def forgot_password(datos: ForgotPasswordRequest, db: Session = Depends(get_db)):
    return auth_service.solicitar_reset(datos.email, db)


@router.post("/reset-password")
def reset_password(datos: ResetPasswordRequest, db: Session = Depends(get_db)):
    return auth_service.resetear_password(datos.token, datos.new_password, db)


@router.post("/cambiar-password")
def cambiar_password(
    datos: CambiarPasswordRequest,
    db: Session = Depends(get_db),
    credentials=Depends(_bearer),
):
    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        session_id = payload.get("sid")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    return auth_service.cambiar_password(
        user_id, session_id, datos.password_actual, datos.nueva_password, db
    )


@router.post("/refresh")
def refresh_token(datos: RefreshRequest, db: Session = Depends(get_db)):
    return auth_service.refrescar_token(datos.refresh_token, db)


@router.post("/logout")
def logout(datos: LogoutRequest, db: Session = Depends(get_db)):
    return auth_service.logout(datos.refresh_token, db)
