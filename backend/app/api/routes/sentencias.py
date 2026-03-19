from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import List, Optional

from ...core.database import get_db
from ...models.database_models import Sentencia, Juez, SentenciaJuez
from ...schemas.sentencia_schemas import (
    SentenciaResponse,
    SentenciaUpdate,
    SentenciaListResponse
)

router = APIRouter(prefix="/sentencias", tags=["Sentencias"])


def _map_sentencia(sentencia) -> dict:
    """Helper para mapear sentencia a dict con jueces"""
    return {
        "id": sentencia.id,
        "hash": sentencia.hash,
        "url_minio": sentencia.url_minio,
        "caratula": sentencia.caratula,
        "nro_expediente": sentencia.nro_expediente,
        "fecha_sentencia": sentencia.fecha_sentencia,
        "instancia": sentencia.instancia,
        "organo": sentencia.organo,
        "jurisdiccion": sentencia.jurisdiccion,
        "palabras_clave": sentencia.palabras_clave,
        "contenido": sentencia.contenido,
        "resumen": sentencia.resumen,
        "created_at": sentencia.created_at,
        "updated_at": sentencia.updated_at,
        "jueces": [
            {
                "id": sj.juez.id,
                "nombre": sj.juez.nombre,
                "apellido": sj.juez.apellido,
                "activo": sj.juez.activo,
                "fecha_alta": sj.juez.fecha_alta,
                "fecha_baja": sj.juez.fecha_baja,
            }
            for sj in sentencia.jueces
        ]
    }


@router.get("/", response_model=SentenciaListResponse)
def list_sentencias(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    q: Optional[str] = None,
    jurisdiccion: Optional[str] = None,
    organo: Optional[str] = None,
    juez_id: Optional[int] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Listar sentencias con filtros y búsqueda de texto"""
    query = db.query(Sentencia).options(
        joinedload(Sentencia.jueces).joinedload(SentenciaJuez.juez)
    )

    # Búsqueda de texto libre (carátula, expediente, resumen, órgano, palabras clave)
    if q:
        from sqlalchemy import cast, Text, func as sqlfunc
        query = query.filter(
            or_(
                Sentencia.caratula.ilike(f"%{q}%"),
                Sentencia.nro_expediente.ilike(f"%{q}%"),
                Sentencia.resumen.ilike(f"%{q}%"),
                Sentencia.organo.ilike(f"%{q}%"),
                sqlfunc.array_to_string(Sentencia.palabras_clave, ' ').ilike(f"%{q}%"),
            )
        )

    if jurisdiccion:
        query = query.filter(Sentencia.jurisdiccion == jurisdiccion)

    if organo:
        query = query.filter(Sentencia.organo.ilike(f"%{organo}%"))

    if juez_id:
        query = query.join(Sentencia.jueces).filter(SentenciaJuez.juez_id == juez_id)

    if fecha_desde:
        query = query.filter(Sentencia.fecha_sentencia >= fecha_desde)

    if fecha_hasta:
        query = query.filter(Sentencia.fecha_sentencia <= fecha_hasta)

    total = query.count()
    sentencias = query.order_by(Sentencia.fecha_sentencia.desc().nullslast(), Sentencia.created_at.desc()).offset(skip).limit(limit).all()

    return SentenciaListResponse(total=total, sentencias=[_map_sentencia(s) for s in sentencias])


@router.get("/{sentencia_id}", response_model=SentenciaResponse)
def get_sentencia(sentencia_id: int, db: Session = Depends(get_db)):
    """Obtener una sentencia por ID"""
    sentencia = (
        db.query(Sentencia)
        .options(joinedload(Sentencia.jueces).joinedload(SentenciaJuez.juez))
        .filter(Sentencia.id == sentencia_id)
        .first()
    )

    if not sentencia:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sentencia no encontrada")

    return _map_sentencia(sentencia)


@router.put("/{sentencia_id}", response_model=SentenciaResponse)
def update_sentencia(
    sentencia_id: int,
    sentencia_data: SentenciaUpdate,
    db: Session = Depends(get_db)
):
    """Actualizar una sentencia (no se puede modificar hash ni url_minio)"""
    sentencia = db.query(Sentencia).filter(Sentencia.id == sentencia_id).first()

    if not sentencia:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sentencia no encontrada")

    update_data = sentencia_data.model_dump(exclude_unset=True, exclude={"jueces_ids"})
    for field, value in update_data.items():
        setattr(sentencia, field, value)

    if sentencia_data.jueces_ids is not None:
        db.query(SentenciaJuez).filter(SentenciaJuez.sentencia_id == sentencia_id).delete()
        for juez_id in sentencia_data.jueces_ids:
            juez = db.query(Juez).filter(Juez.id == juez_id).first()
            if juez:
                db.add(SentenciaJuez(sentencia_id=sentencia_id, juez_id=juez_id))

    db.commit()
    db.refresh(sentencia)

    sentencia = (
        db.query(Sentencia)
        .options(joinedload(Sentencia.jueces).joinedload(SentenciaJuez.juez))
        .filter(Sentencia.id == sentencia_id)
        .first()
    )
    return _map_sentencia(sentencia)


@router.delete("/{sentencia_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sentencia(sentencia_id: int, db: Session = Depends(get_db)):
    """Eliminar una sentencia"""
    sentencia = db.query(Sentencia).filter(Sentencia.id == sentencia_id).first()

    if not sentencia:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sentencia no encontrada")

    try:
        from ...core.minio_client import minio_client
        object_name = sentencia.url_minio.split(f"/{minio_client.bucket_name}/")[-1]
        minio_client.delete_file(object_name)
    except Exception as e:
        print(f"Error al eliminar archivo de MinIO: {e}")

    db.delete(sentencia)
    db.commit()
    return None
