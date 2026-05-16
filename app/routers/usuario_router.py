# app/routers/usuario_router.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User
from app.schemas.usuario_schema import UsuarioCreate, UsuarioUpdate, UsuarioResponse
from app.services.usuario_service import (
    get_all_users,
    get_user_by_id,
    create_user,
    update_user
)

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.get("/", response_model=List[UsuarioResponse])
def listar_usuarios(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst"))
):
    return get_all_users(db, current_user.empresa_id)


@router.get("/{usuario_id}", response_model=UsuarioResponse)
def obtener_usuario(
    usuario_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst"))
):
    return get_user_by_id(db, usuario_id, current_user.empresa_id)


@router.post("/", response_model=UsuarioResponse, status_code=201)
def crear_usuario(
    datos: UsuarioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst"))
):
    return create_user(db, datos, current_user.empresa_id)


@router.patch("/{usuario_id}", response_model=UsuarioResponse)
def actualizar_usuario(
    usuario_id: UUID,
    datos: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst"))
):
    return update_user(db, usuario_id, datos, current_user.empresa_id)