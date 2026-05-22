from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User
from app.models.cargo import Cargo
from app.schemas.cargo_schema import CargoResponse

router = APIRouter(prefix="/cargos", tags=["Cargos"])

@router.get("/", response_model=List[CargoResponse])
def listar_cargos(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst"))
):
    """
    Devuelve todos los cargos activos de la empresa del SST autenticado.
    """
    return db.query(Cargo).filter(
        Cargo.empresa_id == current_user.empresa_id,
        Cargo.activo == True
    ).all()