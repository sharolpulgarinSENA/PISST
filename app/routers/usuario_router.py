# app/routers/usuario_router.py
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.usuario_schema import (
    PerfilUpdate,
    UsuarioCreate,
    UsuarioResponse,
    UsuarioUpdate,
)
from app.services.cloudinary_service import (
    LIMITE_BYTES,
    MIME_PERMITIDOS,
    subir_foto_perfil,
)
from app.services.usuario_service import (
    create_user,
    get_all_users,
    get_user_by_id,
    update_user,
)

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

RETENCION_DIAS = 30


# ── Endpoints SST ─────────────────────────────────────────────────


@router.get("/", response_model=List[UsuarioResponse])
def listar_usuarios(
    skip: int = 0,
    limit: int = 50,
    activo: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    return get_all_users(db, current_user.empresa_id, skip, limit, activo)


@router.get("/{usuario_id}", response_model=UsuarioResponse)
def obtener_usuario(
    usuario_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    return get_user_by_id(db, usuario_id, current_user.empresa_id)


@router.post("/", response_model=UsuarioResponse, status_code=201)
def crear_usuario(
    datos: UsuarioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    return create_user(db, datos, current_user.empresa_id)


@router.patch("/{usuario_id}", response_model=UsuarioResponse)
def actualizar_usuario(
    usuario_id: UUID,
    datos: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    return update_user(db, usuario_id, datos, current_user.empresa_id)


# ── Endpoints perfil propio ────────────────────────────────────────


@router.patch("/me", response_model=UsuarioResponse)
def actualizar_mi_perfil(
    datos: PerfilUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualiza nombre y/o teléfono del usuario autenticado."""
    if datos.nombre is not None:
        current_user.nombre = datos.nombre
    if datos.telefono is not None:
        current_user.telefono = datos.telefono
    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/me/foto")
async def actualizar_foto_perfil(
    foto: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sube o reemplaza la foto de perfil del usuario autenticado."""
    if foto.content_type not in MIME_PERMITIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no permitido: {foto.content_type}. Usa JPG, PNG o WEBP.",
        )
    contenido = await foto.read()
    if len(contenido) > LIMITE_BYTES:
        raise HTTPException(
            status_code=413, detail="La imagen supera el límite de 2 MB"
        )

    try:
        url = subir_foto_perfil(contenido, str(current_user.id))
    except Exception:
        raise HTTPException(status_code=500, detail="Error al subir la imagen")

    current_user.foto_url = url
    db.commit()
    return {"foto_url": url}


@router.get("/me/actividad")
def mi_actividad(
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna el historial de acciones del usuario autenticado (últimos 30 días)."""
    limite_fecha = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        days=RETENCION_DIAS
    )

    # Purgar registros viejos del usuario
    db.query(AuditLog).filter(
        AuditLog.user_id == current_user.id,
        AuditLog.timestamp < limite_fecha,
    ).delete()
    db.commit()

    total = db.query(AuditLog).filter(AuditLog.user_id == current_user.id).count()
    registros = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == current_user.id)
        .order_by(AuditLog.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "registros": [
            {
                "id": str(r.id),
                "accion": r.accion,
                "modulo": r.entidad,
                "detalle": r.detalle,
                "fecha": r.timestamp,
            }
            for r in registros
        ],
    }
