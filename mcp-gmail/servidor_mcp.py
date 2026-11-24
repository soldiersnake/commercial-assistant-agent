# -*- coding: utf-8 -*-
"""servidor_mcp.py — MCP de Gmail (lectura + borradores) y Google Calendar.

Regla de oro del proyecto: este servidor NUNCA envía correos.
No existe ninguna llamada a endpoints de envío en este código —
en Gmail las únicas operaciones son leer (readonly) y crear/listar/
actualizar borradores (compose). El usuario revisa y envía desde Gmail.
En Calendar solo toca el calendario del asesor, sin invitados.

Herramientas MCP expuestas:
  Gmail
  gmail_list_unread(max)          — correos no leídos recientes
  gmail_search(consulta, max)     — búsqueda con sintaxis de Gmail
  gmail_get_thread(thread_id)     — hilo completo (contexto)
  gmail_get_message(message_id)   — un mensaje suelto
  gmail_list_drafts(max)          — borradores pendientes
  gmail_create_draft(para, asunto, cuerpo)            — borrador nuevo
  gmail_create_draft_reply(thread_id, cuerpo, ...)    — borrador EN el hilo
  gmail_update_draft(draft_id, para, asunto, cuerpo)  — sustituye un borrador

  Google Calendar
  calendar_list_events(desde, hasta, max)             — eventos entre fechas
  calendar_create_event(titulo, fecha, hora, ...)     — cita nueva, sin invitados
  calendar_update_event(event_id, ...)                — reprogramar / editar
  calendar_delete_event(event_id)                     — cancelar una cita

Uso (lo configura el cliente IA):
  .venv\\Scripts\\python.exe mcp-gmail\\servidor_mcp.py   (transporte stdio)
"""
from __future__ import annotations

import base64
import json
import sys
from email.message import EmailMessage
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import gcal as gcal_mod  # noqa: E402

CARPETA = Path(__file__).resolve().parent
CREDENCIALES = CARPETA / "credentials.json"
TOKEN = CARPETA / "token.json"

SCOPES = gcal_mod.SCOPES  # gmail.readonly + gmail.compose + calendar.events

mcp = FastMCP("gmail-calendar")

# ── Anotaciones MCP ─────────────────────────────────────────────
# Pistas (hints) que el cliente IA lee al listar las herramientas:
# le dicen si una herramienta solo lee, si puede sobrescribir o borrar
# datos y si repetirla tiene el mismo efecto, para que decida cuándo
# pedir confirmación al usuario. No cambian el comportamiento del
# servidor. openWorldHint=True en todas porque hablan con Google.
SOLO_LECTURA = ToolAnnotations(readOnlyHint=True, destructiveHint=False,
                               idempotentHint=True, openWorldHint=True)
CREA = ToolAnnotations(readOnlyHint=False, destructiveHint=False,
                       idempotentHint=False, openWorldHint=True)
SOBRESCRIBE = ToolAnnotations(readOnlyHint=False, destructiveHint=True,
                              idempotentHint=True, openWorldHint=True)
ELIMINA = ToolAnnotations(readOnlyHint=False, destructiveHint=True,
                          idempotentHint=True, openWorldHint=True)


# ── Servicio Gmail ──────────────────────────────────────────────

def _credenciales() -> Credentials:
    if not TOKEN.exists():
        raise RuntimeError(
            "No hay token de acceso. Ejecuta antes: "
            "python mcp-gmail/autorizar.py")
    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return creds


def _servicio():
    return build("gmail", "v1", credentials=_credenciales(),
                 cache_discovery=False)


def _servicio_calendar():
    return gcal_mod.servicio_calendar()


# ── Utilidades ──────────────────────────────────────────────────

def _cabeceras(mensaje: dict) -> dict:
    """Cabeceras de un mensaje de la API en formato diccionario."""
    salida = {}
    for cab in mensaje.get("payload", {}).get("headers", []):
        salida[cab["name"].lower()] = cab.get("value", "")
    return salida


