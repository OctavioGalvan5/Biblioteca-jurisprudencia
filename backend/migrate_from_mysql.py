"""
Migración MySQL (calculadoras.sentencias) → Biblioteca Jurisprudencia.

Por cada sentencia con drive_link:
  1. Verifica que no sea duplicado (SHA-256 del PDF)
  2. Descarga el PDF desde Google Drive
  3. Sube a MinIO
  4. Importa metadata directamente desde MySQL (sin re-extraer con IA)
  5. Extrae texto completo (con OCR fallback si es escaneado)
  6. Genera chunks + embeddings
  7. Vincula jueces con fuzzy matching — crea los que no existen

Uso (desde backend/, con el venv activo):
    python migrate_from_mysql.py              # migra todo
    python migrate_from_mysql.py --limit 10   # solo 10 para probar
    python migrate_from_mysql.py --offset 50  # arranca desde la fila 50
    python migrate_from_mysql.py --inspect    # muestra 5 filas de ejemplo
"""

import sys
import os
import re
import time
import hashlib
import io
import json
import argparse
from datetime import datetime
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

import logging
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

import pymysql
import requests

from app.core.database import engine, SessionLocal
engine.echo = False  # suppress SQL logs regardless of DEBUG setting
from app.core.minio_client import minio_client
from app.models.database_models import Sentencia, SentenciaChunk, Juez, SentenciaJuez
from app.services.pdf_processor import pdf_processor
from app.services.ai_extractor import ai_extractor
from app.services.embedding_service import embedding_service
from app.services.chunking_service import chunking_service
from sqlalchemy import text


MYSQL_HOST = "76.13.233.143"
MYSQL_PORT = 3306
MYSQL_USER = "admin"
MYSQL_PASS = "root2026"
MYSQL_DB   = "calculadoras"

DOWNLOAD_DELAY = 1.5       # seconds between Drive requests
SIMILITUD_LINK = 0.70      # fuzzy threshold to auto-link existing judge
SIMILITUD_HIGH = 0.95      # high-confidence match (same logic as upload.py)

# Phrases that indicate no judge info available
NO_JUDGE_PHRASES = [
    "no se mencionan", "no se menciona", "no se puede", "no se indica",
    "no disponible", "no hay", "desconocido",
]


# ── Jurisdiction mapping ──────────────────────────────────────────────────────

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
    return "federal"  # default for ANSES cases


# ── Keywords parsing ──────────────────────────────────────────────────────────

def parse_palabras_clave(raw: str | None) -> list[str]:
    if not raw:
        return []
    raw = raw.strip()
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(p).strip() for p in parsed if str(p).strip()]
        except Exception:
            pass
    return [p.strip() for p in re.split(r"[,;]", raw) if p.strip()]


# ── Judge parsing and matching ────────────────────────────────────────────────

def parse_judge_names(raw: str | None) -> list[str]:
    """Parse free-text jueces field into a list of individual judge names."""
    if not raw or not raw.strip():
        return []
    low = raw.lower()
    if any(phrase in low for phrase in NO_JUDGE_PHRASES):
        return []

    # Remove common honorific prefixes
    cleaned = re.sub(r'\b(dres?\.?|dras?\.?|dr\.?|lic\.?)\s*', '', raw, flags=re.IGNORECASE)
    # Split by comma or semicolon
    parts = [p.strip() for p in re.split(r"[,;]", cleaned)]
    return [p for p in parts if len(p.split()) >= 1 and len(p) > 2]


def _similitud(a: str, b: str) -> float:
    return SequenceMatcher(None, a.upper().strip(), b.upper().strip()).ratio()


def find_best_match(nombre_raw: str, jueces_db: list) -> tuple:
    """Return (best_juez, similarity) against all known judges."""
    partes = nombre_raw.strip().split()
    if not partes:
        return None, 0.0

    apellido = partes[-1].upper()
    nombre_completo = nombre_raw.upper()
    mejor_juez = None
    mejor_sim = 0.0

    for juez in jueces_db:
        nombre_db = f"{juez.nombre} {juez.apellido}".upper()
        sim = max(
            _similitud(nombre_completo, nombre_db),
            _similitud(apellido, juez.apellido.upper()),
        )
        if sim > mejor_sim:
            mejor_sim = sim
            mejor_juez = juez

    return mejor_juez, mejor_sim


