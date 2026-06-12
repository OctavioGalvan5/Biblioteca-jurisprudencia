from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
import json

from ...core.database import get_db
from ...core.auth import get_current_user
from ...models.database_models import Sentencia, SentenciaVector, SentenciaJuez
from ...services.embedding_service import embedding_service
from openai import OpenAI
from ...core.config import settings

router = APIRouter(prefix="/chat", tags=["Chat"])
_openai = OpenAI(api_key=settings.OPENAI_API_KEY)


class BuscarRequest(BaseModel):
    query: str
    jurisdiccion: Optional[str] = None
    fecha_desde: Optional[str] = None
    fecha_hasta: Optional[str] = None
    limit: int = 8


class PreguntarRequest(BaseModel):
    pregunta: str
    jurisdiccion: Optional[str] = None
    fecha_desde: Optional[str] = None
    fecha_hasta: Optional[str] = None


def _sentencia_to_dict(s: Sentencia, similitud: float) -> dict:
    return {
        "id": s.id,
        "caratula": s.caratula,
        "nro_expediente": s.nro_expediente,
        "fecha_sentencia": str(s.fecha_sentencia) if s.fecha_sentencia else None,
        "instancia": s.instancia,
        "organo": s.organo,
        "jurisdiccion": s.jurisdiccion,
        "palabras_clave": s.palabras_clave,
        "resumen": s.resumen,
        "similitud": round(similitud, 3),
        "jueces": [
            {"id": sj.juez.id, "nombre": sj.juez.nombre, "apellido": sj.juez.apellido}
            for sj in s.jueces
        ],
    }


def _buscar_similares(query: str, db: Session, jurisdiccion=None, fecha_desde=None, fecha_hasta=None, limit=8):
    try:
        vector = embedding_service.embed(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar embedding: {e}")

    vector_str = "[" + ",".join(str(v) for v in vector) + "]"

    filters = ["sv.embedding IS NOT NULL"]
    params: dict = {"vector": vector_str, "limit": limit}

    if jurisdiccion:
        filters.append("s.jurisdiccion = :jurisdiccion")
        params["jurisdiccion"] = jurisdiccion
    if fecha_desde:
        filters.append("s.fecha_sentencia >= :fecha_desde")
        params["fecha_desde"] = fecha_desde
    if fecha_hasta:
        filters.append("s.fecha_sentencia <= :fecha_hasta")
        params["fecha_hasta"] = fecha_hasta

    where = " AND ".join(filters)

    sql = text(f"""
        SELECT s.id, 1 - (sv.embedding <=> :vector::vector) AS similitud
        FROM sentencias_vectors sv
        JOIN sentencias s ON s.id = sv.sentencia_id
        WHERE {where}
        ORDER BY sv.embedding <=> :vector::vector
        LIMIT :limit
    """)

    rows = db.execute(sql, params).fetchall()
    if not rows:
        return []

    ids = [r[0] for r in rows]
    sim_map = {r[0]: r[1] for r in rows}

    sentencias = (
        db.query(Sentencia)
        .options(joinedload(Sentencia.jueces).joinedload(SentenciaJuez.juez))
        .filter(Sentencia.id.in_(ids))
        .all()
    )
    sentencias.sort(key=lambda s: ids.index(s.id))
    return [_sentencia_to_dict(s, sim_map[s.id]) for s in sentencias]


@router.post("/buscar")
def buscar(req: BuscarRequest, db: Session = Depends(get_db)):
    """Búsqueda semántica de sentencias por tema o concepto. Pública."""
    resultados = _buscar_similares(
        req.query, db,
        jurisdiccion=req.jurisdiccion,
        fecha_desde=req.fecha_desde,
        fecha_hasta=req.fecha_hasta,
        limit=min(req.limit, 20),
    )
    return {"resultados": resultados}


@router.post("/preguntar")
def preguntar(req: PreguntarRequest, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    """
    Responde una pregunta usando las sentencias más relevantes como contexto (RAG).
    Requiere autenticación para evitar abuso (consume tokens de GPT).
    """
    fuentes = _buscar_similares(
        req.pregunta, db,
        jurisdiccion=req.jurisdiccion,
        fecha_desde=req.fecha_desde,
        fecha_hasta=req.fecha_hasta,
        limit=5,
    )
    if not fuentes:
        return {
            "respuesta": "No encontré sentencias relevantes para responder tu pregunta.",
            "fuentes": [],
        }

    # Armar contexto para GPT: caratula + organo + fecha + resumen + primeros 3000 chars del contenido
    contexto_parts = []
    ids_fuentes = [f["id"] for f in fuentes]
    sentencias_completas = db.query(Sentencia).filter(Sentencia.id.in_(ids_fuentes)).all()
    contenidos = {s.id: s.contenido for s in sentencias_completas}

    for f in fuentes:
        sid = f["id"]
        contenido_truncado = (contenidos.get(sid) or "")[:3000]
        parte = (
            f"--- Sentencia: {f['caratula'] or 'Sin carátula'} ---\n"
            f"Órgano: {f['organo'] or '-'} | Fecha: {f['fecha_sentencia'] or '-'} | Jurisdicción: {f['jurisdiccion'] or '-'}\n"
            f"Resumen: {f['resumen'] or '-'}\n"
            f"Extracto: {contenido_truncado}\n"
        )
        contexto_parts.append(parte)

    contexto = "\n".join(contexto_parts)

    prompt = f"""Eres un asistente jurídico especializado en jurisprudencia argentina.
Responde la siguiente pregunta basándote ÚNICAMENTE en las sentencias provistas.
Si la información no está en las sentencias, indicalo claramente.
Citá las sentencias relevantes por su carátula cuando las uses.

PREGUNTA: {req.pregunta}

SENTENCIAS:
{contexto}

RESPUESTA:"""

    try:
        completion = _openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un asistente jurídico experto en derecho argentino. Respondes de forma clara y precisa citando las fuentes."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1500,
        )
        respuesta = completion.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar respuesta: {e}")

    return {"respuesta": respuesta, "fuentes": fuentes}
