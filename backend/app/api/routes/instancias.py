from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from ...core.database import get_db
from ...models.database_models import Instancia
from ...schemas.sentencia_schemas import InstanciaResponse

router = APIRouter(prefix="/instancias", tags=["Instancias"])


@router.get("/", response_model=List[InstanciaResponse])
def list_instancias(db: Session = Depends(get_db)):
    """Listar todas las instancias disponibles"""
    return db.query(Instancia).order_by(Instancia.nombre).all()
