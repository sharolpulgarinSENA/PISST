# app/services/auth_service.py
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    get_password_hash,
    validar_fortaleza_password,
    verify_password,
)
from app.models.user import RoleEnum, User

logger = logging.getLogger(__name__)

MAX_INTENTOS = 5
BLOQUEO_MINUTOS = 5


def _mask_email(email: str) -> str:
    parts = email.split("@")
    if len(parts) != 2:
        return "****"
    user, domain = parts
    return f"{user[0]}{'*' * (len(user) - 1)}@{domain}"


def manejar_intento_fallido(user: User, db: Session) -> None:
    intentos = int(user.intentos_fallidos or 0) + 1
    user.intentos_fallidos = intentos
    if intentos >= MAX_INTENTOS:
        user.bloqueado_hasta = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) + timedelta(minutes=BLOQUEO_MINUTOS)
        db.commit()
        raise HTTPException(
            status_code=429,
            detail=f"Cuenta bloqueada por {BLOQUEO_MINUTOS} minutos tras "
            f"{MAX_INTENTOS} intentos fallidos consecutivos.",
        )
    restantes = MAX_INTENTOS - intentos
    db.commit()
    raise HTTPException(
        status_code=401,
        detail=f"Credenciales incorrectas. Te quedan {restantes} intento(s) antes del bloqueo.",
    )


async def validar_recaptcha(token: str) -> bool:
    if os.getenv("ENVIRONMENT") == "development":
        return True
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": os.getenv("RECAPTCHA_SECRET_KEY"), "response": token},
        )
        return response.json().get("success", False)


async def login(email: str, password: str, recaptcha_token: str, db: Session) -> dict:
    if not await validar_recaptcha(recaptcha_token):
        raise HTTPException(status_code=400, detail="reCAPTCHA inválido")

    user = db.query(User).filter(User.email == email, User.activo == True).first()

    if not user:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    bloqueado_hasta: Optional[datetime] = user.bloqueado_hasta
    if bloqueado_hasta is not None and bloqueado_hasta > datetime.now(
        timezone.utc
    ).replace(tzinfo=None):
        segundos_restantes = (
            bloqueado_hasta - datetime.now(timezone.utc).replace(tzinfo=None)
        ).total_seconds()
        minutos_restantes = int(segundos_restantes / 60) + 1
        hora_desbloqueo = bloqueado_hasta.strftime("%H:%M")
        raise HTTPException(
            status_code=429,
            detail=f"Cuenta bloqueada. Intenta de nuevo en {minutos_restantes} minuto(s) (a las {hora_desbloqueo}).",
        )

    if not verify_password(password, str(user.password_hash)):
        manejar_intento_fallido(user, db)

    user.intentos_fallidos = 0
    user.bloqueado_hasta = None
    nuevo_session_token = secrets.token_hex(32)
    user.session_token = nuevo_session_token

    nuevo_refresh_token = secrets.token_hex(40)
    user.refresh_token = nuevo_refresh_token
    user.refresh_token_expira = datetime.now(timezone.utc).replace(
        tzinfo=None
    ) + timedelta(days=7)
    db.commit()

    access_token = create_access_token(
        {"sub": str(user.id), "role": user.role.value, "sid": nuevo_session_token}
    )

    return {
        "access_token": access_token,
        "refresh_token": nuevo_refresh_token,
        "id": str(user.id),
        "role": user.role.value,
        "nombre": user.nombre,
        "debe_cambiar_password": user.debe_cambiar_password,
    }