def _resumen_mensaje(id_: str, cab: dict, snippet: str, hilo: str) -> dict:
    return {
        "id": id_,
        "threadId": hilo,
        "de": cab.get("from", ""),
        "para": cab.get("to", ""),
        "fecha": cab.get("date", ""),
        "asunto": cab.get("subject", "(sin asunto)"),
        "vista_previa": snippet,
    }


def _texto_mensaje(mensaje: dict) -> str:
    """Extrae el cuerpo en texto (plain si existe; si no, HTML→texto)."""
    payload = mensaje.get("payload", {})

    def caminar(partes: list) -> tuple[str, str]:
        texto, html = "", ""
        for parte in partes:
            mime = parte.get("mimeType", "")
            cuerpo = parte.get("body", {})
            datos = cuerpo.get("data")
            if not datos:
                sub = caminar(parte.get("parts", []))
                if not texto:
                    texto = sub[0]
                if not html:
                    html = sub[1]
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
        # quitar etiquetas básicas para dejar texto legible
        import re
        html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
        html = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
        html = re.sub(r"</p>", "\n\n", html, flags=re.I)
        html = re.sub(r"<[^>]+>", "", html)
        import html as _html
        return _html.unescape(html).strip()
    return "(mensaje sin cuerpo de texto)"


# ── Herramientas MCP ────────────────────────────────────────────

@mcp.tool(annotations=SOLO_LECTURA)
def gmail_list_unread(max: int = 15) -> str:
    """Lista los correos NO leídos recientes del buzón (los más nuevos primero)."""
    servicio = _servicio()
    res = servicio.users().messages().list(
        userId="me", q="is:unread -category:promotions -category:social",
        maxResults=min(max, 50)).execute()
    mensajes = res.get("messages", [])
    salida = []
    for m in mensajes:
        msg = servicio.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"]).execute()
        cab = _cabeceras(msg)
        salida.append(_resumen_mensaje(m["id"], cab, msg.get("snippet", ""),
                                       msg.get("threadId", "")))
    return json.dumps({"total_no_leidos_listados": len(salida),
                       "mensajes": salida}, ensure_ascii=False, indent=1)


@mcp.tool(annotations=SOLO_LECTURA)
def gmail_search(consulta: str, max: int = 15) -> str:
    """Busca correos con la sintaxis de Gmail. Ejemplos:
    'from:laruiz@gmail.com', 'presupuesto Cortes Valencianas',
    'is:unread is:important', 'after:2026/11/01 administracion'."""
    servicio = _servicio()
    res = servicio.users().messages().list(
        userId="me", q=consulta, maxResults=min(max, 50)).execute()
    salida = []
    for m in res.get("messages", []):
        msg = servicio.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"]).execute()
        cab = _cabeceras(msg)
        salida.append(_resumen_mensaje(m["id"], cab, msg.get("snippet", ""),
                                       msg.get("threadId", "")))
    return json.dumps({"consulta": consulta, "resultados": len(salida),
                       "mensajes": salida}, ensure_ascii=False, indent=1)


@mcp.tool(annotations=SOLO_LECTURA)
def gmail_get_thread(thread_id: str) -> str:
    """Devuelve un hilo COMPLETO con todos sus mensajes en orden,
    incluyendo el cuerpo de texto de cada uno (para responder con contexto)."""
    servicio = _servicio()
    hilo = servicio.users().threads().get(
        userId="me", id=thread_id, format="full").execute()
    salida = []
    for msg in hilo.get("messages", []):
        cab = _cabeceras(msg)
        salida.append({
            **_resumen_mensaje(msg["id"], cab, msg.get("snippet", ""),
                               hilo.get("id", "")),
            "cuerpo": _texto_mensaje(msg),
            "etiquetas": msg.get("labelIds", []),
        })
    return json.dumps({"threadId": hilo.get("id"),
                       "mensajes": salida}, ensure_ascii=False, indent=1)


