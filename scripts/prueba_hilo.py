# -*- coding: utf-8 -*-
"""prueba_hilo.py — Prueba del endpoint /api/hilo contra un hilo real."""
import json
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

resp = json.load(urllib.request.urlopen("http://127.0.0.1:8765/api/hilo/1a13affd49eda4dc"))
print("ok:", resp["ok"], "| mensajes:", len(resp["mensajes"]))
for m in resp["mensajes"]:
    de = m["de"][:38]
    cuerpo = (m["cuerpo"] or "")[:45].replace("\n", " ")
    print(f"  [{m['tipo']:8}] {m['fecha'][:25]:25} {de:38} | {cuerpo}")