def registrar_usuario(
    nombre: str, email: str, password: str, role: str, empresa_id, db: Session
) -> dict:
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    try:
        role_enum = RoleEnum(role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Rol inválido: {role}")

    validar_fortaleza_password(password)

    nuevo_usuario = User(
        nombre=nombre,
        email=email,
        password_hash=get_password_hash(password),
        role=role_enum,
        empresa_id=empresa_id,
    )
    db.add(nuevo_usuario)
    db.commit()
    return {"mensaje": "Usuario creado exitosamente"}


def solicitar_reset(email: str, db: Session) -> dict:
    from app.services.email_service import enviar_correo_reset

    mensaje_generico = {
        "mensaje": "Si el correo existe recibirás un enlace de recuperación en los próximos minutos"
    }

    user = db.query(User).filter(User.email == email, User.activo == True).first()
    if not user:
        return mensaje_generico

    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expira = datetime.now(timezone.utc).replace(
        tzinfo=None
    ) + timedelta(minutes=30)
    db.commit()

    enviado = enviar_correo_reset(
        email_destino=user.email, nombre=user.nombre, token=token
    )
    if not enviado:
        logger.warning(
            f"Error enviando correo a {_mask_email(user.email)} — token generado pero no enviado"
        )

    return mensaje_generico


def resetear_password(token: str, new_password: str, db: Session) -> dict:
    if not new_password or len(new_password) < 6:
        raise HTTPException(
            status_code=400, detail="La contraseña debe tener al menos 6 caracteres"
        )

    user = db.query(User).filter(User.reset_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Token inválido")

    if not user.reset_token_expira or user.reset_token_expira < datetime.now(
        timezone.utc
    ).replace(tzinfo=None):
        raise HTTPException(status_code=400, detail="Token expirado")

    validar_fortaleza_password(new_password)
    user.password_hash = get_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expira = None
    db.commit()

    return {"mensaje": "Contraseña actualizada exitosamente"}


def cambiar_password(
    user_id: str,
    session_id: Optional[str],
    password_actual: str,
    nueva_password: str,
    db: Session,
) -> dict:
    user = db.query(User).filter(User.id == UUID(user_id), User.activo == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    if session_id is not None and str(user.session_token) != session_id:
        raise HTTPException(
            status_code=401,
            detail="Sesión expirada. Iniciaste sesión desde otro dispositivo.",
        )

    if not verify_password(password_actual, user.password_hash):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")

    validar_fortaleza_password(nueva_password)
    user.password_hash = get_password_hash(nueva_password)
    user.debe_cambiar_password = False
    db.commit()

    return {"mensaje": "Contraseña cambiada exitosamente"}


def refrescar_token(refresh_token: str, db: Session) -> dict:
    from app.models.empresa import Empresa

    user = (
        db.query(User)
        .filter(User.refresh_token == refresh_token, User.activo == True)
        .first()
    )

    if not user:
        raise HTTPException(status_code=401, detail="Refresh token inválido")

    if not user.refresh_token_expira or user.refresh_token_expira < datetime.now(
        timezone.utc
    ).replace(tzinfo=None):
        raise HTTPException(status_code=401, detail="Refresh token expirado")

    if user.empresa_id:
        empresa = db.query(Empresa).filter(Empresa.id == user.empresa_id).first()
        if not empresa or not empresa.activo:
            raise HTTPException(status_code=401, detail="Empresa desactivada")

    nuevo_access_token = create_access_token(
        {"sub": str(user.id), "role": user.role.value, "sid": str(user.session_token)}
    )

    return {"access_token": nuevo_access_token, "token_type": "bearer"}


def crear_reset_token(usuario_id, db: Session) -> str:
    from app.models.reset_token import ResetToken

    token = secrets.token_hex(32)  # 64 caracteres hex
    expira = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=24)
    rt = ResetToken(usuario_id=usuario_id, token=token, expira_en=expira)
    db.add(rt)
    db.commit()
    return token


def verificar_reset_token(token: str, db: Session):
    from app.models.reset_token import ResetToken

    rt = db.query(ResetToken).filter(ResetToken.token == token).first()
    if not rt:
        raise HTTPException(status_code=400, detail="Token inválido")
    if rt.usado:
        raise HTTPException(status_code=400, detail="Token ya utilizado")
    if rt.expira_en < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(status_code=400, detail="Token expirado")
    return rt


def usar_reset_token(token: str, nueva_password: str, db: Session) -> dict:
    rt = verificar_reset_token(token, db)

    validar_fortaleza_password(nueva_password)

    user = db.query(User).filter(User.id == rt.usuario_id, User.activo == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.password_hash = get_password_hash(nueva_password)
    user.debe_cambiar_password = False
    rt.usado = True
    db.commit()
    return {"mensaje": "Contraseña actualizada exitosamente"}


def logout(refresh_token: str, db: Session) -> dict:
    user = (
        db.query(User)
        .filter(User.refresh_token == refresh_token, User.activo == True)
        .first()
    )

    if user:
        user.refresh_token = None
        user.refresh_token_expira = None
        user.session_token = None
        db.commit()

    return {"mensaje": "Sesión cerrada exitosamente"}
