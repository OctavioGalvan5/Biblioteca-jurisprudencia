"""
Migración MySQL (calculadoras.sentencias) → Biblioteca Jurisprudencia.

Por cada sentencia con drive_link:
  1. Verifica que no sea duplicado (SHA-256 del PDF)
  2. Descarga el PDF desde Google Drive
  3. Sube a MinIO
  4. Importa metadata directamente desde MySQL (sin re-extraer con IA)
  5. Extrae texto completo (con OCR fallback si es escaneado)
  6. Genera chunks + embeddings

Uso (desde backend/, con el venv activo):
    python migrate_from_mysql.py              # migra todo
    python migrate_from_mysql.py --limit 10   # solo 10 para probar
    python migrate_from_mysql.py --offset 50  # arranca desde la fila 50
    python migrate_from_mysql.py --inspect    # solo muestra 5 filas de ejemplo
"""

import sys
import os
import re
import time
import hashlib
import io
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

import pymysql
import requests

from app.core.database import engine, SessionLocal
from app.core.minio_client import minio_client
from app.models.database_models import Sentencia, SentenciaChunk
from app.services.pdf_processor import pdf_processor
from app.services.embedding_service import embedding_service
from app.services.chunking_service import chunking_service
from sqlalchemy import text


MYSQL_HOST = "76.13.233.143"
MYSQL_PORT = 3306
MYSQL_USER = "admin"
MYSQL_PASS = "root2026"
MYSQL_DB   = "calculadoras"

# Seconds between Drive downloads to avoid rate limiting
DOWNLOAD_DELAY = 1.5


# ── Helpers ──────────────────────────────────────────────────────────────────

FEDERAL_KEYWORDS = [
    "federal", "nacional", "nacion", "caf", "css", "fsa", "fro", "fcb",
    "fvm", "fbb", "csjn", "csj", "corte suprema", "camara", "juzgado federal",
    "ccf", "fcr", "flp", "fmz", "fsal", "fsm", "fsl",
]
PROVINCIAL_KEYWORDS = ["provincial", "provincia", "local"]


def map_jurisdiccion(raw: str | None) -> str | None:
    if not raw:
        return None
    low = raw.lower()
    if any(k in low for k in PROVINCIAL_KEYWORDS):
        return "provincial"
    if any(k in low for k in FEDERAL_KEYWORDS):
        return "federal"
    # Default for ANSES cases (all federal jurisdiction)
    return "federal"


def parse_palabras_clave(raw: str | None) -> list[str]:
    if not raw:
        return []
    raw = raw.strip()
    # Try JSON array first
    if raw.startswith("["):
        import json
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(p).strip() for p in parsed if str(p).strip()]
        except Exception:
            pass
    # Comma-separated
    return [p.strip() for p in re.split(r"[,;]", raw) if p.strip()]


def extract_drive_id(url: str) -> str | None:
    patterns = [
        r"/file/d/([a-zA-Z0-9_-]+)",
        r"[?&]id=([a-zA-Z0-9_-]+)",
        r"/open\?id=([a-zA-Z0-9_-]+)",
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def download_from_drive(url: str) -> bytes:
    file_id = extract_drive_id(url)
    if not file_id:
        raise ValueError(f"No se pudo extraer el ID de Drive: {url}")

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    resp = session.get(download_url, timeout=60)

    content_type = resp.headers.get("Content-Type", "")
    if "text/html" in content_type:
        # Large file warning — find confirm token
        token = re.search(r'confirm=([a-zA-Z0-9_-]+)', resp.text)
        if not token:
            token = re.search(r'name="confirm"\s+value="([^"]+)"', resp.text)
        if token:
            resp = session.get(
                f"https://drive.google.com/uc?export=download&id={file_id}&confirm={token.group(1)}",
                timeout=120,
            )
        else:
            # Try with confirm=t (works for most cases)
            resp = session.get(
                f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t",
                timeout=120,
            )

    if len(resp.content) < 1000:
        raise ValueError(f"Descarga sospechosamente pequeña ({len(resp.content)} bytes) — archivo privado?")

    return resp.content


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── Core migration ────────────────────────────────────────────────────────────

def connect_mysql():
    return pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT,
        user=MYSQL_USER, password=MYSQL_PASS,
        database=MYSQL_DB, charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def setup_pgvector():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text(
            "ALTER TABLE sentencias_chunks ADD COLUMN IF NOT EXISTS embedding vector(1536)"
        ))
        conn.commit()


