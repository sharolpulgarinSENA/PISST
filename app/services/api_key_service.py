# app/services/api_key_service.py
import secrets
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.api_key import ApiKey


def generar_clave() -> str:
    return "sk_" + secrets.token_hex(30)


def crear_api_key(
    db: Session,
    descripcion: str = None,
    rol: str = "cron",
    empresa_id: UUID = None,
) -> ApiKey:
    api_key = ApiKey(
        clave=generar_clave(),
        descripcion=descripcion,
        rol=rol,
        empresa_id=empresa_id,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key


def validar_clave(db: Session, clave: str) -> ApiKey:
    api_key = (
        db.query(ApiKey).filter(ApiKey.clave == clave, ApiKey.activo == True).first()
    )
    if not api_key:
        raise HTTPException(status_code=401, detail="API key inválida o inactiva")
    return api_key


def revocar_api_key(db: Session, key_id: UUID) -> ApiKey:
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key no encontrada")
    api_key.activo = False
    db.commit()
    db.refresh(api_key)
    return api_key
