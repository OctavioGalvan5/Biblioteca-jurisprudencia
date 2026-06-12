"""
Genera embeddings para todas las sentencias que aún no los tienen.

Uso (desde la carpeta backend/, con el venv activo):
    python embed_existing.py

El script es idempotente: si se interrumpe, al correrlo de nuevo
solo procesa las sentencias que quedaron sin embedding.
"""

import sys
import os

# Asegurar que Python encuentre el paquete 'app'
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text
from app.core.database import engine, SessionLocal
from app.models.database_models import Sentencia, SentenciaVector
from app.services.embedding_service import embedding_service


def setup_pgvector():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text(
            "ALTER TABLE sentencias_vectors ADD COLUMN IF NOT EXISTS embedding vector(1536)"
        ))
        conn.commit()


def embed_all():
    setup_pgvector()
    db = SessionLocal()

    try:
        embedded_ids = {row[0] for row in db.query(SentenciaVector.sentencia_id).all()}
        pending = db.query(Sentencia).filter(~Sentencia.id.in_(embedded_ids)).order_by(Sentencia.id).all()

        total = len(pending)
        if total == 0:
            print("✅ Todas las sentencias ya tienen embedding.")
            return

        print(f"📄 {total} sentencia(s) sin embedding. Procesando...\n")

        ok = 0
        for i, s in enumerate(pending, 1):
            label = s.caratula or f"ID {s.id}"
            try:
                vector = embedding_service.embed_sentencia(s)
                sv = db.query(SentenciaVector).filter(SentenciaVector.sentencia_id == s.id).first()
                if sv:
                    sv.embedding = vector
                else:
                    db.add(SentenciaVector(sentencia_id=s.id, embedding=vector))
                db.commit()
                ok += 1
                print(f"  [{i}/{total}] ✅ {label[:80]}")
            except Exception as e:
                db.rollback()
                print(f"  [{i}/{total}] ❌ {label[:80]}\n         Error: {e}")

        print(f"\n✅ Listo: {ok}/{total} embeddings generados.")

    finally:
        db.close()


if __name__ == "__main__":
    embed_all()
