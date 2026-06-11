# app/core/deps.py
# Este archivo protege los endpoints verificando el token JWT
# y el rol del usuario antes de ejecutar cualquier función

from typing import Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

_optional_bearer = HTTPBearer(auto_error=False)

# HTTPBearer: extrae el token del header Authorization: Bearer <token>
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Extrae el token JWT del header de la petición,
    lo valida y retorna el usuario correspondiente.

    Se usa así en cualquier endpoint protegido:
    def mi_endpoint(current_user: User = Depends(get_current_user))

    Si el token es inválido o expiró → retorna error 401
    Si el usuario no existe → retorna error 401
    """
    token = credentials.credentials
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        session_id = payload.get("sid")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    user = db.query(User).filter(User.id == UUID(user_id), User.activo == True).first()

    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    if user.debe_cambiar_password:
        raise HTTPException(status_code=403, detail="debe_cambiar_password")

    # Verificar sesión única: si el token no coincide con la sesión activa en BD
    if session_id is not None and str(user.session_token) != session_id:
        raise HTTPException(
            status_code=401,
            detail="Sesión expirada. Iniciaste sesión desde otro dispositivo.",
        )

    return user


def require_role(*roles: str):
    """
    Verifica que el usuario autenticado tenga uno de los roles permitidos.

    Se usa así en endpoints que requieren un rol específico:
    def mi_endpoint(current_user: User = Depends(require_role("sst")))

    Si el rol no coincide → retorna error 403 Forbidden
    """

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.value not in roles:
            raise HTTPException(
                status_code=403, detail=f"Acceso denegado. Roles permitidos: {roles}"
            )
        return current_user

    return role_checker


def require_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """
    Valida el header X-API-Key contra la tabla api_keys.
    Uso: def mi_endpoint(_=Depends(require_api_key))
    """
    from app.services.api_key_service import validar_clave

    return validar_clave(db, x_api_key)


def require_admin_or_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_optional_bearer),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """
    Acepta autenticación via Bearer JWT (role=admin) O via X-API-Key.
    Usado en endpoints que el cron job llama con API key pero el admin
    también puede invocar con su token JWT.
    """
    if x_api_key:
        from app.services.api_key_service import validar_clave

        return validar_clave(db, x_api_key)

    if credentials:
        try:
            payload = decode_token(credentials.credentials)
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(status_code=401, detail="Token inválido")
        except JWTError:
            raise HTTPException(status_code=401, detail="Token inválido o expirado")

        user = (
            db.query(User).filter(User.id == UUID(user_id), User.activo == True).first()
        )
        if not user:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
        if user.role.value != "admin":
            raise HTTPException(status_code=403, detail="Rol admin requerido")
        return user

    raise HTTPException(
        status_code=401, detail="Se requiere X-API-Key o token Bearer admin"
    )
