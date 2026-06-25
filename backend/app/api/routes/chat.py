from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional

from ...core.database import get_db
from ...core.auth import get_current_user
from ...models.database_models import Sentencia, SentenciaJuez
from ...services.embedding_service import embedding_service
from openai import OpenAI
from ...core.config import settings

router = APIRouter(prefix="/chat", tags=["Chat"])
_openai = OpenAI(api_key=settings.OPENAI_API_KEY)

MIN_SIMILARITY = 0.28
TEXT_MATCH_SCORE = 0.42  # Score assigned to keyword-only matches (above MIN_SIMILARITY)

# Considerandos rank highest — legal reasoning is most useful for search
TIPO_BOOST = {"considerando": 0.03, "resuelve": 0.01, "vistos": 0.0, "general": 0.0}


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
        "instancia": s.instancia.nombre if s.instancia else None,
        "organo": s.organo.nombre if s.organo else None,
        "jurisdiccion": s.jurisdiccion,
        "palabras_clave": s.palabras_clave,
        "resumen": s.resumen,
        "similitud": round(similitud, 3),
        "jueces": [
            {"id": sj.juez.id, "nombre": sj.juez.nombre, "apellido": sj.juez.apellido}
            for sj in s.jueces
        ],
    }


def _buscar_similares(
    query: str,
    db: Session,
    jurisdiccion=None,
    fecha_desde=None,
    fecha_hasta=None,
    limit=8,
    min_similarity=MIN_SIMILARITY,
):
    try:
        vector = embedding_service.embed(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar embedding: {e}")

    vector_str = "[" + ",".join(str(v) for v in vector) + "]"

    # Shared filters for both search legs
    filters = []
    params_base: dict = {}

    if jurisdiccion:
        filters.append("s.jurisdiccion = :jurisdiccion")
        params_base["jurisdiccion"] = jurisdiccion
    if fecha_desde:
        filters.append("s.fecha_sentencia >= :fecha_desde")
        params_base["fecha_desde"] = fecha_desde
    if fecha_hasta:
        filters.append("s.fecha_sentencia <= :fecha_hasta")
        params_base["fecha_hasta"] = fecha_hasta

    extra_where = (" AND " + " AND ".join(filters)) if filters else ""

    # --- Leg 1: Semantic (vector) search ---
    sem_sql = text(f"""
        SELECT sc.sentencia_id,
               sc.tipo_seccion,
               1 - (sc.embedding <=> CAST(:vector AS vector)) AS similitud
        FROM sentencias_chunks sc
        JOIN sentencias s ON s.id = sc.sentencia_id
        WHERE sc.embedding IS NOT NULL
        {extra_where}
        ORDER BY sc.embedding <=> CAST(:vector AS vector)
        LIMIT :candidate_limit
    """)
    sem_rows = db.execute(
        sem_sql,
        {**params_base, "vector": vector_str, "candidate_limit": limit * 6},
    ).fetchall()

    # Deduplicate: per sentencia keep best boosted score
    best: dict[int, float] = {}
    for sentencia_id, tipo_seccion, sim in sem_rows:
        boosted = sim + TIPO_BOOST.get(tipo_seccion or "general", 0.0)
        if sentencia_id not in best or boosted > best[sentencia_id]:
            best[sentencia_id] = boosted

    # --- Leg 2: Keyword search on chunk text ---
    # Catches exact phrase matches that fall below the vector similarity threshold
    kw_sql = text(f"""
        SELECT DISTINCT sc.sentencia_id
        FROM sentencias_chunks sc
        JOIN sentencias s ON s.id = sc.sentencia_id
        WHERE sc.contenido ILIKE :pattern
        {extra_where}
    """)
    kw_rows = db.execute(kw_sql, {**params_base, "pattern": f"%{query}%"}).fetchall()

    for row in kw_rows:
        if row.sentencia_id not in best:
            best[row.sentencia_id] = TEXT_MATCH_SCORE

    # Apply threshold and sort
    filtered = [
        (sid, score) for sid, score in best.items() if score >= min_similarity
    ]
    filtered.sort(key=lambda x: x[1], reverse=True)
    top = filtered[:limit]

    if not top:
        return []

    ids = [sid for sid, _ in top]
    sim_map = {sid: score for sid, score in top}

    sentencias = (
        db.query(Sentencia)
        .options(
            joinedload(Sentencia.jueces).joinedload(SentenciaJuez.juez),
            joinedload(Sentencia.instancia),
            joinedload(Sentencia.organo)
        )
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
    Requiere autenticación.
    """
    fuentes = _buscar_similares(
        req.pregunta, db,
        jurisdiccion=req.jurisdiccion,
        fecha_desde=req.fecha_desde,
        fecha_hasta=req.fecha_hasta,
        limit=5,
        min_similarity=0.22,  # slightly lower threshold for RAG to have more context
    )
    if not fuentes:
        return {
            "respuesta": "No encontré sentencias relevantes para responder tu pregunta.",
            "fuentes": [],
        }

    ids_fuentes = [f["id"] for f in fuentes]
    sentencias_completas = (
        db.query(Sentencia)
        .options(joinedload(Sentencia.instancia), joinedload(Sentencia.organo))
        .filter(Sentencia.id.in_(ids_fuentes))
        .all()
    )
    contenidos = {s.id: s.contenido for s in sentencias_completas}

    contexto_parts = []
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
