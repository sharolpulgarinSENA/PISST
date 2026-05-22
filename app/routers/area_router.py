from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User
from app.models.area import Area
from app.schemas.area_schema import AreaResponse

router = APIRouter(prefix="/areas", tags=["Áreas"])

@router.get("/", response_model=List[AreaResponse])
def listar_areas(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst"))
):
    """
    Devuelve todas las áreas activas de la empresa del SST autenticado.
    El frontend muestra el nombre, pero usa el id al crear el empleado.
    """
    return db.query(Area).filter(
        Area.empresa_id == current_user.empresa_id,
        Area.activo == True
    ).all()