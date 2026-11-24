# -*- coding: utf-8 -*-
"""asistente.py — Asistente de primer uso del Panel de Gestión (Fase 7).

Permite que una persona sin conocimientos técnicos deje el sistema
listo desde el navegador, sin consola:

  0. Bienvenida: probar con datos de ejemplo o empezar con los suyos.
  1. Google: subir su credencial OAuth (credentials.json) y pulsar
     "Conectar con Google" (OAuth en el propio panel, sin autorizar.py).
  2. Sus datos y los de su empresa (datos/config.json).
  3. Su cartera de clientes (Excel → importador de siempre).
  4. Estado del cliente de IA (Gemini CLI / OpenCode).

El servidor del panel (servidor.py) solo traduce HTTP ↔ estas
funciones. Reglas que se mantienen:
  - Ningún permiso de envío: los scopes son los de gcal.SCOPES.
  - Nada se borra sin archivar (la demo se MUEVE a datos/archivo/).
  - Las credenciales y el token se quedan en mcp-gmail/ (gitignored).
"""
from __future__ import annotations

import base64
import binascii
import io
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import memoria  # noqa: E402
import gcal  # noqa: E402

MCP_DIR = RAIZ / "mcp-gmail"
CREDENCIALES = MCP_DIR / "credentials.json"
TOKEN = gcal.TOKEN
ENTRADA = RAIZ / "entrada"
CONFIG_EJEMPLO = RAIZ / "datos" / "config.example.json"
GEMINI_SETTINGS = RAIZ / ".gemini" / "settings.json"
GEMINI_EJEMPLO = RAIZ / ".gemini" / "settings.example.json"
OPENCODE_JSON = RAIZ / "opencode.json"

ESTADO_ASISTENTE = "asistente.json"     # datos/asistente.json (gitignored)
REDIRECT_URI = "http://127.0.0.1:8765/"
AVISO_DEMO = "Estos datos son FICTICIOS"
PLACEHOLDERS = {"Tu Nombre y Apellidos", "Mi Empresa S.L.", "tu.email@miempresa.com"}
MAX_SUBIDA = 10 * 1024 * 1024           # 10 MB
EXT_CLIENTES = (".xlsx", ".xls", ".csv")

# Qué permite cada permiso, en palabras del usuario
PERMISOS_TXT = {
    "https://www.googleapis.com/auth/gmail.readonly": "Ver tus correos",
    "https://www.googleapis.com/auth/gmail.compose": "Crear borradores de correo",
    "https://www.googleapis.com/auth/calendar.events": "Gestionar las citas de tu calendario",
}

# Flujos OAuth en curso: state → Flow (guarda el PKCE entre ida y vuelta)
_FLUJOS: dict = {}


class ErrorAsistente(Exception):
    """Error con un mensaje pensado para el usuario final."""


# ── Estado persistente del asistente ────────────────────────────

def _leer() -> dict:
    return memoria.cargar(ESTADO_ASISTENTE, {}) or {}


def _escribir(**cambios) -> dict:
    datos = _leer()
    datos.update(cambios)
    datos["actualizado"] = datetime.now().isoformat(timespec="seconds")
    memoria.guardar(ESTADO_ASISTENTE, datos)
    return datos


def es_config_demo(config: dict | None) -> bool:
    return bool(config) and str(config.get("_comentario", "")).startswith(AVISO_DEMO)


def modo_actual() -> str | None:
    """'demo', 'real' o None (primer uso: no hay nada todavía).

    Si el asistente nunca se usó (instalaciones anteriores a la
    Fase 7) se deduce de los datos: la demo lleva un aviso en
    config.json; cualquier otro config o cartera es real.
    """
    modo = _leer().get("modo")
    if modo in ("demo", "real"):
        return modo
    config = memoria.cargar("config.json")
    if config is not None:
        return "demo" if es_config_demo(config) else "real"
    if memoria.ruta("maestro_clientes.json").exists():
        return "real"
    return None


# ── Paso 1: Google ──────────────────────────────────────────────

