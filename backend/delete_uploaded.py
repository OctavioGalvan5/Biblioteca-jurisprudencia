"""
Borra las sentencias que subió upload_folder.py (ids guardados en upload_report.json).

Uso (mismas variables de entorno que upload_folder.py):
    python delete_uploaded.py             # solo lista lo que borraría
    python delete_uploaded.py --confirm   # borra de verdad (fila + chunks + PDF en MinIO)
"""
import json
import os
import sys
from pathlib import Path

import requests

reporte = json.loads(Path(__file__).with_name("upload_report.json").read_text(encoding="utf-8"))
items = reporte["ok"]
confirm = "--confirm" in sys.argv

print(f"{len(items)} sentencias del reporte:")
for it in items:
    print(f"  id={it['id']}  {it['archivo']}")
if not confirm:
    sys.exit("\nModo simulación: no se borró nada. Agregá --confirm para borrar.")

api = os.environ["BIBLIOTECA_API_URL"].rstrip("/")
r = requests.post(
    f"{api}/auth/login",
    data={"username": os.environ["BIBLIOTECA_USER"], "password": os.environ["BIBLIOTECA_PASSWORD"]},
    timeout=30,
)
r.raise_for_status()
headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

borradas = 0
for it in items:
    resp = requests.delete(f"{api}/sentencias/{it['id']}", headers=headers, timeout=60)
    ok = resp.status_code in (200, 204)
    borradas += ok
    print(f"id={it['id']}: {'borrada' if ok else 'ERROR ' + str(resp.status_code)}")
print(f"\n{borradas}/{len(items)} borradas")
