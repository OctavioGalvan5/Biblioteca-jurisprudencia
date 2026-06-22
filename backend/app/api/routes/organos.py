from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from ...core.database import get_db
from ...models.database_models import Organo
from ...schemas.sentencia_schemas import OrganoResponse

router = APIRouter(prefix="/organos", tags=["Órganos"])


@router.get("/", response_model=List[OrganoResponse])
def list_organos(db: Session = Depends(get_db)):
    """Listar todos los órganos disponibles"""
    return db.query(Organo).order_by(Organo.nombre).all()
