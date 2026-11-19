# -*- coding: utf-8 -*-
"""gcal.py — Acceso compartido a Google (Gmail + Calendar).

Único punto de credenciales OAuth para el MCP (mcp-gmail/) y el
servidor del panel (dashboard/). Usa el token de
`mcp-gmail/token.json` (gitignored).

Scopes: gmail.readonly + gmail.compose + calendar.events.
La regla de oro sigue intacta: NO se envían correos; Calendar solo
gestiona eventos en SU propio calendario (nunca invitaciones a
clientes — esos avisos salen como BORRADORES de Gmail).
"""
from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

RAIZ = Path(__file__).resolve().parent.parent
TOKEN = RAIZ / "mcp-gmail" / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar.events",
]

ZONA_HORARIA = "Europe/Madrid"


def credenciales() -> Credentials:
    if not TOKEN.exists():
        raise RuntimeError(
            "No hay token de acceso. Ejecuta antes: "
            "python mcp-gmail/autorizar.py (re-autorización con Calendar)")
    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return creds


def servicio_gmail():
    from googleapiclient.discovery import build
    return build("gmail", "v1", credentials=credenciales(),
                 cache_discovery=False)


def servicio_calendar():
    from googleapiclient.discovery import build
    return build("calendar", "v3", credentials=credenciales(),
                 cache_discovery=False)


# ── Utilidades Gmail compartidas (MCP + panel) ──────────────────

def cabeceras_de(mensaje: dict) -> dict:
    """Cabeceras de un mensaje de la API en formato diccionario."""
    salida = {}
    for cab in mensaje.get("payload", {}).get("headers", []):
        salida[cab["name"].lower()] = cab.get("value", "")
    return salida


def texto_de_mensaje(mensaje: dict) -> str:
    """Extrae el cuerpo en texto de un mensaje de la API."""
    import base64
    payload = mensaje.get("payload", {})

    def caminar(partes: list) -> tuple[str, str]:
        texto, html = "", ""
        for parte in partes:
            mime = parte.get("mimeType", "")
            datos = parte.get("body", {}).get("data")
            if not datos:
                sub = caminar(parte.get("parts", []))
                texto = texto or sub[0]
                html = html or sub[1]
                continue
            contenido = base64.urlsafe_b64decode(datos).decode("utf-8", "replace")
            if mime == "text/plain" and not texto:
                texto = contenido
            elif mime == "text/html" and not html:
                html = contenido
        return texto, html

    if "parts" in payload:
        texto, html = caminar(payload["parts"])
    else:
        datos = payload.get("body", {}).get("data")
        contenido = base64.urlsafe_b64decode(datos).decode("utf-8", "replace") if datos else ""
        texto, html = (contenido, "") if payload.get("mimeType") == "text/plain" else ("", contenido)
    if texto:
        return texto
    if html:
        import re
        import html as _html
        html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
        html = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
        html = re.sub(r"</p>", "\n\n", html, flags=re.I)
        html = re.sub(r"<[^>]+>", "", html)
        return _html.unescape(html).strip()
    return "(mensaje sin cuerpo de texto)"


def fin_de_cita(hora: str, duracion_min: int) -> str:
    """Hora de fin 'HH:MM' a partir de hora de inicio + duración en
    minutos (correcto incluso cruzando la medianoche)."""
    partes = hora.split(":")
    total = int(partes[0]) * 60 + int(partes[1]) + int(duracion_min)
    return f"{total // 60 % 24:02d}:{total % 60:02d}"


def eventos_del_dia(fecha: str) -> list[dict]:
    """Eventos del calendario del asesor para un día ('AAAA-MM-DD'),
    como bloques de ocupación: {'titulo', 'inicio', 'fin',
    'todo_el_dia'} con horas 'HH:MM' (zona Europe/Madrid)."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(ZONA_HORARIA)
    desde = datetime.fromisoformat(fecha + "T00:00:00").replace(tzinfo=tz)
    hasta = datetime.fromisoformat(fecha + "T23:59:59").replace(tzinfo=tz)
    servicio = servicio_calendar()
    res = servicio.events().list(
        calendarId="primary", timeMin=desde.isoformat(),
        timeMax=hasta.isoformat(), singleEvents=True,
        orderBy="startTime").execute()
    salida = []
    for e in res.get("items", []):
        st, en = e.get("start", {}), e.get("end", {})
        if "date" in st:  # evento de todo el día
            salida.append({"titulo": e.get("summary", "(sin título)"),
                           "todo_el_dia": True, "inicio": "00:00", "fin": "23:59"})
            continue
        salida.append({"titulo": e.get("summary", "(sin título)"),
                       "todo_el_dia": False,
                       "inicio": st.get("dateTime", "")[11:16],
                       "fin": en.get("dateTime", "")[11:16]
                       or st.get("dateTime", "")[11:16]})
    salida.sort(key=lambda x: x["inicio"])
    return salida


def agenda_proxima(dias: int = 14) -> list[dict]:
    """Eventos futuros del calendario del asesor (hoy + N días),
    incluidos los que él creó a mano en Google. Devuelve:
    {'event_id', 'fecha', 'hora', 'hora_fin', 'titulo', 'ubicacion'}."""
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(ZONA_HORARIA)
    ahora = datetime.now(tz)
    servicio = servicio_calendar()
    res = servicio.events().list(
        calendarId="primary", timeMin=ahora.isoformat(),
        timeMax=(ahora + timedelta(days=dias)).isoformat(),
        singleEvents=True, orderBy="startTime").execute()
    salida = []
    for e in res.get("items", []):
        st, en = e.get("start", {}), e.get("end", {})
        if "date" in st:
            salida.append({"event_id": e["id"], "fecha": st["date"],
                           "hora": "todo el día", "hora_fin": "",
                           "titulo": e.get("summary", "(sin título)"),
                           "ubicacion": e.get("location", "")})
        else:
            dt = st.get("dateTime", "")
            salida.append({"event_id": e["id"], "fecha": dt[:10],
                           "hora": dt[11:16] or "",
                           "hora_fin": en.get("dateTime", "")[11:16] or "",
                           "titulo": e.get("summary", "(sin título)"),
                           "ubicacion": e.get("location", "")})
    return salida


def hilo_para_panel(thread_id: str) -> list[dict]:
    """Devuelve la conversación de un hilo ordenada por fecha, con
    etiquetas normalizadas para la vista del panel."""
    servicio = servicio_gmail()
    hilo = servicio.users().threads().get(
        userId="me", id=thread_id, format="full").execute()
    mensajes = []
    for msg in hilo.get("messages", []):
        cab = cabeceras_de(msg)
        etiquetas = msg.get("labelIds", [])
        tipo = ("ENVIADO" if "SENT" in etiquetas
                else "BORRADOR" if "DRAFT" in etiquetas else "RECIBIDO")
        mensajes.append({
            "id": msg["id"],
            "de": cab.get("from", ""),
            "fecha": cab.get("date", ""),
            "tipo": tipo,
            "asunto": cab.get("subject", ""),
            "cuerpo": texto_de_mensaje(msg)[:4000],
        })
    return mensajes