@mcp.tool(annotations=SOLO_LECTURA)
def gmail_get_message(message_id: str) -> str:
    """Devuelve un mensaje concreto con su cuerpo completo."""
    servicio = _servicio()
    msg = servicio.users().messages().get(
        userId="me", id=message_id, format="full").execute()
    cab = _cabeceras(msg)
    salida = {**_resumen_mensaje(msg["id"], cab, msg.get("snippet", ""),
                                 msg.get("threadId", "")),
              "cuerpo": _texto_mensaje(msg),
              "etiquetas": msg.get("labelIds", [])}
    return json.dumps(salida, ensure_ascii=False, indent=1)


@mcp.tool(annotations=SOLO_LECTURA)
def gmail_list_drafts(max: int = 15) -> str:
    """Lista los borradores existentes (pendientes de revisión y envío por el usuario)."""
    servicio = _servicio()
    res = servicio.users().drafts().list(userId="me",
                                         maxResults=min(max, 50)).execute()
    salida = []
    for d in res.get("drafts", []):
        msg = d.get("message", {})
        # drafts.list no trae cabeceras: pedir cada borrador completo
        if not msg.get("payload", {}).get("headers"):
            try:
                completo = servicio.users().drafts().get(
                    userId="me", id=d["id"], format="full").execute()
                msg = completo.get("message", msg)
            except Exception:
                pass
        cab = _cabeceras(msg)
        salida.append({
            "draftId": d["id"],
            **_resumen_mensaje(msg.get("id", ""), cab, "", msg.get("threadId", "")),
        })
    return json.dumps({"borradores": len(salida), "lista": salida},
                      ensure_ascii=False, indent=1)


def _raw_para_draft(cuerpo: str, para: str, asunto: str,
                    reply_a: str | None, referencias: str | None) -> str:
    """Construye el MIME del mensaje para el borrador."""
    email = EmailMessage()
    email["To"] = para
    email["Subject"] = asunto
    if reply_a:
        email["In-Reply-To"] = reply_a
    if referencias:
        email["References"] = referencias
    email.set_content(cuerpo)
    return base64.urlsafe_b64encode(email.as_bytes()).decode()


@mcp.tool(annotations=CREA)
def gmail_create_draft(para: str, asunto: str, cuerpo: str,
                       thread_id: str | None = None) -> str:
    """Crea un BORRADOR nuevo (no se envía). Si le pasas thread_id,
    el borrador queda vinculado a ese hilo. El usuario lo revisará
    y enviará manualmente desde Gmail."""
    servicio = _servicio()
    raw = _raw_para_draft(cuerpo, para, asunto, None, None)
    cuerpo_peticion = {"message": {"raw": raw}}
    if thread_id:
        cuerpo_peticion["message"]["threadId"] = thread_id
    draft = servicio.users().drafts().create(
        userId="me", body=cuerpo_peticion).execute()
    return json.dumps({"ok": True, "draftId": draft["id"],
                       "messageId": draft["message"]["id"],
                       "threadId": draft["message"].get("threadId", thread_id),
                       "nota": "Borrador creado en Gmail — NADIE lo ha enviado"},
                      ensure_ascii=False, indent=1)


