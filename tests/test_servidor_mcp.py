# -*- coding: utf-8 -*-
"""tests/test_servidor_mcp.py — Pruebas del servidor MCP de Gmail/Calendar.

Sin credenciales reales: los servicios de Google se sustituyen por
MagicMock y las herramientas se invocan por su nombre a través de
FastMCP (igual que lo haría un cliente IA).
Ejecutar:  python -m unittest discover tests   (o pytest)
"""
import asyncio
import base64
import email
import email.policy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "mcp-gmail"))
import servidor_mcp as srv  # noqa: E402

ARCHIVO_SERVIDOR = RAIZ / "mcp-gmail" / "servidor_mcp.py"

# Anotaciones esperadas: (readOnly, destructive, idempotent, openWorld)
ESPERADAS = {
    "gmail_list_unread":        (True, False, True, True),
    "gmail_search":             (True, False, True, True),
    "gmail_get_thread":         (True, False, True, True),
    "gmail_get_message":        (True, False, True, True),
    "gmail_list_drafts":        (True, False, True, True),
    "calendar_list_events":     (True, False, True, True),
    "gmail_create_draft":       (False, False, False, True),
    "gmail_create_draft_reply": (False, False, False, True),
    "calendar_create_event":    (False, False, False, True),
    "gmail_update_draft":       (False, True, True, True),
    "calendar_update_event":    (False, True, True, True),
    "calendar_delete_event":    (False, True, True, True),
}


# ── Utilidades de prueba ────────────────────────────────────────

def llamar(nombre: str, **args) -> dict:
    """Invoca una herramienta por su nombre y devuelve su JSON."""
    res = asyncio.run(srv.mcp.call_tool(nombre, args))
    if isinstance(res, tuple):  # mcp>=1.10 devuelve (contenido, estructurado)
        res = res[0]
    return json.loads(res[0].text)


def b64(texto: str) -> str:
    return base64.urlsafe_b64encode(texto.encode("utf-8")).decode()


def cabeceras(**kw) -> list:
    nombres = {"from_": "From", "to": "To", "subject": "Subject",
               "date": "Date", "message_id": "Message-ID",
               "references": "References"}
    return [{"name": nombres[k], "value": v} for k, v in kw.items()]


def mime_de_raw(raw: str):
    return email.message_from_bytes(base64.urlsafe_b64decode(raw),
                                    policy=email.policy.default)


class ConGmail(unittest.TestCase):
    """Base: sustituye srv._servicio por un MagicMock."""

    def setUp(self):
        self.gmail = MagicMock(name="gmail")
        parche = patch.object(srv, "_servicio", return_value=self.gmail)
        parche.start()
        self.addCleanup(parche.stop)
        self.users = self.gmail.users.return_value
        self.messages = self.users.messages.return_value
        self.threads = self.users.threads.return_value
        self.drafts = self.users.drafts.return_value

    def tearDown(self):
        # regla de oro: ninguna prueba debe acabar llamando a send
        self.assertFalse(self.messages.send.called)
        self.assertFalse(self.drafts.send.called)


class ConCalendar(unittest.TestCase):
    """Base: sustituye srv._servicio_calendar por un MagicMock."""

    def setUp(self):
        self.cal = MagicMock(name="calendar")
        parche = patch.object(srv, "_servicio_calendar", return_value=self.cal)
        parche.start()
        self.addCleanup(parche.stop)
        self.events = self.cal.events.return_value


# ── Registro y regla de oro ─────────────────────────────────────

class Registro(unittest.TestCase):
    def test_doce_herramientas_con_sus_anotaciones(self):
        herramientas = asyncio.run(srv.mcp.list_tools())
        por_nombre = {h.name: h for h in herramientas}
        self.assertEqual(set(por_nombre), set(ESPERADAS))
        self.assertEqual(len(herramientas), 12)
        for nombre, (ro, destr, idem, abierto) in ESPERADAS.items():
            with self.subTest(herramienta=nombre):
                a = por_nombre[nombre].annotations
                self.assertIsNotNone(a)
                self.assertIs(a.readOnlyHint, ro)
                self.assertIs(a.destructiveHint, destr)
                self.assertIs(a.idempotentHint, idem)
                self.assertIs(a.openWorldHint, abierto)


