# -*- coding: utf-8 -*-
"""autorizar.py — Autorización ÚNICA del buzón (se ejecuta una vez).

Abre el navegador para que el usuario autorice el acceso de la app
a su Gmail con scopes restringidos:

  - gmail.readonly  → leer correos e hilos
  - gmail.compose   → crear borradores

NO se solicita gmail.send ni gmail.modify. El token resultante se
guarda en mcp-gmail/token.json (excluido del git) y lo usa el
servidor MCP. Para revocar: cuenta de Google → Seguridad →
Aplicaciones con acceso → quitar, y borrar token.json.

Uso:  .venv\\Scripts\\python.exe mcp-gmail\\autorizar.py
"""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402

CARPETA = Path(__file__).resolve().parent
CREDENCIALES = CARPETA / "credentials.json"
TOKEN = CARPETA / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar.events",
]


def main() -> int:
    if not CREDENCIALES.exists():
        print(f"[ERROR] No existe {CREDENCIALES}")
        print("        Descarga el credentials.json de Google Cloud y colócalo ahí.")
        return 1

    print("=" * 60)
    print("AUTORIZACIÓN ÚNICA — Gestor Comercial")
    print("=" * 60)
    print()
    print("Se abrirá tu navegador. Inicia sesión con el buzón a gestionar")
    print("(cuenta personal o corporativa) y concede el permiso.")
    print()
    print("Si aparece 'Google no ha verificado esta app':")
    print("  → clic en 'Configuración avanzada'")
    print("  → clic en 'Ir a <nombre de tu app> (no seguro)'")
    print("  → revisa los permisos (leer + borradores) y 'Permitir'")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENCIALES), SCOPES)
    credenciales = flow.run_local_server(port=0, prompt="consent",
                                         access_type="offline")

    TOKEN.write_text(credenciales.to_json(), encoding="utf-8")
    print()
    print(f"[OK] Token guardado en {TOKEN}")
    print("     (este token NO se sube al repositorio: está excluido del git)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