def _scopes_del_token() -> list[str]:
    try:
        datos = json.loads(TOKEN.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    scopes = datos.get("scopes") or []
    return scopes.split() if isinstance(scopes, str) else list(scopes)


def estado_google() -> dict:
    credencial_ok = False
    if CREDENCIALES.exists():
        try:
            credencial_ok = "installed" in json.loads(
                CREDENCIALES.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    conectado = TOKEN.exists()
    faltan = [PERMISOS_TXT[s] for s in gcal.SCOPES
              if conectado and s not in _scopes_del_token()]
    return {
        "credencial": credencial_ok,
        "conectado": conectado and not faltan,
        "faltan_permisos": faltan,
        "email": _leer().get("google_email"),
    }


def _decodificar(contenido_b64: str) -> bytes:
    try:
        datos = base64.b64decode(contenido_b64 or "", validate=True)
    except (binascii.Error, ValueError):
        raise ErrorAsistente("El fichero no ha llegado bien. Vuelve a intentarlo.")
    if not datos:
        raise ErrorAsistente("El fichero está vacío.")
    if len(datos) > MAX_SUBIDA:
        raise ErrorAsistente("El fichero es demasiado grande (máximo 10 MB).")
    return datos


def guardar_credencial(contenido_b64: str) -> str:
    """Valida y guarda el credentials.json descargado de Google Cloud."""
    try:
        datos = json.loads(_decodificar(contenido_b64).decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError):
        raise ErrorAsistente("Ese fichero no es el JSON que descarga Google. "
                             "Busca uno que empiece por «client_secret_…».")
    if "web" in datos:
        raise ErrorAsistente("Esa credencial es de tipo «Aplicación web». Crea otra "
                             "eligiendo «App de escritorio» como tipo de aplicación.")
    cliente = datos.get("installed") if isinstance(datos, dict) else None
    if not cliente or not cliente.get("client_id") or not cliente.get("client_secret"):
        raise ErrorAsistente("Ese fichero no es una credencial OAuth de Google. "
                             "Descarga el JSON del cliente «App de escritorio».")
    MCP_DIR.mkdir(exist_ok=True)
    if CREDENCIALES.exists():   # nada se borra sin archivar
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(CREDENCIALES, MCP_DIR / f"credentials_anterior_{marca}.json")
    CREDENCIALES.write_text(json.dumps(datos, indent=2), encoding="utf-8")
    return "Credencial guardada. Ahora pulsa «Conectar con Google»."


def url_autorizacion() -> str:
    """Prepara el flujo OAuth y devuelve la URL de Google a la que ir."""
    if not estado_google()["credencial"]:
        raise ErrorAsistente("Primero sube tu credencial de Google (paso 1).")
    from google_auth_oauthlib.flow import Flow
    flujo = Flow.from_client_secrets_file(str(CREDENCIALES), scopes=gcal.SCOPES,
                                          redirect_uri=REDIRECT_URI)
    url, state = flujo.authorization_url(access_type="offline", prompt="consent")
    _FLUJOS.clear()             # solo vale el último intento
    _FLUJOS[state] = flujo
    return url


def _email_de(credenciales) -> str | None:
    try:
        from googleapiclient.discovery import build
        gmail = build("gmail", "v1", credentials=credenciales, cache_discovery=False)
        return gmail.users().getProfile(userId="me").execute().get("emailAddress")
    except Exception:  # noqa: BLE001 — el email es informativo
        return None


def completar_autorizacion(params: dict) -> str:
    """Vuelta de Google a http://127.0.0.1:8765/?state=…&code=…"""
    if params.get("error"):
        if params["error"] == "access_denied":
            raise ErrorAsistente("Has cancelado el permiso en Google. Vuelve a "
                                 "pulsar «Conectar con Google» cuando quieras.")
        raise ErrorAsistente(f"Google ha devuelto un error: {params['error']}")
    flujo = _FLUJOS.pop(params.get("state", ""), None)
    if flujo is None or not params.get("code"):
        raise ErrorAsistente("La conexión ha caducado (¿se reinició el panel?). "
                             "Vuelve a pulsar «Conectar con Google».")
    # Google permite desmarcar permisos: los comprobamos nosotros
    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")
    try:
        flujo.fetch_token(code=params["code"])
    except Exception as exc:  # noqa: BLE001
        raise ErrorAsistente(f"Google no ha aceptado la conexión: {exc}")
    concedidos = flujo.oauth2session.token.get("scope") or []
    if isinstance(concedidos, str):
        concedidos = concedidos.split()
    faltan = [PERMISOS_TXT[s] for s in gcal.SCOPES if s not in concedidos]
    if faltan:
        raise ErrorAsistente("Faltan permisos: " + ", ".join(faltan) + ". Vuelve a "
                             "conectar y marca TODAS las casillas en la pantalla de Google.")
    credenciales = flujo.credentials
    TOKEN.write_text(credenciales.to_json(), encoding="utf-8")
    email = _email_de(credenciales)
    _escribir(google_email=email, google_conectado=datetime.now().isoformat(timespec="seconds"))
    return f"Conectado con Google como {email}" if email else "Conectado con Google"


def probar_google() -> str:
    """Comprueba que el token sigue sirviendo (detecta la caducidad de 7 días)."""
    if not TOKEN.exists():
        raise ErrorAsistente("Todavía no has conectado tu cuenta de Google.")
    try:
        perfil = gcal.servicio_gmail().users().getProfile(userId="me").execute()
    except Exception as exc:  # noqa: BLE001
        texto = str(exc)
        if "invalid_grant" in texto:
            raise ErrorAsistente("El acceso ha caducado o se ha revocado. Suele pasar "
                                 "si la app sigue en modo «Prueba» en Google Cloud: "
                                 "publícala (paso 1) y vuelve a conectar.")
        raise ErrorAsistente(f"No se pudo hablar con Google: {texto}")
    email = perfil.get("emailAddress")
    _escribir(google_email=email)
    return f"Conexión correcta con {email}"


# ── Paso 2: tus datos y tu empresa ──────────────────────────────

RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _limpio(valor) -> str:
    return str(valor or "").strip()


def datos_hechos(config: dict | None, modo: str | None) -> bool:
    if modo != "real" or not config or es_config_demo(config):
        return False
    nombre = _limpio(config.get("asesor", {}).get("nombre"))
    empresa = _limpio(config.get("empresa", {}).get("nombre"))
    return bool(nombre and empresa) and not ({nombre, empresa} & PLACEHOLDERS)


def guardar_datos(p: dict) -> str:
    asesor = p.get("asesor") or {}
    empresa = p.get("empresa") or {}
    nombre, empresa_nombre = _limpio(asesor.get("nombre")), _limpio(empresa.get("nombre"))
    if not nombre:
        raise ErrorAsistente("Escribe tu nombre y apellidos.")
    if not empresa_nombre:
        raise ErrorAsistente("Escribe el nombre de tu empresa.")
    email = _limpio(asesor.get("email")).lower()
    if email and not RE_EMAIL.match(email):
        raise ErrorAsistente(f"El email «{email}» no parece válido.")
    dominios = [d.strip().lower().lstrip("@") for d in
                re.split(r"[,;\s]+", _limpio(empresa.get("dominios")))
                if d.strip()]
    if not dominios and "@" in email:
        dominios = [email.split("@", 1)[1]]
    contactos = []
    for c in empresa.get("contactos_corporativos") or []:
        c_email = _limpio(c.get("email")).lower()
        if not (_limpio(c.get("nombre")) or c_email or _limpio(c.get("area"))):
            continue            # fila vacía del formulario
        if not RE_EMAIL.match(c_email):
            raise ErrorAsistente(f"Revisa el email del contacto «{_limpio(c.get('nombre')) or c_email}».")
        contactos.append({"nombre": _limpio(c.get("nombre")), "email": c_email,
                          "area": _limpio(c.get("area")),
                          "telefono": _limpio(c.get("telefono")) or None})

    actual = memoria.cargar("config.json")
    if actual and not es_config_demo(actual):
        config = actual
    else:
        config = json.loads(CONFIG_EJEMPLO.read_text(encoding="utf-8"))
        config.pop("_comentario", None)
        config.setdefault("objetivo_anual", {})["anno"] = datetime.now().year
    config["asesor"] = {"nombre": nombre,
                        "cargo": _limpio(asesor.get("cargo")) or "Asesor comercial",
                        "email": email}
    config.setdefault("empresa", {})
    config["empresa"].update({"nombre": empresa_nombre, "dominios": dominios,
                              "contactos_corporativos": contactos})
    memoria.guardar("config.json", config, backup=True)
    _escribir(modo="real")
    return "Datos guardados"


# ── Paso 3: clientes ────────────────────────────────────────────

def _nombre_seguro(nombre: str) -> str:
    base = re.split(r"[\\/]", nombre or "")[-1]     # igual en Windows y Linux
    base = re.sub(r"[^\w.\- ]", "_", base).strip(" .")
    return base or "clientes.xlsx"


def importar_clientes(nombre: str, contenido_b64: str) -> dict:
    """Guarda el Excel en entrada/ y ejecuta el importador + sync."""
    nombre = _nombre_seguro(nombre)
    if not nombre.lower().endswith(EXT_CLIENTES):
        raise ErrorAsistente("Sube un Excel (.xlsx o .xls) o un .csv.")
    datos = _decodificar(contenido_b64)
    ENTRADA.mkdir(exist_ok=True)
    destino = ENTRADA / nombre
    if destino.exists():        # no pisar un fichero que el usuario dejó ahí
        destino = ENTRADA / f"{destino.stem}_{datetime.now():%H%M%S}{destino.suffix}"
    destino.write_bytes(datos)

    def ejecutar(*args) -> subprocess.CompletedProcess:
        entorno = dict(os.environ, PYTHONIOENCODING="utf-8")
        return subprocess.run([sys.executable, *args], cwd=str(RAIZ), env=entorno,
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=300)

    imp = ejecutar("scripts/importar_clientes.py", str(destino))
    salida = (imp.stdout + imp.stderr).strip()
    if imp.returncode != 0 or destino.exists():
        if destino.exists():    # no se importó: no dejarlo pendiente en entrada/
            memoria.archivar(destino, "importaciones_fallidas")
        lineas = [l for l in salida.splitlines() if "ERROR" in l or "Error" in l]
        raise ErrorAsistente("No se ha podido importar el fichero. "
                             + (lineas[-1].replace("[ERROR]", "").strip() if lineas else
                                "Comprueba que usa la plantilla (columnas CÓD, NOMBRE, "
                                "DOMICILIO, POBLACIÓN, E-MAIL, TELÉFONO)."))
    sync = ejecutar("scripts/sync.py")
    informe = memoria.cargar("informe_importacion.json", {})
    _escribir(modo="real")
    return {
        "mensaje": f"{informe.get('total_registros', 0)} clientes importados",
        "informe": _resumen_informe(informe),
        "aviso_excel": None if sync.returncode == 0 else
        "Los clientes se importaron, pero no se pudo regenerar el Excel de gestión.",
    }


def _resumen_informe(informe: dict) -> dict | None:
    if not informe:
        return None
    return {k: informe.get(k) for k in ("fichero", "importado", "total_registros",
                                       "con_email", "con_telefono", "sin_email",
                                       "sin_telefono")} | {
        "duplicados": len(informe.get("posibles_duplicados") or [])}


def plantilla_clientes() -> bytes:
    """Excel vacío con las columnas que entiende el importador."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Clientes"
    cabecera = ["CÓD", "NOMBRE", "DOMICILIO", "POBLACIÓN", "E-MAIL", "TELÉFONO"]
    hoja.append(cabecera)
    for celda, ancho in zip(hoja[1], (10, 36, 36, 20, 34, 18)):
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor="1F4E78")
        hoja.column_dimensions[celda.column_letter].width = ancho
    hoja.freeze_panes = "A2"
    ayuda = libro.create_sheet("Cómo rellenarla")
    for fila in (
        ["Una fila por cliente, empezando en la fila 2 de la hoja «Clientes»."],
        ["CÓD: tu código interno del cliente (puede quedar vacío)."],
        ["NOMBRE: obligatorio. Filas sin nombre se ignoran."],
        ["E-MAIL y TELÉFONO: si hay varios, sepáralos con «;»."],
        ["No cambies los títulos de la fila 1 ni el orden de las hojas."],
    ):
        ayuda.append(fila)
    ayuda.column_dimensions["A"].width = 80
    buffer = io.BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


# ── Paso 4: cliente de IA ───────────────────────────────────────

def estado_ia() -> dict:
    gemini = bool(shutil.which("gemini"))
    opencode = bool(shutil.which("opencode"))
    return {
        "node": bool(shutil.which("node")),
        "gemini": gemini,
        "gemini_configurado": GEMINI_SETTINGS.exists(),
        "opencode": opencode,
        "opencode_configurado": OPENCODE_JSON.exists(),
        "listo": (gemini and GEMINI_SETTINGS.exists()) or (opencode and OPENCODE_JSON.exists()),
    }


def crear_settings_gemini() -> str:
    if GEMINI_SETTINGS.exists():
        return "La configuración de Gemini CLI ya existía; no se ha tocado."
    if not GEMINI_EJEMPLO.exists():
        raise ErrorAsistente("No encuentro .gemini/settings.example.json.")
    datos = json.loads(GEMINI_EJEMPLO.read_text(encoding="utf-8"))
    datos.pop("_comentario", None)
    GEMINI_SETTINGS.write_text(json.dumps(datos, indent=2, ensure_ascii=False),
                               encoding="utf-8")
    return "Configuración de Gemini CLI creada (.gemini/settings.json)."


# ── Bienvenida: demo o datos reales ─────────────────────────────

FICHEROS_DEMO = ("config.json", "maestro_clientes.json", "seguimientos.json",
                 "presupuestos.json", "programaciones.json", "ventas.json",
                 "citas.json", "identidad.json", "informe_importacion.json")


def elegir_modo(modo: str) -> str:
    actual = modo_actual()
    if modo == "demo":
        if actual == "real":
            raise ErrorAsistente("Ya tienes tus propios datos: no se cargará la demo "
                                 "para no mezclarlos.")
        if actual != "demo":
            proc = subprocess.run([sys.executable, "scripts/demo_data.py", "--solo"],
                                  cwd=str(RAIZ), capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=120,
                                  env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            if proc.returncode != 0:
                raise ErrorAsistente("No se pudieron generar los datos de ejemplo.")
        _escribir(modo="demo")
        return "Datos de ejemplo cargados: explora el panel con total libertad."
    if modo == "real":
        if actual == "demo":
            _archivar_demo()
        _escribir(modo="real")
        return "Empecemos con tus datos."
    raise ErrorAsistente(f"Modo desconocido: {modo}")


def _archivar_demo() -> Path:
    """Mueve los datos de ejemplo a datos/archivo/demo_<fecha>/ (no se borran)."""
    destino = memoria.ARCHIVO / f"demo_{datetime.now():%Y%m%d_%H%M%S}"
    destino.mkdir(parents=True, exist_ok=True)
    rutas = [memoria.ruta(n) for n in FICHEROS_DEMO]
    rutas += list(memoria.ruta("meses").glob("*.md")) if memoria.ruta("meses").exists() else []
    rutas.append(memoria.ruta("memoria/lecciones.md"))
    for fich in rutas:
        if fich.exists():
            rel = fich.relative_to(memoria.DATOS)
            (destino / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(fich), str(destino / rel))
    return destino


# ── Resumen para el panel ───────────────────────────────────────

def estado() -> dict:
    modo = modo_actual()
    config = memoria.cargar("config.json")
    maestro = memoria.cargar("maestro_clientes.json", {"clientes": []}) or {"clientes": []}
    google = estado_google()
    datos_ok = datos_hechos(config, modo)
    clientes = [] if modo == "demo" else maestro.get("clientes", [])
    pendientes = []
    if not google["conectado"]:
        pendientes.append("google")
    if not datos_ok:
        pendientes.append("datos")
    asesor = (config or {}).get("asesor", {}) if not es_config_demo(config) else {}
    empresa = (config or {}).get("empresa", {}) if not es_config_demo(config) else {}
    return {
        "modo": modo,
        "primer_uso": modo is None,
        "google": google,
        "datos": {"hecho": datos_ok, "asesor": asesor, "empresa": empresa},
        "clientes": {"hecho": bool(clientes), "total": len(clientes),
                     "informe": _resumen_informe(
                         memoria.cargar("informe_importacion.json", {}) or {})
                     if clientes else None},
        "ia": estado_ia(),
        "pendientes": pendientes,
        "completo": modo == "real" and not pendientes,
    }