class ReglaDeOro(unittest.TestCase):
    def test_el_servidor_nunca_envia_correos(self):
        codigo = ARCHIVO_SERVIDOR.read_text(encoding="utf-8")
        self.assertNotIn(".send(", codigo)


# ── Gmail: lectura ──────────────────────────────────────────────

class ListUnread(ConGmail):
    def test_limite_50_y_resumen(self):
        self.messages.list.return_value.execute.return_value = {
            "messages": [{"id": "m1"}]}
        self.messages.get.return_value.execute.return_value = {
            "id": "m1", "threadId": "t1", "snippet": "hola",
            "payload": {"headers": cabeceras(from_="Ana <ana@x.com>",
                                             subject="Presupuesto")}}
        datos = llamar("gmail_list_unread", max=200)
        kw = self.messages.list.call_args.kwargs
        self.assertEqual(kw["maxResults"], 50)
        self.assertIn("is:unread", kw["q"])
        self.assertEqual(datos["total_no_leidos_listados"], 1)
        m = datos["mensajes"][0]
        self.assertEqual((m["id"], m["threadId"], m["asunto"], m["de"]),
                         ("m1", "t1", "Presupuesto", "Ana <ana@x.com>"))
        self.assertEqual(self.messages.get.call_args.kwargs["format"], "metadata")


class Search(ConGmail):
    def test_pasa_la_consulta_y_limita_a_50(self):
        self.messages.list.return_value.execute.return_value = {}
        datos = llamar("gmail_search", consulta="from:ana@x.com", max=99)
        kw = self.messages.list.call_args.kwargs
        self.assertEqual(kw["q"], "from:ana@x.com")
        self.assertEqual(kw["maxResults"], 50)
        self.assertEqual(datos, {"consulta": "from:ana@x.com",
                                 "resultados": 0, "mensajes": []})

    def test_respeta_max_menor(self):
        self.messages.list.return_value.execute.return_value = {}
        llamar("gmail_search", consulta="x", max=5)
        self.assertEqual(self.messages.list.call_args.kwargs["maxResults"], 5)


class GetThread(ConGmail):
    def test_convierte_html_a_texto(self):
        html = ("<html><style>p{color:red}</style><p>Hola&nbsp;Ana</p>"
                "L&iacute;nea 1<br>L&iacute;nea 2<script>alert(1)</script></html>")
        self.threads.get.return_value.execute.return_value = {
            "id": "t1", "messages": [{
                "id": "m1", "labelIds": ["INBOX"],
                "payload": {"headers": cabeceras(subject="Hola"),
                            "mimeType": "multipart/alternative",
                            "parts": [{"mimeType": "text/html",
                                       "body": {"data": b64(html)}}]}}]}
        datos = llamar("gmail_get_thread", thread_id="t1")
        cuerpo = datos["mensajes"][0]["cuerpo"]
        self.assertNotIn("<", cuerpo)
        self.assertNotIn("alert", cuerpo)
        self.assertNotIn("color", cuerpo)
        self.assertIn("Hola\xa0Ana", cuerpo)
        self.assertIn("Línea 1\nLínea 2", cuerpo)
        self.assertEqual(datos["threadId"], "t1")
        self.assertEqual(datos["mensajes"][0]["etiquetas"], ["INBOX"])
        self.assertEqual(self.threads.get.call_args.kwargs["format"], "full")