def split_nombre_apellido(nombre_raw: str) -> tuple[str, str]:
    """
    Split 'Juan Carlos Pérez' → ('Juan Carlos', 'Pérez').
    If only one word assume it's the apellido.
    """
    partes = nombre_raw.strip().split()
    if len(partes) == 1:
        return "", partes[0].title()
    return " ".join(partes[:-1]).title(), partes[-1].title()


def _jueces_raw_useless(jueces_raw: str | None) -> bool:
    """True when the MySQL jueces field has no usable names."""
    if not jueces_raw or not jueces_raw.strip():
        return True
    return any(phrase in jueces_raw.lower() for phrase in NO_JUDGE_PHRASES)


def extract_jueces_via_vision(pdf_bytes: bytes, db) -> list[str]:
    """Fallback: extract judge names from the PDF signature page using GPT-4o Vision."""
    img_b64 = pdf_processor.convert_last_page_to_image(pdf_bytes)
    if not img_b64:
        return []
    known = [{"nombre": j.nombre, "apellido": j.apellido}
             for j in db.query(Juez).filter(Juez.activo == True).all()]
    return ai_extractor.extract_judges_from_image(img_b64, known)


def vincular_jueces(sentencia_id: int, nombres: list[str], db):
    """
    Fuzzy-match or create each judge name, then link to sentencia.
    Same logic as the upload confirm-jueces endpoint.
    """
    if not nombres:
        return 0

    jueces_db = db.query(Juez).filter(Juez.activo == True).all()
    vinculados = 0

    for nombre_raw in nombres:
        nombre_raw = nombre_raw.strip()
        if not nombre_raw:
            continue
        mejor_juez, sim = find_best_match(nombre_raw, jueces_db)

        if sim >= SIMILITUD_LINK and mejor_juez:
            juez = mejor_juez
        else:
            # Create new judge
            nombre, apellido = split_nombre_apellido(nombre_raw)
            if not apellido:
                continue
            juez = Juez(nombre=nombre, apellido=apellido, activo=True)
            db.add(juez)
            db.flush()
            jueces_db.append(juez)  # update local cache for subsequent names
            action = "CREADO"
            print(f"       -> {action}: {juez.nombre} {juez.apellido}")

        # Avoid duplicate links
        already = db.query(SentenciaJuez).filter(
            SentenciaJuez.sentencia_id == sentencia_id,
            SentenciaJuez.juez_id == juez.id,
        ).first()
        if not already:
            db.add(SentenciaJuez(sentencia_id=sentencia_id, juez_id=juez.id))
            vinculados += 1

    return vinculados


# ── Drive download ────────────────────────────────────────────────────────────

def extract_drive_id(url: str) -> str | None:
    for pat in [r"/file/d/([a-zA-Z0-9_-]+)", r"[?&]id=([a-zA-Z0-9_-]+)", r"/open\?id=([a-zA-Z0-9_-]+)"]:
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
    dl = f"https://drive.google.com/uc?export=download&id={file_id}"
    resp = session.get(dl, timeout=60)

    if "text/html" in resp.headers.get("Content-Type", ""):
        token = re.search(r'confirm=([a-zA-Z0-9_-]+)', resp.text)
        if not token:
            token = re.search(r'name="confirm"\s+value="([^"]+)"', resp.text)
        confirm = token.group(1) if token else "t"
        resp = session.get(f"{dl}&confirm={confirm}", timeout=120)

    if len(resp.content) < 1000:
        raise ValueError(f"Descarga muy pequena ({len(resp.content)} bytes) — privado?")
    return resp.content


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── DB setup ──────────────────────────────────────────────────────────────────

def connect_mysql():
    return pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASS,
        database=MYSQL_DB, charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
    )


def setup_pgvector():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text("ALTER TABLE sentencias_chunks ADD COLUMN IF NOT EXISTS embedding vector(1536)"))
        conn.commit()


# ── Migration ─────────────────────────────────────────────────────────────────

