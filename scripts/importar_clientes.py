# -*- coding: utf-8 -*-
"""importar_clientes.py — Importa el Excel de clientes.

Proceso:
  1. Busca el fichero (.xls/.xlsx/.csv) más reciente en `entrada/`.
  2. Detecta la fila de cabecera (CÓD | NOMBRE | DOMICILIO | …).
  3. Verifica el offset de columnas CONTRA LOS DATOS (en el fichero
     real la cabecera "POBLACION" cubre también la columna del CP).
  4. Limpia emails y teléfonos (varios por celda, con notas, o
     texto no-email como "PLATAFORMA CONECTA" / "CORREO POSTAL").
  5. Detecta posibles duplicados (mismo email o misma dirección).
  6. Control de calidad: si no se extrae ningún email/teléfono,
     ABORTA sin tocar la memoria ni archivar el fichero.
  7. Archiva la versión previa del maestro en `datos/archivo/`,
     escribe maestro_clientes.json + identidad.json +
     informe_importacion.json y mueve el fichero a `entrada/procesados/`.

Uso:  .venv\\Scripts\\python.exe scripts\\importar_clientes.py
"""
from __future__ import annotations

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import memoria  # noqa: E402

ENTRADA = RAIZ / "entrada"
PROCESADOS = ENTRADA / "procesados"

RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# teléfono: dígito inicial y 8-11 dígitos más, admitiendo espacios
# simples como separador interior ('96 153 72 13'); las letras lo
# cortan ('AMPARO 601013838' → solo el número).
RE_TEL = re.compile(r"\d(?:[ .]?\d){8,11}")
RE_CP = re.compile(r"^\d{5}$")

NO_EMAIL_CONOCIDOS = [
    ("plataforma conecta", "usa plataforma Conecta (sin email directo)"),
    ("conecta", "usa plataforma Conecta (sin email directo)"),
    ("correo postal", "prefiere correo postal"),
    ("correo ordinario", "prefiere correo ordinario"),
]


# ── Normalización ────────────────────────────────────────────────

def extraer_emails(texto: str) -> tuple[list[str], list[str]]:
    """Devuelve (emails, notas). Una celda puede tener varios emails
    y texto no-email que se convierte en nota."""
    if not texto:
        return [], []
    texto = str(texto).strip()
    emails = [m.group(0).lower() for m in RE_EMAIL.finditer(texto)]
    notas: list[str] = []
    resto = RE_EMAIL.sub(" ", texto).strip().rstrip(";,. ")
    if resto:
        bajo = resto.lower()
        nota = next((n for clave, n in NO_EMAIL_CONOCIDOS if clave in bajo), None)
        if nota:
            notas.append(nota)
        else:
            notas.append(f"texto adicional: «{resto}»")
    return list(dict.fromkeys(emails)), notas


def extraer_telefonos(texto: str) -> tuple[list[str], list[str]]:
    """Devuelve (telefonos, notas). Extrae números de 9-12 dígitos,
    admitiendo espacios/puntos interiores, sin mezclar dos números
    separados por guión o barra."""
    if not texto:
        return [], []
    texto = str(texto)
    telefonos: list[str] = []
    # dividir por separadores fuertes para no unir dos números
    for parte in re.split(r"\s*[-/]\s*", texto):
        for m in RE_TEL.finditer(parte):
            digitos = re.sub(r"\D", "", m.group(0))
            if 9 <= len(digitos) <= 12:
                telefonos.append(digitos)
    notas: list[str] = []
    resto = re.sub(r"\d", " ", texto)
    resto = re.sub(r"[;,.:\-/\s]+", " ", resto).strip()
    # quitar palabras de conteo que sobran (números ya extraídos)
    if resto:
        notas.append(f"en teléfono: {resto}")
    return list(dict.fromkeys(telefonos)), notas


def limpiar(texto) -> str:
    if texto is None:
        return ""
    return re.sub(r"\s+", " ", str(texto)).strip()


def a_texto(valor) -> str:
    """xlrd/openpyxl pueden devolver floats para celdas numéricas."""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor) if valor is not None else ""


# ── Lectura del fichero ─────────────────────────────────────────

def localizar_fichero() -> Path | None:
    for patron in ("*.xls", "*.xlsx", "*.csv"):
        candidatos = [f for f in ENTRADA.glob(patron) if f.is_file()]
        if candidatos:
            return max(candidatos, key=lambda f: f.stat().st_mtime)
    return None