class GetMessage(ConGmail):
    def test_prefiere_texto_plano_en_partes_anidadas(self):
        self.messages.get.return_value.execute.return_value = {
            "id": "m1", "threadId": "t1",
            "payload": {"headers": cabeceras(subject="S"),
                        "mimeType": "multipart/mixed",
                        "parts": [{"mimeType": "multipart/alternative",
                                   "body": {},
                                   "parts": [
                                       {"mimeType": "text/html",
                                        "body": {"data": b64("<b>HTML</b>")}},
                                       {"mimeType": "text/plain",
                                        "body": {"data": b64("Texto plano")}}]}]}}
        datos = llamar("gmail_get_message", message_id="m1")
        self.assertEqual(datos["cuerpo"], "Texto plano")
        self.assertEqual(self.messages.get.call_args.kwargs["id"], "m1")

    def test_sin_cuerpo(self):
        self.messages.get.return_value.execute.return_value = {
            "id": "m1", "payload": {"headers": []}}
        datos = llamar("gmail_get_message", message_id="m1")
        self.assertEqual(datos["cuerpo"], "(mensaje sin cuerpo de texto)")
        self.assertEqual(datos["asunto"], "(sin asunto)")


class ListDrafts(ConGmail):
    def test_pide_cabeceras_si_faltan_y_limita_a_50(self):
        self.drafts.list.return_value.execute.return_value = {
            "drafts": [{"id": "d1", "message": {"id": "m1"}}]}
        self.drafts.get.return_value.execute.return_value = {
            "message": {"id": "m1", "threadId": "t1",
                        "payload": {"headers": cabeceras(subject="Borrador X",
                                                         to="ana@x.com")}}}
        datos = llamar("gmail_list_drafts", max=80)
        self.assertEqual(self.drafts.list.call_args.kwargs["maxResults"], 50)
        self.assertEqual(self.drafts.get.call_args.kwargs,
                         {"userId": "me", "id": "d1", "format": "full"})
        self.assertEqual(datos["borradores"], 1)
        d = datos["lista"][0]
        self.assertEqual((d["draftId"], d["asunto"], d["para"]),
                         ("d1", "Borrador X", "ana@x.com"))


# ── Gmail: borradores ───────────────────────────────────────────

class CreateDraft(ConGmail):
    def test_crea_borrador_vinculado_al_hilo(self):
        self.drafts.create.return_value.execute.return_value = {
            "id": "d1", "message": {"id": "m9", "threadId": "t1"}}
        datos = llamar("gmail_create_draft", para="ana@x.com",
                       asunto="Presupuesto", cuerpo="Adjunto precio.",
                       thread_id="t1")
        cuerpo = self.drafts.create.call_args.kwargs["body"]
        self.assertEqual(cuerpo["message"]["threadId"], "t1")
        mime = mime_de_raw(cuerpo["message"]["raw"])
        self.assertEqual(mime["To"], "ana@x.com")
        self.assertEqual(mime["Subject"], "Presupuesto")
        self.assertIsNone(mime["In-Reply-To"])
        self.assertIn("Adjunto precio.", mime.get_content())
        self.assertTrue(datos["ok"])
        self.assertEqual(datos["draftId"], "d1")

    def test_sin_hilo_no_manda_threadId(self):
        self.drafts.create.return_value.execute.return_value = {
            "id": "d1", "message": {"id": "m9"}}
        llamar("gmail_create_draft", para="a@x.com", asunto="A", cuerpo="B")
        cuerpo = self.drafts.create.call_args.kwargs["body"]
        self.assertNotIn("threadId", cuerpo["message"])


