"""
Genera chunks + embeddings para todas las sentencias que aun no los tienen.

Uso (desde backend/, con el venv activo):
    python rechunk_existing.py

Idempotente: si se interrumpe, al correrlo de nuevo solo procesa las que
quedaron sin chunks.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from sqlalchemy import text
from app.core.database import engine, SessionLocal
from app.models.database_models import Sentencia, SentenciaChunk
from app.services.chunking_service import chunking_service
from app.services.embedding_service import embedding_service


def setup():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text(
            "ALTER TABLE sentencias_chunks ADD COLUMN IF NOT EXISTS embedding vector(1536)"
        ))
        conn.commit()


def rechunk_all():
    setup()
    db = SessionLocal()

    try:
        chunked_ids = {row[0] for row in db.query(SentenciaChunk.sentencia_id).distinct().all()}
        pending = (
            db.query(Sentencia)
            .filter(~Sentencia.id.in_(chunked_ids), Sentencia.contenido.isnot(None))
            .order_by(Sentencia.id)
            .all()
        )

        total = len(pending)
        if total == 0:
            print("Todas las sentencias ya tienen chunks.")
            return

        print(f"{total} sentencia(s) sin chunks. Procesando...\n")

        ok = 0
        for i, s in enumerate(pending, 1):
            label = (s.caratula or f"ID {s.id}")[:80]
            try:
                chunks = chunking_service.chunk_sentencia(s.contenido)
                for idx, chunk in enumerate(chunks):
                    emb = embedding_service.embed(chunk["contenido"])
                    db.add(SentenciaChunk(
                        sentencia_id=s.id,
                        chunk_index=idx,
                        tipo_seccion=chunk["tipo"],
                        contenido=chunk["contenido"],
                        embedding=emb,
                    ))
                db.commit()
                ok += 1
                print(f"  [{i}/{total}] OK ({len(chunks)} chunks) {label}")
            except Exception as e:
                db.rollback()
                print(f"  [{i}/{total}] ERROR {label}\n         {e}")

        print(f"\nListo: {ok}/{total} sentencias procesadas.")

    finally:
        db.close()


if __name__ == "__main__":
    rechunk_all()
