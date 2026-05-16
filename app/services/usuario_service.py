# app/services/usuario_service.py
import secrets
import string
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.user import User, RoleEnum
from app.schemas.usuario_schema import UsuarioCreate, UsuarioUpdate
from app.core.security import get_password_hash
from app.services.email_service import enviar_correo_bienvenida


def generar_password_temporal(longitud: int = 10) -> str:
    caracteres = string.ascii_letters + string.digits
    return ''.join(secrets.choice(caracteres) for _ in range(longitud))


def get_all_users(db: Session, empresa_id: UUID):
    return db.query(User).filter(User.empresa_id == empresa_id).all()


def get_user_by_id(db: Session, usuario_id: UUID, empresa_id: UUID):
    user = db.query(User).filter(
        User.id == usuario_id,
        User.empresa_id == empresa_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


def create_user(db: Session, datos: UsuarioCreate, empresa_id: UUID) -> User:
    if db.query(User).filter(User.email == datos.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    password_temporal = generar_password_temporal()

    nuevo_usuario = User(
        nombre=datos.nombre,
        email=datos.email,
        password_hash=get_password_hash(password_temporal),
        role=RoleEnum(datos.role),
        empresa_id=empresa_id,
        area_id=datos.area_id,
        cargo_id=datos.cargo_id,
        activo=True
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    enviar_correo_bienvenida(
        email_destino=nuevo_usuario.email,
        nombre=nuevo_usuario.nombre,
        password_temporal=password_temporal
    )

    return nuevo_usuario


def update_user(db: Session, usuario_id: UUID, datos: UsuarioUpdate, empresa_id: UUID) -> User:
    user = get_user_by_id(db, usuario_id, empresa_id)

    if datos.nombre is not None:
        user.nombre = datos.nombre
    if datos.area_id is not None:
        user.area_id = datos.area_id
    if datos.cargo_id is not None:
        user.cargo_id = datos.cargo_id
    if datos.activo is not None:
        user.activo = datos.activo

    db.commit()
    db.refresh(user)
    return user