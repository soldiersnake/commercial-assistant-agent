# -*- coding: utf-8 -*-
"""prueba_agenda.py — Prueba del endpoint /api/agenda (próximos 14 días)."""
import json
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

resp = json.load(urllib.request.urlopen("http://127.0.0.1:8765/api/agenda"))
print("ok:", resp["ok"], "| eventos próximos:", len(resp["eventos"]))
for ev in resp["eventos"]:
    origen = "sistema" if ev["del_sistema"] else "a mano"
    print(f"  {ev['fecha']} {ev['hora']:12} | {ev['titulo'][:48]:48} | {origen}")
