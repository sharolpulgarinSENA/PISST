# app/routers/admin_router.py
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
import os

from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.user import User, RoleEnum
from app.models.empresa import Empresa
from app.services.email_service import enviar_correo_bienvenida
import secrets
import string
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Administración"])


# ── Clave secreta para proteger los endpoints admin ───────────────
def verificar_clave_admin(x_admin_key: str = Header(...)):
    clave_correcta = os.getenv("ADMIN_SECRET_KEY")
    if not clave_correcta or x_admin_key != clave_correcta:
        raise HTTPException(status_code=403, detail="Clave admin incorrecta")


# ── Schemas ───────────────────────────────────────────────────────
class EmpresaCreate(BaseModel):
    nombre: str
    nit: str
    sector: Optional[str] = None


class SSTCreate(BaseModel):
    nombre: str
    email: EmailStr
    empresa_id: UUID


# ── Endpoints ─────────────────────────────────────────────────────


@router.post("/empresas", status_code=201)
def crear_empresa(
    datos: EmpresaCreate,
    db: Session = Depends(get_db),
    _: str = Depends(verificar_clave_admin),
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


@router.get("/empresas")
def listar_empresas(
    db: Session = Depends(get_db), _: str = Depends(verificar_clave_admin)
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


@router.post("/crear-sst", status_code=201)
def crear_usuario_sst(
    datos: SSTCreate,
    db: Session = Depends(get_db),
    _: str = Depends(verificar_clave_admin),
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
        logger.warning(f"Correo no enviado a {nuevo_sst.email}")

    return {
        "mensaje": "Usuario SST creado exitosamente",
        "usuario_id": str(nuevo_sst.id),
        "nombre": nuevo_sst.nombre,
        "email": nuevo_sst.email,
        "empresa": empresa.nombre,
    }


@router.post("/crear-gerencia", status_code=201)
def crear_usuario_gerencia(
    datos: SSTCreate,
    db: Session = Depends(get_db),
    _: str = Depends(verificar_clave_admin),
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

    caracteres = string.ascii_letters + string.digits
    password_temporal = "".join(secrets.choice(caracteres) for _ in range(10))

    nuevo_gerencia = User(
        nombre=datos.nombre,
        email=datos.email,
        password_hash=get_password_hash(password_temporal),
        role=RoleEnum.gerencia,
        empresa_id=datos.empresa_id,
        activo=True,
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
        logger.warning(f"Correo no enviado a {nuevo_gerencia.email}")

    return {
        "mensaje": "Usuario Gerencia creado exitosamente",
        "usuario_id": str(nuevo_gerencia.id),
        "nombre": nuevo_gerencia.nombre,
        "email": nuevo_gerencia.email,
        "empresa": empresa.nombre,
    }