def leer_filas(fich: Path) -> list[list[str]]:
    if fich.suffix.lower() == ".xls":
        import xlrd
        libro = xlrd.open_workbook(str(fich))
        hoja = libro.sheet_by_index(0)
        return [[a_texto(hoja.cell_value(r, c)) for c in range(hoja.ncols)]
                for r in range(hoja.nrows)]
    if fich.suffix.lower() == ".xlsx":
        from openpyxl import load_workbook
        libro = load_workbook(str(fich), data_only=True)
        hoja = libro.active
        return [["" if c is None else a_texto(c) for c in fila]
                for fila in hoja.iter_rows(values_only=True)]
    import csv
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(fich, encoding=encoding, newline="") as fh:
                return list(csv.reader(fh, delimiter=";"))
        except UnicodeDecodeError:
            continue
    raise ValueError(f"No se pudo leer el CSV {fich}")


def detectar_cabecera(filas: list[list[str]]) -> int:
    for i, fila in enumerate(filas[:10]):
        unidos = " ".join(fila).lower()
        if ("cód" in unidos or "cod" in unidos) and "nombre" in unidos:
            return i
    raise ValueError("No se encontró la fila de cabecera (CÓD | NOMBRE | …)")


def buscar_columna(cab: list[str], fragmento: str) -> int:
    frag = fragmento.lower()
    for j, celda in enumerate(cab):
        if frag in celda.lower():
            return j
    return -1


def columnas_con_datos(filas: list[list[str]], idx: int) -> dict[str, int]:
    """Localiza columnas por cabecera y las verifica contra los
    datos: si la columna de 'e-mail' guarda códigos postales, todo
    el bloque derecho está desplazado una columna (caso del fichero
    real: la cabecera POBLACION cubre CP + POBLACIÓN)."""
    cab = filas[idx]
    colmap = {
        "cod": buscar_columna(cab, "cód") if buscar_columna(cab, "cód") >= 0
        else buscar_columna(cab, "cod"),
        "nombre": buscar_columna(cab, "nombre"),
        "domicilio": buscar_columna(cab, "domicilio"),
        "poblacion": buscar_columna(cab, "poblaci"),
        "email": buscar_columna(cab, "e-mail") if buscar_columna(cab, "e-mail") >= 0
        else buscar_columna(cab, "mail"),
        "telefono": buscar_columna(cab, "tel"),
    }

    muestra = [f for f in filas[idx + 1: idx + 15] if any(c.strip() for c in f)]
    if colmap["poblacion"] >= 0 and colmap["email"] >= 0 and colmap["telefono"] >= 0 and muestra:
        # en el fichero real, la columna bajo la cabecera 'POBLACION'
        # guarda los códigos postales → el bloque derecho va desplazado
        es_cp = sum(1 for f in muestra if RE_CP.match(limpiar(f[colmap["poblacion"]])))
        if es_cp >= len(muestra) * 0.7:
            print("[i] Detectado offset de columnas: CP oculto bajo 'POBLACION'")
            colmap["cp"] = colmap["poblacion"]
            colmap["poblacion"] = colmap["email"]
            colmap["email"] = colmap["telefono"]
            colmap["telefono"] = colmap["cp"] + 3
    else:
        colmap["cp"] = -1
    return colmap


# ── Construcción del maestro ────────────────────────────────────

def fila_a_cliente(num: int, fila: dict) -> dict:
    emails, notas_email = extraer_emails(fila.get("email", ""))
    telefonos, notas_tel = extraer_telefonos(fila.get("telefono", ""))
    fichas = [{"tipo": "email", "valor": e, "nombre": "", "verificado": False}
              for e in emails]
    fichas += [{"tipo": "telefono", "valor": t, "nombre": "", "verificado": False}
               for t in telefonos]
    notas = notas_email + notas_tel
    return {
        "id": f"CLI-{num:04d}",
        "codigo_empresa": limpiar(fila.get("cod", "")),
        "nombre": limpiar(fila.get("nombre", "")),
        "direccion": limpiar(fila.get("domicilio", "")),
        "cp": limpiar(fila.get("cp", "")),
        "poblacion": limpiar(fila.get("poblacion", "")),
        "edificios": [],
        "tipo": "cliente",
        "propiedad": "propio",   # exportado bajo el código comercial del asesor
        "fichas_contacto": fichas,
        "fecha_alta": None,
        "fecha_primera_contactacion": None,
        "fecha_ultima_interaccion": None,
        "estado_seguimiento": "al_dia",
        "notas": " | ".join(notas),
        "demo": False,
    }


# ── Proceso principal ───────────────────────────────────────────