class CreateDraftReply(ConGmail):
    def _hilo(self, asunto="Presupuesto"):
        self.threads.get.return_value.execute.return_value = {"messages": [
            {"id": "m1", "payload": {"headers": cabeceras(
                from_="Yo <yo@empresa.com>", subject=asunto,
                message_id="<uno@mail>")}},
            {"id": "m2", "payload": {"headers": cabeceras(
                from_="Laura Ruiz <laruiz@gmail.com>", subject=f"Re: {asunto}",
                message_id="<dos@mail>", references="<uno@mail>")}},
        ]}
        self.drafts.create.return_value.execute.return_value = {
            "id": "d1", "message": {"id": "m3"}}

    def test_responde_al_ultimo_mensaje_del_hilo(self):
        self._hilo()
        datos = llamar("gmail_create_draft_reply", thread_id="t1",
                       cuerpo="Gracias, Laura.")
        cuerpo = self.drafts.create.call_args.kwargs["body"]
        self.assertEqual(cuerpo["message"]["threadId"], "t1")
        mime = mime_de_raw(cuerpo["message"]["raw"])
        self.assertEqual(mime["Subject"], "Re: Presupuesto")  # sin "Re: Re:"
        self.assertEqual(mime["In-Reply-To"], "<dos@mail>")
        self.assertEqual(mime["References"], "<uno@mail>")
        self.assertEqual(mime["To"], "laruiz@gmail.com")
        self.assertEqual(datos["responde_a"], "laruiz@gmail.com")

    def test_message_id_concreto_y_prefijo_re(self):
        self._hilo(asunto="Cita martes")
        llamar("gmail_create_draft_reply", thread_id="t1", cuerpo="Ok",
               message_id="m1")
        mime = mime_de_raw(self.drafts.create.call_args.kwargs["body"]["message"]["raw"])
        self.assertEqual(mime["Subject"], "Re: Cita martes")
        self.assertEqual(mime["In-Reply-To"], "<uno@mail>")
        self.assertEqual(mime["To"], "yo@empresa.com")

    def test_hilo_vacio(self):
        self.threads.get.return_value.execute.return_value = {"messages": []}
        datos = llamar("gmail_create_draft_reply", thread_id="t1", cuerpo="x")
        self.assertFalse(datos["ok"])
        self.assertFalse(self.drafts.create.called)


class UpdateDraft(ConGmail):
    def test_sustituye_el_borrador_indicado(self):
        self.drafts.update.return_value.execute.return_value = {"id": "d7"}
        datos = llamar("gmail_update_draft", draft_id="d7", para="ana@x.com",
                       asunto="Nuevo asunto", cuerpo="Texto del panel",
                       thread_id="t1")
        kw = self.drafts.update.call_args.kwargs
        self.assertEqual(kw["id"], "d7")
        self.assertEqual(kw["body"]["message"]["threadId"], "t1")
        mime = mime_de_raw(kw["body"]["message"]["raw"])
        self.assertEqual(mime["Subject"], "Nuevo asunto")
        self.assertIn("Texto del panel", mime.get_content())
        self.assertFalse(self.drafts.create.called)
        self.assertEqual(datos["draftId"], "d7")


# ── Calendar ────────────────────────────────────────────────────

class CreateEvent(ConCalendar):
    def test_sin_invitados_y_con_duracion(self):
        self.events.insert.return_value.execute.return_value = {
            "id": "e1", "htmlLink": "https://cal/e1"}
        datos = llamar("calendar_create_event", titulo="Visita Ana",
                       fecha="2026-12-01", hora="10:00", duracion_min=90,
                       ubicacion="Oficina")
        kw = self.events.insert.call_args.kwargs
        self.assertEqual(kw["calendarId"], "primary")
        evento = kw["body"]
        self.assertNotIn("attendees", evento)
        self.assertEqual(evento["start"]["dateTime"], "2026-12-01T10:00:00")
        self.assertEqual(evento["end"]["dateTime"], "2026-12-01T11:30:00")
        self.assertEqual(evento["start"]["timeZone"], "Europe/Madrid")
        self.assertEqual(evento["location"], "Oficina")
        self.assertNotIn("description", evento)
        self.assertEqual(datos["event_id"], "e1")


class ListEvents(ConCalendar):
    def test_rango_limite_y_formato(self):
        self.events.list.return_value.execute.return_value = {"items": [
            {"id": "e1", "start": {"dateTime": "2026-12-01T10:00:00+01:00"},
             "end": {"dateTime": "2026-12-01T11:00:00+01:00"}},
            {"id": "e2", "summary": "Festivo", "start": {"date": "2026-12-08"},
             "end": {"date": "2026-12-09"}}]}
        datos = llamar("calendar_list_events", desde="2026-12-01",
                       hasta="2026-12-08", max=500)
        kw = self.events.list.call_args.kwargs
        self.assertEqual(kw["calendarId"], "primary")
        self.assertEqual(kw["maxResults"], 50)
        self.assertTrue(kw["timeMin"].startswith("2026-12-01T00:00:00"))
        self.assertTrue(kw["timeMax"].startswith("2026-12-08T23:59:59"))
        self.assertTrue(kw["singleEvents"])
        e1, e2 = datos["eventos"]
        self.assertEqual(e1["titulo"], "(sin título)")
        self.assertEqual(e2["inicio"], "2026-12-08")


