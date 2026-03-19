from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ...core.database import get_db
from ...models.database_models import Juez
from ...schemas.sentencia_schemas import JuezCreate, JuezResponse

router = APIRouter(prefix="/jueces", tags=["Jueces"])


@router.get("/", response_model=List[JuezResponse])
def list_jueces(
    activo: bool = None,
    db: Session = Depends(get_db)
):
    """Listar todos los jueces"""
    query = db.query(Juez)

    if activo is not None:
        query = query.filter(Juez.activo == activo)

    jueces = query.order_by(Juez.apellido, Juez.nombre).all()
    return jueces


@router.post("/", response_model=JuezResponse, status_code=status.HTTP_201_CREATED)
def create_juez(juez_data: JuezCreate, db: Session = Depends(get_db)):
    """Crear un nuevo juez"""
    nuevo_juez = Juez(**juez_data.model_dump())
    db.add(nuevo_juez)
    db.commit()
    db.refresh(nuevo_juez)
    return nuevo_juez


@router.put("/{juez_id}", response_model=JuezResponse)
def update_juez(
    juez_id: int,
    juez_data: JuezCreate,
    db: Session = Depends(get_db)
):
    """Actualizar un juez"""
    juez = db.query(Juez).filter(Juez.id == juez_id).first()

    if not juez:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Juez no encontrado"
        )

    for field, value in juez_data.model_dump().items():
        setattr(juez, field, value)

    db.commit()
    db.refresh(juez)
    return juez


@router.delete("/{juez_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_juez(juez_id: int, db: Session = Depends(get_db)):
    """Eliminar un juez (soft delete - marcar como inactivo)"""
    juez = db.query(Juez).filter(Juez.id == juez_id).first()

    if not juez:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Juez no encontrado"
        )

    # Soft delete
    from datetime import datetime
    juez.activo = False
    juez.fecha_baja = datetime.now()

    db.commit()
    return None
