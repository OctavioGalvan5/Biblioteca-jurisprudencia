"""
Genera chunks + embeddings para todas las sentencias que aun no los tienen.

Uso (desde la carpeta backend/, con el venv activo):
    python embed_existing.py

El script es idempotente: si se interrumpe, al correrlo de nuevo
solo procesa las sentencias que quedaron sin chunks.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'), override=True)

from app.core.database import SessionLocal
from app.models.database_models import Sentencia, SentenciaChunk
from app.services.chunking_service import chunking_service
from app.services.embedding_service import embedding_service


def chunk_all():
    db = SessionLocal()
    try:
        chunked_ids = {row[0] for row in db.query(SentenciaChunk.sentencia_id).distinct().all()}
        pending = (
            db.query(Sentencia)
            .filter(~Sentencia.id.in_(chunked_ids))
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
            db2 = SessionLocal()
            try:
                chunks = chunking_service.chunk_sentencia(s.contenido or "")
                for j, chunk in enumerate(chunks):
                    emb = embedding_service.embed(chunk["contenido"])
                    db2.add(SentenciaChunk(
                        sentencia_id=s.id,
                        chunk_index=j,
                        tipo_seccion=chunk["tipo"],
                        contenido=chunk["contenido"],
                        embedding=emb,
                    ))
                db2.commit()
                ok += 1
                print(f"  [{i}/{total}] OK ({len(chunks)} chunks) {label}")
            except Exception as e:
                db2.rollback()
                print(f"  [{i}/{total}] ERROR {label}\n         {e}")
            finally:
                db2.close()

        print(f"\nListo: {ok}/{total} sentencias procesadas con chunks.")

    finally:
        db.close()


if __name__ == "__main__":
    chunk_all()
