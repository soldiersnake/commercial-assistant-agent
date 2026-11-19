# -*- coding: utf-8 -*-
"""prueba_acceso.py — Prueba rápida de la conexión a Gmail.

1. Lista los no leídos más recientes (solo lectura).
2. Crea un borrador de PRUEBA dirigido al propio buzón.
3. Lo lista entre los borradores.
4. Lo ELIMINA para no dejar rastro.

Uso:  .venv\\Scripts\\python.exe mcp-gmail\\prueba_acceso.py
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

CARPETA = Path(__file__).resolve().parent
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]


def main() -> int:
    creds = Credentials.from_authorized_user_file(str(CARPETA / "token.json"), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        (CARPETA / "token.json").write_text(creds.to_json(), encoding="utf-8")
    servicio = build("gmail", "v1", credentials=creds, cache_discovery=False)

    # 1 — no leídos
    res = servicio.users().messages().list(
        userId="me", q="is:unread", maxResults=5).execute()
    mensajes = res.get("messages", [])
    print(f"[1] No leídos (últimos {len(mensajes)}):")
    for m in mensajes:
        msg = servicio.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["From", "Subject", "Date"]).execute()
        cab = {h["name"]: h["value"] for h in
               msg["payload"].get("headers", [])}
        print(f"    · {cab.get('From', '?')[:45]:45} | {cab.get('Subject', '(sin asunto)')[:50]}")

    # 2 — borrador de prueba
    raw = base64.urlsafe_b64encode(
        ("To: destinatario@ejemplo.com\r\n"
         "Subject: [PRUEBA del sistema - se elimina sola]\r\n\r\n"
         "Este borrador es una prueba del Gestor Comercial.\r\n"
         "Se crea y se elimina automaticamente; no hace falta hacer nada.\r\n"
         ).encode("utf-8")).decode()
    draft = servicio.users().drafts().create(
        userId="me", body={"message": {"raw": raw}}).execute()
    print(f"[2] Borrador de prueba creado: {draft['id']}")

    # 3 — listar borradores
    lista = servicio.users().drafts().list(userId="me", maxResults=5).execute()
    print(f"[3] Borradores en el buzón: {len(lista.get('drafts', []))}")

    # 4 — eliminarlo
    servicio.users().drafts().delete(userId="me", id=draft["id"]).execute()
    print("[4] Borrador de prueba eliminado — el buzón queda limpio")
    print()
    print("[OK] CONEXIÓN VERIFICADA: lectura + borradores funcionando")
    return 0


if __name__ == "__main__":
    sys.exit(main())
