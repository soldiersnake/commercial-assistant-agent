# -*- coding: utf-8 -*-
"""memoria.py — Capa de acceso a la memoria de datos.

ÚNICO punto de lectura/escritura de `datos/`. Todo el resto del
sistema (importador, sync, dashboard, agente) pasa por aquí, para
que una futura migración a base de datos solo requiera reescribir
este módulo.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
ARCHIVO = DATOS / "archivo"


def ruta(nombre: str) -> Path:
    """Ruta de un fichero de memoria (admite subcarpetas 'meses/2026-11.md')."""
    return DATOS / nombre


def cargar(nombre: str, default: Any = None) -> Any:
    """Carga un fichero JSON de la memoria; devuelve `default` si no existe."""
    fich = ruta(nombre)
    if not fich.exists():
        return default
    with open(fich, encoding="utf-8") as fh:
        return json.load(fh)


def guardar(nombre: str, datos: Any, backup: bool = False) -> Path:
    """Guarda JSON en la memoria de forma atómica (tmp + replace).

    Con `backup=True` copia la versión previa a `datos/archivo/`
    (regla: nada se borra sin archivar).
    """
    fich = ruta(nombre)
    fich.parent.mkdir(parents=True, exist_ok=True)
    if backup and fich.exists():
        ARCHIVO.mkdir(exist_ok=True)
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(fich, ARCHIVO / f"{fich.stem}_{marca}{fich.suffix}")
    tmp = fich.with_suffix(f"{fich.suffix}.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=2)
    tmp.replace(fich)
    return fich


def cargar_texto(nombre: str) -> str | None:
    """Carga un fichero de texto/Markdown de la memoria."""
    fich = ruta(nombre)
    if not fich.exists():
        return None
    return fich.read_text(encoding="utf-8")


def guardar_texto(nombre: str, texto: str, backup: bool = False) -> Path:
    fich = ruta(nombre)
    fich.parent.mkdir(parents=True, exist_ok=True)
    if backup and fich.exists():
        ARCHIVO.mkdir(exist_ok=True)
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(fich, ARCHIVO / f"{fich.stem}_{marca}{fich.suffix}")
    fich.write_text(texto, encoding="utf-8")
    return fich


def archivar(ruta_fichero: str | Path, subcarpeta: str = "") -> Path:
    """Mueve un fichero a `datos/archivo/` (o `entrada/procesados/`)."""
    origen = Path(ruta_fichero)
    destino_dir = ARCHIVO / subcarpeta if subcarpeta else ARCHIVO
    destino_dir.mkdir(parents=True, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = destino_dir / f"{marca}_{origen.name}"
    shutil.move(str(origen), str(destino))
    return destino
