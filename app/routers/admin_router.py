# app/routers/admin_router.py
import logging
import secrets
import string
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.core.security import get_password_hash
from app.models.empresa import Empresa
from app.models.user import RoleEnum, User
from app.services.email_service import (
    enviar_correo_bienvenida,
    enviar_correo_reset_admin,
)

logger = logging.getLogger(__name__)


def _mask_email(email: str) -> str:
    parts = email.split("@")
    if len(parts) != 2:
        return "****"
    user, domain = parts
    return f"{user[0]}{'*' * (len(user) - 1)}@{domain}"


router = APIRouter(prefix="/admin", tags=["Administración"])


# ── Schemas ───────────────────────────────────────────────────────
class EmpresaCreate(BaseModel):
    nombre: str
    nit: str
    sector: Optional[str] = None


class SSTCreate(BaseModel):
    nombre: str
    email: EmailStr
    empresa_id: UUID


class EmpresaResponse(BaseModel):
    mensaje: str
    empresa_id: str
    nombre: str
    nit: str


class EmpresaListItem(BaseModel):
    id: str
    nombre: str
    nit: str
    sector: Optional[str]
    activo: bool


class UsuarioAdminResponse(BaseModel):
    mensaje: str
    usuario_id: str
    nombre: str
    email: str
    empresa: str


# ── Endpoints ─────────────────────────────────────────────────────


@router.post("/empresas", response_model=EmpresaResponse, status_code=201)
def crear_empresa(
    datos: EmpresaCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """
    Crea una nueva empresa en el sistema.
    Requiere header: X-Admin-Key con la clave secreta.
    """
    if db.query(Empresa).filter(Empresa.nit == datos.nit).first():
        raise HTTPException(status_code=400, detail="Ya existe una empresa con ese NIT")

    empresa = Empresa(nombre=datos.nombre, nit=datos.nit, sector=datos.sector)
    db.add(empresa)
    db.commit()
    db.refresh(empresa)

    return {
        "mensaje": "Empresa creada exitosamente",
        "empresa_id": str(empresa.id),
        "nombre": empresa.nombre,
        "nit": empresa.nit,
    }


@router.get("/empresas", response_model=List[EmpresaListItem])
def listar_empresas(
    db: Session = Depends(get_db), _: User = Depends(require_role("admin"))
):
    """
    Lista todas las empresas registradas en el sistema.
    Requiere header: X-Admin-Key con la clave secreta.
    """
    empresas = db.query(Empresa).all()
    return [
        {
            "id": str(e.id),
            "nombre": e.nombre,
            "nit": e.nit,
            "sector": e.sector,
            "activo": e.activo,
        }
        for e in empresas
    ]


@router.post("/crear-sst", response_model=UsuarioAdminResponse, status_code=201)
def crear_usuario_sst(
    datos: SSTCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """
    Crea el primer usuario SST de una empresa.
    Requiere header: X-Admin-Key con la clave secreta.
    Envía correo de bienvenida con contraseña temporal.
    """
    if db.query(User).filter(User.email == datos.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    empresa = db.query(Empresa).filter(Empresa.id == datos.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    if (
        db.query(User)
        .filter(
            User.empresa_id == datos.empresa_id,
            User.role == RoleEnum.sst,
            User.activo == True,
        )
        .first()
    ):
        raise HTTPException(
            status_code=400, detail="Esta empresa ya tiene un usuario SST activo"
        )

    # Generar contraseña temporal
    caracteres = string.ascii_letters + string.digits
    password_temporal = "".join(secrets.choice(caracteres) for _ in range(10))

    nuevo_sst = User(
        nombre=datos.nombre,
        email=datos.email,
        password_hash=get_password_hash(password_temporal),
        role=RoleEnum.sst,
        empresa_id=datos.empresa_id,
        activo=True,
        debe_cambiar_password=True,
    )
    db.add(nuevo_sst)
    db.commit()
    db.refresh(nuevo_sst)

    # Enviar correo de bienvenida
    enviado = enviar_correo_bienvenida(
        email_destino=nuevo_sst.email,
        nombre=nuevo_sst.nombre,
        password_temporal=password_temporal,
    )
    if not enviado:
        logger.warning(f"Correo no enviado a {_mask_email(nuevo_sst.email)}")

    return {
        "mensaje": "Usuario SST creado exitosamente",
        "usuario_id": str(nuevo_sst.id),
        "nombre": nuevo_sst.nombre,
        "email": nuevo_sst.email,
        "empresa": empresa.nombre,
    }


@router.post("/crear-gerencia", response_model=UsuarioAdminResponse, status_code=201)
def crear_usuario_gerencia(
    datos: SSTCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """
    Crea un usuario de Gerencia para una empresa.
    Requiere header: X-Admin-Key con la clave secreta.
    """
    if db.query(User).filter(User.email == datos.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    empresa = db.query(Empresa).filter(Empresa.id == datos.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    if (
        db.query(User)
        .filter(
            User.empresa_id == datos.empresa_id,
            User.role == RoleEnum.gerencia,
            User.activo == True,
        )
        .first()
    ):
        raise HTTPException(
            status_code=400, detail="Esta empresa ya tiene un usuario Gerencia activo"
        )

    caracteres = string.ascii_letters + string.digits
    password_temporal = "".join(secrets.choice(caracteres) for _ in range(10))

    nuevo_gerencia = User(
        nombre=datos.nombre,
        email=datos.email,
        password_hash=get_password_hash(password_temporal),
        role=RoleEnum.gerencia,
        empresa_id=datos.empresa_id,
        activo=True,
        debe_cambiar_password=True,
    )
    db.add(nuevo_gerencia)
    db.commit()
    db.refresh(nuevo_gerencia)

    enviado = enviar_correo_bienvenida(
        email_destino=nuevo_gerencia.email,
        nombre=nuevo_gerencia.nombre,
        password_temporal=password_temporal,
    )
    if not enviado:
        logger.warning(f"Correo no enviado a {_mask_email(nuevo_gerencia.email)}")

    return {
        "mensaje": "Usuario Gerencia creado exitosamente",
        "usuario_id": str(nuevo_gerencia.id),
        "nombre": nuevo_gerencia.nombre,
        "email": nuevo_gerencia.email,
        "empresa": empresa.nombre,
    }


@router.post("/usuarios/{usuario_id}/reset-password")
def reset_password_usuario(
    usuario_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """
    Genera un token de reset y envía el enlace por email al usuario.
    No envía contraseña — el usuario establece la suya al hacer clic.
    """
    from app.services.auth_service import crear_reset_token

    user = db.query(User).filter(User.id == usuario_id, User.activo == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    token = crear_reset_token(user.id, db)

    enviado = enviar_correo_reset_admin(
        email_destino=user.email,
        nombre=user.nombre,
        token=token,
    )
    if not enviado:
        logger.warning(f"Correo reset no enviado a {_mask_email(user.email)}")

    return {"mensaje": "Enlace de reset enviado", "usuario_id": str(user.id)}


@router.post("/limpiar-tokens")
def limpiar_tokens_caducados(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """
    Limpia refresh tokens y session tokens caducados de todos los usuarios.
    Requiere header: X-Admin-Key con la clave secreta.
    """
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)

    usuarios = (
        db.query(User)
        .filter(
            User.refresh_token_expira.isnot(None), User.refresh_token_expira < ahora
        )
        .all()
    )

    total = len(usuarios)
    for user in usuarios:
        user.refresh_token = None
        user.refresh_token_expira = None
        user.session_token = None

    db.commit()

    return {
        "mensaje": f"Limpieza completada. {total} usuario(s) con tokens caducados fueron procesados."
    }
