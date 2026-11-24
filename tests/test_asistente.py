# -*- coding: utf-8 -*-
"""tests/test_asistente.py — Pruebas del asistente de primer uso (Fase 7).

Todo ocurre en una carpeta temporal que imita el proyecto (datos/,
mcp-gmail/, entrada/, scripts/): nunca se tocan los datos reales.
Google se sustituye por MagicMock.
Ejecutar:  python -m unittest discover tests   (o pytest)
"""
import base64
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "dashboard"))
import memoria  # noqa: E402
import asistente  # noqa: E402
import servidor  # noqa: E402

SCOPES = asistente.gcal.SCOPES
CRED_ESCRITORIO = {"installed": {
    "client_id": "123.apps.googleusercontent.com", "client_secret": "secreto",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "redirect_uris": ["http://localhost"]}}


def b64(datos) -> str:
    if isinstance(datos, (dict, list)):
        datos = json.dumps(datos)
    if isinstance(datos, str):
        datos = datos.encode("utf-8")
    return base64.b64encode(datos).decode()


class EnCarpetaTemporal(unittest.TestCase):
    """Proyecto de mentira en una carpeta temporal."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="asistente_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "datos").mkdir()
        (self.tmp / "mcp-gmail").mkdir()
        (self.tmp / "entrada").mkdir()
        (self.tmp / ".gemini").mkdir()
        shutil.copy2(RAIZ / "datos" / "config.example.json",
                     self.tmp / "datos" / "config.example.json")
        shutil.copy2(RAIZ / ".gemini" / "settings.example.json",
                     self.tmp / ".gemini" / "settings.example.json")
        d = self.tmp / "datos"
        cambios = [
            (memoria, "DATOS", d), (memoria, "ARCHIVO", d / "archivo"),
            (asistente, "RAIZ", self.tmp),
            (asistente, "MCP_DIR", self.tmp / "mcp-gmail"),
            (asistente, "CREDENCIALES", self.tmp / "mcp-gmail" / "credentials.json"),
            (asistente, "TOKEN", self.tmp / "mcp-gmail" / "token.json"),
            (asistente, "ENTRADA", self.tmp / "entrada"),
            (asistente, "CONFIG_EJEMPLO", d / "config.example.json"),
            (asistente, "GEMINI_SETTINGS", self.tmp / ".gemini" / "settings.json"),
            (asistente, "GEMINI_EJEMPLO", self.tmp / ".gemini" / "settings.example.json"),
            (asistente, "OPENCODE_JSON", self.tmp / "opencode.json"),
        ]
        for modulo, nombre, valor in cambios:
            parche = patch.object(modulo, nombre, valor)
            parche.start()
            self.addCleanup(parche.stop)
        asistente._FLUJOS.clear()

    def config_demo(self):
        memoria.guardar("config.json", {"_comentario": asistente.AVISO_DEMO + " (demo)",
                                        "asesor": {"nombre": "Alex Ferrer"},
                                        "empresa": {"nombre": "Eleva"}})

    def token(self, scopes=SCOPES):
        asistente.TOKEN.write_text(json.dumps({"token": "t", "scopes": list(scopes)}),
                                   encoding="utf-8")


# ── Modo: primer uso / demo / real ──────────────────────────────

class Modo(EnCarpetaTemporal):
    def test_primer_uso_sin_nada(self):
        self.assertIsNone(asistente.modo_actual())
        self.assertTrue(asistente.estado()["primer_uso"])

    def test_detecta_demo_por_el_aviso_del_config(self):
        self.config_demo()
        self.assertEqual(asistente.modo_actual(), "demo")

    def test_instalacion_anterior_con_config_real_no_ve_bienvenida(self):
        memoria.guardar("config.json", {"asesor": {"nombre": "Real"}})
        self.assertEqual(asistente.modo_actual(), "real")

    def test_solo_cartera_tambien_es_real(self):
        memoria.guardar("maestro_clientes.json", {"clientes": []})
        self.assertEqual(asistente.modo_actual(), "real")

    def test_asistente_json_manda(self):
        self.config_demo()
        memoria.guardar("asistente.json", {"modo": "real"})
        self.assertEqual(asistente.modo_actual(), "real")

    def test_pasar_a_real_archiva_la_demo_sin_borrar(self):
        self.config_demo()
        memoria.guardar("seguimientos.json", {"seguimientos": [{"id": "SEG-1"}]})
        memoria.guardar_texto("meses/2026-11.md", "registro demo")
        memoria.guardar_texto("memoria/lecciones.md", "lecciones demo")
        asistente.elegir_modo("real")
        self.assertEqual(asistente.modo_actual(), "real")
        for nombre in ("config.json", "seguimientos.json", "meses/2026-11.md",
                       "memoria/lecciones.md"):
            self.assertFalse(memoria.ruta(nombre).exists(), nombre)
        archivados = [p.relative_to(memoria.ARCHIVO).as_posix()
                      for p in memoria.ARCHIVO.rglob("*") if p.is_file()]
        self.assertEqual(len(archivados), 4)
        self.assertTrue(all(a.startswith("demo_") for a in archivados))
        self.assertTrue(any(a.endswith("meses/2026-11.md") for a in archivados))

    def test_no_carga_demo_encima_de_datos_reales(self):
        memoria.guardar("config.json", {"asesor": {"nombre": "Real"}})
        with self.assertRaises(asistente.ErrorAsistente):
            asistente.elegir_modo("demo")
        self.assertEqual(memoria.cargar("config.json")["asesor"]["nombre"], "Real")

    def test_modo_desconocido(self):
        with self.assertRaises(asistente.ErrorAsistente):
            asistente.elegir_modo("otro")


# ── Paso 1: Google ──────────────────────────────────────────────

class Credencial(EnCarpetaTemporal):
    def test_guarda_credencial_de_escritorio(self):
        asistente.guardar_credencial(b64(CRED_ESCRITORIO))
        guardada = json.loads(asistente.CREDENCIALES.read_text(encoding="utf-8"))
        self.assertEqual(guardada["installed"]["client_id"], "123.apps.googleusercontent.com")
        self.assertTrue(asistente.estado_google()["credencial"])

    def test_rechaza_cliente_web(self):
        with self.assertRaisesRegex(asistente.ErrorAsistente, "escritorio"):
            asistente.guardar_credencial(b64({"web": {"client_id": "x"}}))
        self.assertFalse(asistente.CREDENCIALES.exists())

    def test_rechaza_fichero_que_no_es_json(self):
        with self.assertRaises(asistente.ErrorAsistente):
            asistente.guardar_credencial(b64("esto no es json"))
        with self.assertRaises(asistente.ErrorAsistente):
            asistente.guardar_credencial("%%%no-es-base64")
        with self.assertRaises(asistente.ErrorAsistente):
            asistente.guardar_credencial(b64({"installed": {"client_id": "x"}}))

    def test_cambiar_credencial_archiva_la_anterior(self):
        asistente.guardar_credencial(b64(CRED_ESCRITORIO))
        otra = json.loads(json.dumps(CRED_ESCRITORIO))
        otra["installed"]["client_id"] = "456.apps.googleusercontent.com"
        asistente.guardar_credencial(b64(otra))
        anteriores = list(asistente.MCP_DIR.glob("credentials_anterior_*.json"))
        self.assertEqual(len(anteriores), 1)
        self.assertIn("123.apps", anteriores[0].read_text(encoding="utf-8"))

    def test_fichero_demasiado_grande(self):
        with patch.object(asistente, "MAX_SUBIDA", 10):
            with self.assertRaisesRegex(asistente.ErrorAsistente, "grande"):
                asistente.guardar_credencial(b64(CRED_ESCRITORIO))


class EstadoGoogle(EnCarpetaTemporal):
    def test_token_con_todos_los_permisos(self):
        self.token()
        g = asistente.estado_google()
        self.assertTrue(g["conectado"])
        self.assertEqual(g["faltan_permisos"], [])

    def test_token_sin_calendario_no_cuenta_como_conectado(self):
        self.token(SCOPES[:2])
        g = asistente.estado_google()
        self.assertFalse(g["conectado"])
        self.assertEqual(g["faltan_permisos"], ["Gestionar las citas de tu calendario"])


class OAuth(EnCarpetaTemporal):
    def test_sin_credencial_no_hay_url(self):
        with self.assertRaisesRegex(asistente.ErrorAsistente, "credencial"):
            asistente.url_autorizacion()

    def test_url_de_google_con_pkce_y_vuelta_al_panel(self):
        asistente.guardar_credencial(b64(CRED_ESCRITORIO))
        url = asistente.url_autorizacion()
        self.assertTrue(url.startswith("https://accounts.google.com/"))
        self.assertIn("redirect_uri=http%3A%2F%2F127.0.0.1%3A8765%2F", url)
        self.assertIn("access_type=offline", url)
        self.assertIn("code_challenge=", url)
        self.assertNotIn("gmail.send", url)
        self.assertEqual(len(asistente._FLUJOS), 1)

    def test_usuario_cancela(self):
        with self.assertRaisesRegex(asistente.ErrorAsistente, "cancelado"):
            asistente.completar_autorizacion({"state": "x", "error": "access_denied"})

    def test_state_desconocido(self):
        with self.assertRaisesRegex(asistente.ErrorAsistente, "caducado"):
            asistente.completar_autorizacion({"state": "nada", "code": "c"})

    def _flujo(self, scopes):
        flujo = MagicMock()
        flujo.oauth2session.token = {"scope": scopes}
        flujo.credentials.to_json.return_value = '{"token": "nuevo"}'
        asistente._FLUJOS["st"] = flujo
        return flujo

    def test_faltan_casillas_no_guarda_token(self):
        self._flujo(SCOPES[:1])
        with self.assertRaisesRegex(asistente.ErrorAsistente, "Faltan permisos"):
            asistente.completar_autorizacion({"state": "st", "code": "c"})
        self.assertFalse(asistente.TOKEN.exists())

    def test_vuelta_correcta_guarda_token_y_email(self):
        flujo = self._flujo(" ".join(SCOPES))
        with patch.object(asistente, "_email_de", return_value="ana@acme.es"):
            mensaje = asistente.completar_autorizacion({"state": "st", "code": "abc"})
        flujo.fetch_token.assert_called_once_with(code="abc")
        self.assertEqual(asistente.TOKEN.read_text(encoding="utf-8"), '{"token": "nuevo"}')
        self.assertIn("ana@acme.es", mensaje)
        self.assertEqual(asistente.estado_google()["email"], "ana@acme.es")
        self.assertEqual(asistente._FLUJOS, {})   # el flujo no se reutiliza

    def test_probar_detecta_caducidad(self):
        self.token()
        gmail = MagicMock()
        gmail.users.return_value.getProfile.return_value.execute.side_effect = \
            Exception("invalid_grant: Token has been expired or revoked.")
        with patch.object(asistente.gcal, "servicio_gmail", return_value=gmail):
            with self.assertRaisesRegex(asistente.ErrorAsistente, "Prueba"):
                asistente.probar_google()


# ── Paso 2: datos ───────────────────────────────────────────────

class Datos(EnCarpetaTemporal):
    BASE = {"asesor": {"nombre": " Ana García ", "email": "Ana@Acme.es"},
            "empresa": {"nombre": "Acme S.L.", "dominios": "",
                        "contactos_corporativos": [
                            {"nombre": "Lucía", "area": "Facturación",
                             "email": "fact@acme.es", "telefono": ""},
                            {"nombre": "", "area": "", "email": "", "telefono": ""}]}}

    def test_guarda_desde_la_plantilla_y_completa_dominio(self):
        asistente.guardar_datos(self.BASE)
        config = memoria.cargar("config.json")
        self.assertNotIn("_comentario", config)
        self.assertEqual(config["asesor"]["nombre"], "Ana García")
        self.assertEqual(config["asesor"]["email"], "ana@acme.es")
        self.assertEqual(config["empresa"]["dominios"], ["acme.es"])
        self.assertEqual(len(config["empresa"]["contactos_corporativos"]), 1)
        self.assertIn("reglas_presupuestos", config)      # viene de la plantilla
        self.assertEqual(asistente.modo_actual(), "real")
        self.assertTrue(asistente.estado()["datos"]["hecho"])

    def test_conserva_el_resto_del_config_real(self):
        memoria.guardar("config.json", {"asesor": {"nombre": "X"},
                                        "objetivo_anual": {"monto": 5000}})
        asistente.guardar_datos(self.BASE)
        self.assertEqual(memoria.cargar("config.json")["objetivo_anual"]["monto"], 5000)

    def test_validaciones(self):
        for cambio, texto in [({"asesor": {"nombre": ""}}, "nombre"),
                              ({"empresa": {"nombre": ""}}, "empresa"),
                              ({"asesor": {"nombre": "A", "email": "mal"}}, "email")]:
            with self.subTest(texto=texto):
                p = json.loads(json.dumps(self.BASE))
                for k, v in cambio.items():
                    p[k].update(v)
                with self.assertRaisesRegex(asistente.ErrorAsistente, texto):
                    asistente.guardar_datos(p)

    def test_contacto_con_email_invalido(self):
        p = json.loads(json.dumps(self.BASE))
        p["empresa"]["contactos_corporativos"][0]["email"] = "sin-arroba"
        with self.assertRaisesRegex(asistente.ErrorAsistente, "Lucía"):
            asistente.guardar_datos(p)

    def test_placeholders_o_demo_no_cuentan_como_hechos(self):
        self.assertFalse(asistente.datos_hechos(
            {"asesor": {"nombre": "Tu Nombre y Apellidos"}, "empresa": {"nombre": "Acme"}}, "real"))
        self.assertFalse(asistente.datos_hechos(
            {"_comentario": asistente.AVISO_DEMO, "asesor": {"nombre": "A"},
             "empresa": {"nombre": "B"}}, "real"))


# ── Paso 3: clientes (importador real, en la carpeta temporal) ──

class Clientes(EnCarpetaTemporal):
    def setUp(self):
        super().setUp()
        shutil.copytree(RAIZ / "scripts", self.tmp / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__"))

    def excel(self, filas) -> str:
        from openpyxl import load_workbook
        libro = load_workbook(io.BytesIO(asistente.plantilla_clientes()))
        for fila in filas:
            libro["Clientes"].append(fila)
        buffer = io.BytesIO()
        libro.save(buffer)
        return b64(buffer.getvalue())

    def test_plantilla_tiene_las_columnas_del_importador(self):
        from openpyxl import load_workbook
        libro = load_workbook(io.BytesIO(asistente.plantilla_clientes()))
        cabecera = [c.value for c in libro.worksheets[0][1]]
        self.assertEqual(cabecera, ["CÓD", "NOMBRE", "DOMICILIO", "POBLACIÓN",
                                    "E-MAIL", "TELÉFONO"])

    def test_importa_la_plantilla_rellena(self):
        datos = self.excel([["1", "Comunidad Sol", "C/ Sol 1", "Valencia",
                             "admin@sol.es; otro@sol.es", "600111222"],
                            ["2", "Comunidad Luna", "C/ Luna 2", "Valencia", "", "611222333"]])
        resp = asistente.importar_clientes("mis clientes.xlsx", datos)
        self.assertEqual(resp["mensaje"], "2 clientes importados")
        self.assertEqual(resp["informe"]["con_email"], 1)
        clientes = memoria.cargar("maestro_clientes.json")["clientes"]
        self.assertEqual([c["nombre"] for c in clientes], ["Comunidad Sol", "Comunidad Luna"])
        self.assertEqual(list(asistente.ENTRADA.glob("*.xlsx")), [])   # archivado
        self.assertEqual(len(list((asistente.ENTRADA / "procesados").glob("*"))), 1)
        self.assertTrue(asistente.estado()["clientes"]["hecho"])

    def test_fichero_sin_cabecera_no_toca_la_cartera(self):
        memoria.guardar("maestro_clientes.json", {"clientes": [{"id": "CLI-0001"}]})
        with self.assertRaisesRegex(asistente.ErrorAsistente, "cabecera"):
            asistente.importar_clientes("x.csv", b64("a;b;c\n1;2;3\n"))
        self.assertEqual(memoria.cargar("maestro_clientes.json"),
                         {"clientes": [{"id": "CLI-0001"}]})
        self.assertEqual(list(asistente.ENTRADA.glob("*.csv")), [])    # no queda pendiente
        self.assertTrue((memoria.ARCHIVO / "importaciones_fallidas").exists())

    def test_extension_no_admitida(self):
        with self.assertRaisesRegex(asistente.ErrorAsistente, "Excel"):
            asistente.importar_clientes("clientes.pdf", b64("x"))

    def test_nombre_de_fichero_saneado(self):
        self.assertEqual(asistente._nombre_seguro("..\\..\\malo<>.xlsx"), "malo__.xlsx")


# ── Paso 4: IA ──────────────────────────────────────────────────

class IA(EnCarpetaTemporal):
    def test_estado_segun_programas_instalados(self):
        instalados = {"node": "/x/node", "gemini": "/x/gemini"}
        with patch.object(asistente.shutil, "which", side_effect=instalados.get):
            ia = asistente.estado_ia()
            self.assertTrue(ia["gemini"])
            self.assertFalse(ia["listo"])           # falta .gemini/settings.json
            asistente.crear_settings_gemini()
            self.assertTrue(asistente.estado_ia()["listo"])
        settings = json.loads(asistente.GEMINI_SETTINGS.read_text(encoding="utf-8"))
        self.assertNotIn("_comentario", settings)
        self.assertIn("gmail-calendar", settings["mcpServers"])

    def test_no_pisa_una_configuracion_existente(self):
        asistente.GEMINI_SETTINGS.write_text("{\"mio\": 1}", encoding="utf-8")
        self.assertIn("no se ha tocado", asistente.crear_settings_gemini())
        self.assertEqual(asistente.GEMINI_SETTINGS.read_text(encoding="utf-8"), "{\"mio\": 1}")


# ── Estado global ───────────────────────────────────────────────

class Estado(EnCarpetaTemporal):
    def test_completo_solo_con_google_y_datos(self):
        asistente.guardar_datos(Datos.BASE)
        self.assertEqual(asistente.estado()["pendientes"], ["google"])
        self.token()
        est = asistente.estado()
        self.assertEqual(est["pendientes"], [])
        self.assertTrue(est["completo"])

    def test_en_demo_no_expone_los_datos_ficticios(self):
        self.config_demo()
        est = asistente.estado()
        self.assertEqual(est["modo"], "demo")
        self.assertEqual(est["datos"]["asesor"], {})
        self.assertFalse(est["completo"])


# ── Servidor: rutas y protección ────────────────────────────────

class Servidor(unittest.TestCase):
    def manejador(self, cabeceras):
        m = servidor.Manejador.__new__(servidor.Manejador)
        m.headers = cabeceras
        return m

    def test_solo_peticiones_del_propio_panel(self):
        casos = [
            ({"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765"}, True),
            ({"Host": "localhost:8765"}, True),                       # sin Origin (curl)
            ({"Host": "127.0.0.1:8765", "Origin": "https://evil.example"}, False),
            ({"Host": "evil.example:8765", "Origin": "http://evil.example:8765"}, False),
        ]
        for cabeceras, esperado in casos:
            with self.subTest(cabeceras=cabeceras):
                self.assertIs(self.manejador(cabeceras)._peticion_local(), esperado)

    def test_rutas_post_del_asistente(self):
        with patch.object(servidor.asistente, "estado", return_value={"modo": "real"}), \
             patch.object(servidor.asistente, "guardar_datos", return_value="ok") as gd:
            resp = servidor._setup_post("/api/setup/datos", {"asesor": {}})
        gd.assert_called_once_with({"asesor": {}})
        self.assertEqual(resp, {"ok": True, "mensaje": "ok", "setup": {"modo": "real"}})
        with self.assertRaises(servidor.asistente.ErrorAsistente):
            servidor._setup_post("/api/setup/nada", {})


if __name__ == "__main__":
    unittest.main()