class UpdateEvent(ConCalendar):
    def _evento(self, inicio, fin):
        self.events.get.return_value.execute.return_value = {
            "id": "e1", "summary": "Cita",
            "start": {"dateTime": inicio, "timeZone": "Europe/Madrid"},
            "end": {"dateTime": fin, "timeZone": "Europe/Madrid"}}
        self.events.update.return_value.execute.return_value = {"id": "e1"}

    def _enviado(self):
        kw = self.events.update.call_args.kwargs
        self.assertEqual((kw["calendarId"], kw["eventId"]), ("primary", "e1"))
        return kw["body"]

    def test_mover_conserva_la_duracion_original(self):
        # bug corregido: 10:00–11:00 movida a las 12:00 quedaba 12:00–11:00
        self._evento("2026-12-01T10:00:00+01:00", "2026-12-01T11:00:00+01:00")
        llamar("calendar_update_event", event_id="e1",
               fecha="2026-12-01", hora="12:00")
        ev = self._enviado()
        self.assertEqual(ev["start"]["dateTime"], "2026-12-01T12:00:00")
        self.assertEqual(ev["end"]["dateTime"], "2026-12-01T13:00:00")

    def test_duracion_que_cruza_medianoche(self):
        self._evento("2026-12-01T23:30:00+01:00", "2026-12-02T00:15:00+01:00")
        llamar("calendar_update_event", event_id="e1",
               fecha="2026-12-03", hora="20:00")
        ev = self._enviado()
        self.assertEqual(ev["start"]["dateTime"], "2026-12-03T20:00:00")
        self.assertEqual(ev["end"]["dateTime"], "2026-12-03T20:45:00")

    def test_solo_fecha_mantiene_hora_y_duracion(self):
        self._evento("2026-12-01T09:30:00+01:00", "2026-12-01T10:15:00+01:00")
        llamar("calendar_update_event", event_id="e1", fecha="2026-12-05")
        ev = self._enviado()
        self.assertEqual(ev["start"]["dateTime"], "2026-12-05T09:30:00")
        self.assertEqual(ev["end"]["dateTime"], "2026-12-05T10:15:00")

    def test_duracion_explicita_manda(self):
        self._evento("2026-12-01T10:00:00+01:00", "2026-12-01T11:00:00+01:00")
        llamar("calendar_update_event", event_id="e1", fecha="2026-12-01",
               hora="16:00", duracion_min=30)
        self.assertEqual(self._enviado()["end"]["dateTime"], "2026-12-01T16:30:00")

    def test_sin_fin_previo_usa_60(self):
        self.events.get.return_value.execute.return_value = {"id": "e1"}
        self.events.update.return_value.execute.return_value = {"id": "e1"}
        llamar("calendar_update_event", event_id="e1", fecha="2026-12-01",
               hora="08:00")
        self.assertEqual(self._enviado()["end"]["dateTime"], "2026-12-01T09:00:00")

    def test_solo_titulo_no_toca_fechas(self):
        self._evento("2026-12-01T10:00:00+01:00", "2026-12-01T11:00:00+01:00")
        llamar("calendar_update_event", event_id="e1", titulo="Cita movida")
        ev = self._enviado()
        self.assertEqual(ev["summary"], "Cita movida")
        self.assertEqual(ev["start"]["dateTime"], "2026-12-01T10:00:00+01:00")


class DeleteEvent(ConCalendar):
    def test_borra_en_el_calendario_primary(self):
        datos = llamar("calendar_delete_event", event_id="e1")
        self.events.delete.assert_called_once_with(calendarId="primary",
                                                   eventId="e1")
        self.events.delete.return_value.execute.assert_called_once()
        self.assertEqual(datos, {"ok": True, "event_id": "e1",
                                 "nota": "evento eliminado del calendario"})


if __name__ == "__main__":
    unittest.main()