@mcp.tool(annotations=CREA)
def gmail_create_draft_reply(thread_id: str, cuerpo: str,
                             message_id: str | None = None) -> str:
    """Crea un borrador de RESPUESTA dentro de un hilo existente.
    Responde al último mensaje del hilo (o al message_id indicado),
    hacia el remitente de ese mensaje, con asunto 'Re: …' y
    cabeceras In-Reply-To/References correctas. El usuario revisa y
    envía desde Gmail."""
    servicio = _servicio()
    hilo = servicio.users().threads().get(
        userId="me", id=thread_id, format="metadata",
        metadataHeaders=["From", "To", "Subject", "Date",
                         "Message-ID", "References"]).execute()
    mensajes = hilo.get("messages", [])
    if not mensajes:
        return json.dumps({"ok": False, "error": "hilo vacío"})
    objetivo = None
    if message_id:
        objetivo = next((m for m in mensajes if m["id"] == message_id), None)
    if not objetivo:
        objetivo = mensajes[-1]  # el último mensaje del hilo
    cab = _cabeceras(objetivo)
    de = cab.get("from", "")
    # dirección del remitente (el draft va a quien envió ese mensaje)
    import re
    m = re.search(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", de)
    para = m.group(0) if m else de
    asunto = cab.get("subject", "")
    if asunto and not asunto.lower().startswith("re:"):
        asunto = f"Re: {asunto}"
    raw = _raw_para_draft(cuerpo, para, asunto,
                          cab.get("message-id"), cab.get("references"))
    cuerpo_peticion = {"message": {"raw": raw, "threadId": thread_id}}
    draft = servicio.users().drafts().create(
        userId="me", body=cuerpo_peticion).execute()
    return json.dumps({"ok": True, "draftId": draft["id"],
                       "messageId": draft["message"]["id"],
                       "threadId": thread_id,
                       "responde_a": para,
                       "nota": "Borrador de respuesta creado en el hilo — NADIE lo ha enviado"},
                      ensure_ascii=False, indent=1)


@mcp.tool(annotations=SOBRESCRIBE)
def gmail_update_draft(draft_id: str, para: str, asunto: str, cuerpo: str,
                       thread_id: str | None = None) -> str:
    """SUSTITUYE el contenido de un borrador existente (draft_id).
    Se usa cuando el panel ordena una respuesta para un hilo que ya
    tenía borrador: el texto del panel tiene prioridad. No se envía."""
    servicio = _servicio()
    raw = _raw_para_draft(cuerpo, para, asunto, None, None)
    mensaje = {"raw": raw}
    if thread_id:
        mensaje["threadId"] = thread_id
    draft = servicio.users().drafts().update(
        userId="me", id=draft_id, body={"message": mensaje}).execute()
    return json.dumps({"ok": True, "draftId": draft["id"],
                       "nota": "Borrador actualizado con el texto del panel — NADIE lo ha enviado"},
                      ensure_ascii=False, indent=1)


@mcp.tool(annotations=CREA)
def calendar_create_event(titulo: str, fecha: str, hora: str,
                          duracion_min: int = 60, ubicacion: str | None = None,
                          descripcion: str | None = None) -> str:
    """Crea una cita/evento en el calendario del asesor (solo en SU
    calendario, SIN invitados — avisar al cliente se hace con un
    borrador de Gmail, nunca Google lo envía). fecha 'AAAA-MM-DD',
    hora 'HH:MM', duracion_min minutos."""
    servicio = _servicio_calendar()
    inicio = f"{fecha}T{hora}:00"
    fin = f"{fecha}T{gcal_mod.fin_de_cita(hora, duracion_min)}:00"
    evento = {"summary": titulo, "start": {"dateTime": inicio,
                                           "timeZone": gcal_mod.ZONA_HORARIA},
              "end": {"dateTime": fin, "timeZone": gcal_mod.ZONA_HORARIA}}
    if ubicacion:
        evento["location"] = ubicacion
    if descripcion:
        evento["description"] = descripcion
    creado = servicio.events().insert(calendarId="primary", body=evento).execute()
    return json.dumps({"ok": True, "event_id": creado["id"],
                       "htmlLink": creado.get("htmlLink", "")},
                      ensure_ascii=False, indent=1)


@mcp.tool(annotations=SOLO_LECTURA)
def calendar_list_events(desde: str, hasta: str, max: int = 25) -> str:
    """Lista eventos del calendario del asesor entre dos fechas
    ('AAAA-MM-DD', inclusivas). Sirve para responder '¿qué tengo
    mañana?'. Devuelve los que el sistema conoce de él, incluidas
    las que creó a mano en Google."""
    # offset real de la zona horaria en cada fecha (+01:00 en invierno,
    # +02:00 en verano), no uno fijo
    from datetime import datetime
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(gcal_mod.ZONA_HORARIA)
    time_min = datetime.fromisoformat(f"{desde}T00:00:00").replace(tzinfo=tz)
    time_max = datetime.fromisoformat(f"{hasta}T23:59:59").replace(tzinfo=tz)
    servicio = _servicio_calendar()
    res = servicio.events().list(
        calendarId="primary", timeMin=time_min.isoformat(),
        timeMax=time_max.isoformat(), singleEvents=True,
        orderBy="startTime", maxResults=min(max, 50)).execute()
    salida = [{"id": e["id"], "titulo": e.get("summary", "(sin título)"),
               "inicio": e.get("start", {}).get("dateTime",
                                                e.get("start", {}).get("date", "")),
               "fin": e.get("end", {}).get("dateTime",
                                           e.get("end", {}).get("date", "")),
               "ubicacion": e.get("location", ""),
               "estado": e.get("status", "")}
              for e in res.get("items", [])]
    return json.dumps({"desde": desde, "hasta": hasta, "eventos": salida},
                      ensure_ascii=False, indent=1)


@mcp.tool(annotations=SOBRESCRIBE)
def calendar_update_event(event_id: str, titulo: str | None = None,
                          fecha: str | None = None, hora: str | None = None,
                          duracion_min: int | None = None,
                          ubicacion: str | None = None,
                          descripcion: str | None = None) -> str:
    """Actualiza un evento (reprogramación: pasar fecha y/o hora —
    con solo la hora se mantiene el día —; también título, ubicación,
    duración). Sin duracion_min se conserva la duración original."""
    servicio = _servicio_calendar()
    evento = servicio.events().get(calendarId="primary",
                                   eventId=event_id).execute()
    if titulo:
        evento["summary"] = titulo
    if fecha or hora:
        evento.setdefault("start", {})
        evento.setdefault("end", {})
        inicio_viejo = evento["start"].get("dateTime", "")
        # solo hora → se mantiene el día que tenía la cita
        fecha = fecha or inicio_viejo[:10] or evento["start"].get("date", "")
        if not fecha:
            return json.dumps({"ok": False, "error": "el evento no tiene fecha: "
                               "indica también 'fecha'"}, ensure_ascii=False)
        hora_vieja = inicio_viejo.split("T")[1][:5] if "T" in inicio_viejo else "09:00"
        hora_nueva = hora or hora_vieja
        dur = duracion_min
        if not dur:
            # conservar la duración ORIGINAL (fin viejo − inicio viejo);
            # % 1440 por si la cita cruzaba la medianoche
            fin_viejo = evento["end"].get("dateTime", "")
            hora_fin_vieja = fin_viejo.split("T")[1][:5] if "T" in fin_viejo else None
            if hora_fin_vieja:
                dur = ((int(hora_fin_vieja[:2]) * 60 + int(hora_fin_vieja[3:5]))
                       - (int(hora_vieja[:2]) * 60 + int(hora_vieja[3:5]))) % 1440
            dur = dur or 60
        # si era de día completo deja de serlo (Google no admite date + dateTime)
        evento["start"].pop("date", None)
        evento["end"].pop("date", None)
        evento["start"]["dateTime"] = f"{fecha}T{hora_nueva}:00"
        evento["end"]["dateTime"] = f"{fecha}T{gcal_mod.fin_de_cita(hora_nueva, dur)}:00"
        evento["start"]["timeZone"] = gcal_mod.ZONA_HORARIA
        evento["end"]["timeZone"] = gcal_mod.ZONA_HORARIA
    if ubicacion:
        evento["location"] = ubicacion
    if descripcion:
        evento["description"] = descripcion
    actualizado = servicio.events().update(
        calendarId="primary", eventId=event_id, body=evento).execute()
    return json.dumps({"ok": True, "event_id": actualizado["id"]},
                      ensure_ascii=False, indent=1)


@mcp.tool(annotations=ELIMINA)
def calendar_delete_event(event_id: str) -> str:
    """Cancela (elimina) un evento del calendario del asesor."""
    servicio = _servicio_calendar()
    servicio.events().delete(calendarId="primary", eventId=event_id).execute()
    return json.dumps({"ok": True, "event_id": event_id,
                       "nota": "evento eliminado del calendario"},
                      ensure_ascii=False, indent=1)


if __name__ == "__main__":
    mcp.run()  # transporte stdio: lo lanza el cliente IA (OpenCode, Gemini…)