def _process_row(row: dict, i: int, total: int) -> str:
    """Process a single sentencia. Returns 'ok', 'dup', or 'err'."""
    label = (row.get("caratula") or f"MySQL ID {row['id']}")[:80]
    drive_url = row["drive_link"]

    # Fresh DB session per sentencia — avoids idle connection drops from pgbouncer
    db = SessionLocal()
    try:
        print(f"  [{i}/{total}] Descargando: {label[:60]}")
        pdf_bytes = download_from_drive(drive_url)
        time.sleep(DOWNLOAD_DELAY)

        file_hash = sha256(pdf_bytes)
        existing = db.query(Sentencia).filter(Sentencia.hash == file_hash).first()
        if existing:
            print(f"  [{i}/{total}] DUP (ID {existing.id})")
            return "dup"

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        object_name = f"{file_hash}_{ts}.pdf"
        minio_url = minio_client.upload_file(
            file_data=io.BytesIO(pdf_bytes),
            object_name=object_name,
            content_type="application/pdf",
        )

        contenido = pdf_processor.extract_text(pdf_bytes)

        resumen_parts = [p for p in [
            row.get("resumen"), row.get("fundamentos"), row.get("normativa"),
        ] if p and p.strip()]

        nueva = Sentencia(
            hash=file_hash,
            url_minio=minio_url,
            caratula=row.get("caratula"),
            nro_expediente=row.get("numero_expediente"),
            fecha_sentencia=row.get("fecha_sentencia"),
            instancia=row.get("instancia"),
            organo=row.get("juzgado"),
            jurisdiccion=map_jurisdiccion(row.get("jurisdiccion")),
            palabras_clave=parse_palabras_clave(row.get("palabras_clave")),
            contenido=contenido,
            resumen="\n\n".join(resumen_parts) if resumen_parts else None,
        )
        db.add(nueva)
        db.commit()
        db.refresh(nueva)

        # Judges
        jueces_raw = row.get("jueces")
        if _jueces_raw_useless(jueces_raw):
            print(f"       -> sin jueces en MySQL, usando Vision...")
            nombres_jueces = extract_jueces_via_vision(pdf_bytes, db)
        else:
            nombres_jueces = parse_judge_names(jueces_raw)
        n_jueces = vincular_jueces(nueva.id, nombres_jueces, db)
        db.commit()

        # Chunks + embeddings
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

        print(f"  [{i}/{total}] OK | {len(chunks)} chunks | {n_jueces} jueces | {label}")
        return "ok"

    except Exception as e:
        db.rollback()
        print(f"  [{i}/{total}] ERROR {label}\n           {e}")
        return "err"
    finally:
        db.close()


def migrate(limit: int | None = None, offset: int = 0):
    setup_pgvector()
    mysql = connect_mysql()

    try:
        cur = mysql.cursor()
        query = """
            SELECT id, caratula, resumen, instancia, juzgado, jurisdiccion,
                   numero_expediente, fecha_sentencia, palabras_clave,
                   fundamentos, normativa, jueces, drive_link
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
        ok = dup = err = 0

        for i, row in enumerate(rows, 1):
            result = _process_row(row, i, total)
            if result == "ok":
                ok += 1
            elif result == "dup":
                dup += 1
            else:
                err += 1

        print(f"\n{'='*60}")
        print(f"Migradas: {ok}  |  Duplicadas: {dup}  |  Errores: {err}  |  Total: {total}")

    finally:
        mysql.close()


def inspect():
    mysql = connect_mysql()
    cur = mysql.cursor()
    cur.execute("""
        SELECT id, caratula, jurisdiccion, fecha_sentencia, jueces, drive_link
        FROM sentencias WHERE drive_link IS NOT NULL AND drive_link != '' LIMIT 5
    """)
    print("\nMuestra de 5 sentencias:\n")
    for r in cur.fetchall():
        print(f"  ID {r['id']}: {(r['caratula'] or '')[:60]}")
        print(f"    Jurisdiccion: {r['jurisdiccion']}")
        print(f"    Fecha: {r['fecha_sentencia']}")
        print(f"    Jueces: {r['jueces']}")
        print(f"    Link: {r['drive_link']}")
        print()
    mysql.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()

    if args.inspect:
        inspect()
    else:
        migrate(limit=args.limit, offset=args.offset)