def migrate(limit: int | None = None, offset: int = 0):
    setup_pgvector()
    mysql = connect_mysql()
    db = SessionLocal()

    try:
        cur = mysql.cursor()
        query = """
            SELECT id, caratula, resumen, instancia, juzgado, jurisdiccion,
                   numero_expediente, fecha_sentencia, palabras_clave,
                   fundamentos, normativa, drive_link, file_hash
            FROM sentencias
            WHERE drive_link IS NOT NULL AND drive_link != ''
            ORDER BY id
        """
        if limit:
            query += f" LIMIT {int(limit)} OFFSET {int(offset)}"
        elif offset:
            query += f" LIMIT 99999 OFFSET {int(offset)}"

        cur.execute(query)
        rows = cur.fetchall()
        total = len(rows)

        if total == 0:
            print("No hay sentencias con drive_link para migrar.")
            return

        print(f"\n{total} sentencia(s) a migrar.\n")

        ok = 0
        dup = 0
        err = 0

        for i, row in enumerate(rows, 1):
            label = (row.get("caratula") or f"MySQL ID {row['id']}")[:80]
            drive_url = row["drive_link"]

            try:
                # 1. Download PDF
                print(f"  [{i}/{total}] Descargando: {label[:60]}")
                pdf_bytes = download_from_drive(drive_url)
                time.sleep(DOWNLOAD_DELAY)

                # 2. Compute hash and check for duplicates
                file_hash = sha256(pdf_bytes)
                existing = db.query(Sentencia).filter(Sentencia.hash == file_hash).first()
                if existing:
                    print(f"  [{i}/{total}] DUP (ID {existing.id}) {label}")
                    dup += 1
                    continue

                # 3. Upload to MinIO
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                object_name = f"{file_hash}_{ts}.pdf"
                minio_url = minio_client.upload_file(
                    file_data=io.BytesIO(pdf_bytes),
                    object_name=object_name,
                    content_type="application/pdf",
                )

                # 4. Extract full text (OCR fallback built-in)
                contenido = pdf_processor.extract_text(pdf_bytes)

                # 5. Build metadata from MySQL — no AI needed
                fecha = row.get("fecha_sentencia")  # already a date object from MySQL
                jur = map_jurisdiccion(row.get("jurisdiccion"))
                kw = parse_palabras_clave(row.get("palabras_clave"))

                # Combine resumen + fundamentos + normativa as resumen if available
                resumen_parts = [p for p in [
                    row.get("resumen"),
                    row.get("fundamentos"),
                    row.get("normativa"),
                ] if p and p.strip()]
                resumen_final = "\n\n".join(resumen_parts) if resumen_parts else None

                nueva = Sentencia(
                    hash=file_hash,
                    url_minio=minio_url,
                    caratula=row.get("caratula"),
                    nro_expediente=row.get("numero_expediente"),
                    fecha_sentencia=fecha,
                    instancia=row.get("instancia"),
                    organo=row.get("juzgado"),
                    jurisdiccion=jur,
                    palabras_clave=kw or [],
                    contenido=contenido,
                    resumen=resumen_final,
                )
                db.add(nueva)
                db.commit()
                db.refresh(nueva)

                # 6. Generate chunks + embeddings
                chunks = chunking_service.chunk_sentencia(contenido)
                for idx, chunk in enumerate(chunks):
                    emb = embedding_service.embed(chunk["contenido"])
                    db.add(SentenciaChunk(
                        sentencia_id=nueva.id,
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
                err += 1
                print(f"  [{i}/{total}] ERROR {label}\n           {e}")

        print(f"\n{'='*60}")
        print(f"Migradas: {ok}  |  Duplicadas: {dup}  |  Errores: {err}  |  Total: {total}")

    finally:
        db.close()
        mysql.close()


def inspect():
    mysql = connect_mysql()
    cur = mysql.cursor()
    cur.execute("""
        SELECT id, caratula, jurisdiccion, fecha_sentencia, drive_link
        FROM sentencias
        WHERE drive_link IS NOT NULL AND drive_link != ''
        LIMIT 5
    """)
    rows = cur.fetchall()
    print("\nMuestra de 5 sentencias con drive_link:\n")
    for r in rows:
        print(f"  ID {r['id']}: {(r['caratula'] or '')[:60]}")
        print(f"    Jurisdiccion: {r['jurisdiccion']}")
        print(f"    Fecha: {r['fecha_sentencia']}")
        print(f"    Link: {r['drive_link']}")
        print()
    mysql.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspect", action="store_true", help="Mostrar 5 filas de ejemplo")
    parser.add_argument("--limit", type=int, default=None, help="Procesar solo N sentencias")
    parser.add_argument("--offset", type=int, default=0, help="Arrancar desde la fila N")
    args = parser.parse_args()

    if args.inspect:
        inspect()
    else:
        migrate(limit=args.limit, offset=args.offset)