def main(fich: Path | None = None) -> int:
    """Importa `fich` (lo usa el asistente del panel) o, si no se
    indica, el fichero más reciente de entrada/."""
    fich = fich or localizar_fichero()
    if not fich:
        print("[i] No hay ficheros pendientes en entrada/")
        return 0
    if not fich.is_file():
        print(f"[ERROR] No existe el fichero {fich}")
        return 1
    print(f"[i] Importando: {fich.name}")

    try:
        filas = leer_filas(fich)
        idx = detectar_cabecera(filas)
    except Exception as exc:  # noqa: BLE001 — fichero ilegible o sin cabecera
        print(f"[ERROR] {exc}. No se importa nada.")
        return 1
    colmap = columnas_con_datos(filas, idx)
    print(f"[i] Cabecera en fila {idx+1}: columnas {colmap}")
    faltantes = [k for k in ("nombre", "email", "telefono") if colmap[k] == -1]
    if faltantes:
        print(f"[ERROR] No se encontraron columnas: {faltantes}. No se importa nada.")
        return 1

    clientes = []
    num = 0
    for fila_cruda in filas[idx + 1:]:
        if not any(c.strip() for c in fila_cruda):
            continue
        fila = {k: (fila_cruda[v] if v >= 0 else "") for k, v in colmap.items()}
        if not fila.get("nombre", "").strip():
            continue
        num += 1
        clientes.append(fila_a_cliente(num, fila))

    # ── Control de calidad antes de escribir nada ──
    n_email = sum(1 for c in clientes if any(f["tipo"] == "email" for f in c["fichas_contacto"]))
    n_tel = sum(1 for c in clientes if any(f["tipo"] == "telefono" for f in c["fichas_contacto"]))
    if n_email == 0 and n_tel == 0:
        print(f"[ERROR] No se extrajo ningún email ni teléfono de {num} filas.")
        print("        Posible mapeo de columnas erróneo. NO se importa ni archiva nada.")
        return 1

    # ── Duplicados: mismo email o misma dirección ──
    duplicados: list[dict] = []
    vistos_email: dict[str, str] = {}
    vistos_dir: dict[str, str] = {}
    for cli in clientes:
        for f in cli["fichas_contacto"]:
            if f["tipo"] != "email":
                continue
            if f["valor"] in vistos_email:
                duplicados.append({"tipo": "email repetido", "valor": f["valor"],
                                   "clientes": [vistos_email[f["valor"]],
                                                f"{cli['id']} {cli['nombre']}"]})
            else:
                vistos_email[f["valor"]] = f"{cli['id']} {cli['nombre']}"
        clave_dir = f"{cli['direccion'].lower()}|{cli['poblacion'].lower()}".strip("|")
        if clave_dir in vistos_dir:
            duplicados.append({"tipo": "misma dirección", "valor": cli["direccion"],
                               "clientes": [vistos_dir[clave_dir],
                                            f"{cli['id']} {cli['nombre']}"]})
        else:
            vistos_dir[clave_dir] = f"{cli['id']} {cli['nombre']}"

    # identidad: cada email/teléfono apunta al PRIMER cliente que lo usa
    mapeo: dict[str, str] = {}
    for cli in clientes:
        for f in cli["fichas_contacto"]:
            if f["valor"] not in mapeo:
                mapeo[f["valor"]] = cli["id"]

    informe = {
        "fichero": fich.name,
        "importado": datetime.now().isoformat(timespec="seconds"),
        "cabecera_fila": idx + 1,
        "columnas": colmap,
        "total_registros": len(clientes),
        "con_email": n_email,
        "con_telefono": n_tel,
        "sin_email": len(clientes) - n_email,
        "sin_telefono": len(clientes) - n_tel,
        "posibles_duplicados": duplicados,
        "registros": [
            {"codigo": c["codigo_empresa"], "nombre": c["nombre"],
             "poblacion": c["poblacion"],
             "emails": [f["valor"] for f in c["fichas_contacto"] if f["tipo"] == "email"],
             "telefonos": [f["valor"] for f in c["fichas_contacto"] if f["tipo"] == "telefono"],
             "notas": c["notas"]}
            for c in clientes
        ],
    }

    # ── Escritura segura (con backup previo) ──
    memoria.guardar("maestro_clientes.json",
                    {"version": 1, "clientes": clientes}, backup=True)
    memoria.guardar("identidad.json",
                    {"version": 1, "mapeo": mapeo, "sin_vincular": []}, backup=True)
    memoria.guardar("informe_importacion.json", informe)

    # ── Archivar el fichero importado ──
    PROCESADOS.mkdir(exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.move(str(fich), PROCESADOS / f"{marca}_{fich.name}")

    print(f"[OK] {len(clientes)} clientes importados")
    print(f"     con email: {n_email} (sin: {informe['sin_email']})"
          f"  ·  con teléfono: {n_tel} (sin: {informe['sin_telefono']})")
    if duplicados:
        print(f"[!] {len(duplicados)} posibles duplicados (ver datos/informe_importacion.json):")
        for d in duplicados:
            print(f"     [{d['tipo']}] {d['valor']}")
            for cli in d["clientes"]:
                print(f"        - {cli}")
    print("[OK] Fichero archivado en entrada/procesados/")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else None))
