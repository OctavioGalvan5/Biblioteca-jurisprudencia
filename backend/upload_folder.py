"""
Sube a la biblioteca todos los PDFs de una carpeta, uno por uno, vía API.

Uso:
    set BIBLIOTECA_API_URL=https://<host-del-backend>/api
    set BIBLIOTECA_USER=<usuario>
    set BIBLIOTECA_PASSWORD=<contraseña>
    python upload_folder.py "C:\\ruta\\a\\la\\carpeta" [--dry-run]

Los archivos listados en EXCLUIR (leyes, decretos, doctrina, etc.) se saltean.
Los jueces dudosos quedan pendientes: se resuelven después desde la web.
Escribe un resumen en upload_report.json junto al script.
"""
import json
import os
import sys
import time
from pathlib import Path

import requests

EXCLUIR = {
    "ley 21839.pdf",
    "ley 27423 actualizada.pdf",
    "decreto 157 2018.pdf",
    "instructivo para la carga de atencion virtual para solicitud de honorarios y seguimiento de expedientes.pdf",
    "la sentenica como unidad logica juridica.pdf",
    "defectos de fundamentacion.pdf",
    "costas procesales gozain.pdf",
    "las-costas-procesales en previsional.pdf",
    "dictamne morales blanca azucena.pdf",
}

TIMEOUT = 600  # la ingesta es síncrona (OCR + IA + embeddings)
PALABRA_CLAVE = "Honorarios"  # se agrega a todas las sentencias subidas


def agregar_palabra_clave(api, headers, sentencia_id, existentes):
    claves = list(existentes)
    if PALABRA_CLAVE.lower() not in (c.lower() for c in claves):
        claves.append(PALABRA_CLAVE)
    r = requests.put(
        f"{api}/sentencias/{sentencia_id}",
        headers=headers,
        json={"palabras_clave": claves},
        timeout=60,
    )
    return r.status_code == 200


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    if not args:
        sys.exit(__doc__)
    carpeta = Path(args[0])

    pdfs = sorted(p for p in carpeta.glob("*.pdf") if p.name.lower() not in EXCLUIR)
    omitidos = sorted(p.name for p in carpeta.glob("*.pdf") if p.name.lower() in EXCLUIR)
    print(f"{len(pdfs)} a subir, {len(omitidos)} excluidos")
    if dry:
        for p in pdfs:
            print("  ->", p.name)
        return

    api = os.environ["BIBLIOTECA_API_URL"].rstrip("/")
    r = requests.post(
        f"{api}/auth/login",
        data={"username": os.environ["BIBLIOTECA_USER"], "password": os.environ["BIBLIOTECA_PASSWORD"]},
        timeout=30,
    )
    r.raise_for_status()
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    reporte = {"ok": [], "duplicados": [], "errores": [], "excluidos": omitidos}
    for i, pdf in enumerate(pdfs, 1):
        print(f"[{i}/{len(pdfs)}] {pdf.name} ...", end=" ", flush=True)
        t0 = time.time()
        try:
            with open(pdf, "rb") as f:
                resp = requests.post(
                    f"{api}/upload/sentencia",
                    headers=headers,
                    files={"file": (pdf.name, f, "application/pdf")},
                    timeout=TIMEOUT,
                )
        except requests.RequestException as e:
            print(f"ERROR de red: {e}")
            reporte["errores"].append({"archivo": pdf.name, "error": str(e)})
            continue

        dt = time.time() - t0
        if resp.status_code == 200:
            d = resp.json()
            pend = len(d.get("jueces_pendientes", []))
            etiqueta_ok = agregar_palabra_clave(api, headers, d["sentencia_id"], d.get("extracted_data", {}).get("palabras_clave") or [])
            print(f"OK id={d['sentencia_id']} ({dt:.0f}s, {pend} jueces por revisar, etiqueta {'OK' if etiqueta_ok else 'FALLO'})")
            reporte["ok"].append({"archivo": pdf.name, "id": d["sentencia_id"], "jueces_pendientes": pend, "etiqueta": etiqueta_ok})
        elif resp.status_code == 409:
            print("ya existía")
            reporte["duplicados"].append(pdf.name)
        else:
            print(f"ERROR {resp.status_code}: {resp.text[:200]}")
            reporte["errores"].append({"archivo": pdf.name, "status": resp.status_code, "error": resp.text[:500]})

    out = Path(__file__).with_name("upload_report.json")
    out.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nOK: {len(reporte['ok'])}  duplicados: {len(reporte['duplicados'])}  errores: {len(reporte['errores'])}")
    print(f"Reporte: {out}")


if __name__ == "__main__":
    main()
