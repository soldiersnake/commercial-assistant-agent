# -*- coding: utf-8 -*-
"""prueba_ocupacion.py — Prueba del endpoint /api/ocupacion."""
import json
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

resp = json.load(urllib.request.urlopen(
    "http://127.0.0.1:8765/api/ocupacion?fecha=2026-11-18"))
print("ok:", resp["ok"], "| bloques ocupados el 18/11:")
for b in resp["bloques"]:
    print("  ", b["inicio"], "-", b["fin"], "|", b["titulo"][:55])
