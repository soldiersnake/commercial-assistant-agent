# -*- coding: utf-8 -*-
"""servidor.py — Panel de Gestión (mini-app local).

Servidor HTTP pequeño en 127.0.0.1:8765 que sirve el dashboard y
expone una API mínima:

  GET  /api/estado   → instantánea completa de la memoria (datos/)
  POST /api/accion   → ejecuta una acción del panel sobre la memoria

Las acciones del panel escriben DIRECTAMENTE en la memoria (via
scripts/memoria.py) salvo `responder`, que además deposita una
orden en `datos/acciones/` para que el agente la procese (refinar
el texto y crear el borrador en Gmail — nunca enviar).

Uso:  .venv\\Scripts\\python.exe dashboard\\servidor.py
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import memoria  # noqa: E402
import gcal  # noqa: E402

HOST = "127.0.0.1"
PUERTO = 8765
INDICE_HTML = RAIZ / "dashboard" / "index.html"
ACCIONES_DIR = RAIZ / "datos" / "acciones"
ENTRADA = RAIZ / "entrada"

CATEGORIAS = ("tecnico", "facturacion", "trabajos_pendientes", "comercial", "empresa")


# ── Utilidades ──────────────────────────────────────────────────

def hoy() -> date:
    return date.today()


def fecha(valor: str | None) -> date | None:
    if not valor:
        return None
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError:
        return None


def normalizar(valor: str) -> str:
    valor = str(valor).strip().lower()
    if "@" in valor:
        return valor
    return "".join(c for c in valor if c.isdigit())


def siguiente_id(prefijo: str, ficheros: list[Path], patron: str) -> str:
    """Siguiente identificador ACC-000n mirando los ficheros existentes."""
    import re
    maximo = 0
    for f in ficheros:
        m = re.match(patron, f.stem)
        if m:
            maximo = max(maximo, int(m.group(1)))
    return f"{prefijo}-{maximo + 1:04d}"


def anadir_registro_mes(hora: datetime, cliente_txt: str, categoria: str,
                        canal: str, accion: str, estado: str, nota: str = "") -> None:
    """Añade una fila al registro cronológico del mes (datos/meses/)."""
    mes_txt = hora.strftime("%Y-%m")
    nombre = f"meses/{mes_txt}.md"
    texto = memoria.cargar_texto(nombre) or (
        f"# Registro — {hora.strftime('%B %Y')}\n\n> Fila: fecha | hora | "
        "cliente/ID | categoría | canal | acción | estado | nota\n\n"
        f"## {hora:%d/%m/%Y}\n"
    )
    marca = f"## {hora:%d/%m/%Y}"
    if marca not in texto:
        texto += f"\n{marca}\n"
    fila = (f"| {hora:%Y-%m-%d} | {hora:%H:%M} | {cliente_txt} | {categoria or '-'} "
            f"| {canal} | {accion} | {estado} | {nota} |\n")
    memoria.guardar_texto(nombre, texto.rstrip("\n") + "\n" + fila)


# ── Instantánea de estado ───────────────────────────────────────

def _paso_pendiente_captacion(seg: dict) -> dict | None:
    """Siguiente paso pendiente del plan de captación (o None)."""
    if not seg.get("captacion"):
        return None
    plan = seg.get("plan_captacion") or {}
    if plan.get("estado") != "activo":
        return None
    pendientes = [p for p in plan.get("pasos", [])
                  if p.get("estado") in ("pendiente", "borrador_creado")]
    if not pendientes:
        return None
    p = pendientes[0]
    fp = fecha(p.get("fecha_programada"))
    return {"n": p["n"], "concepto": p.get("concepto", ""),
            "fecha_programada": p.get("fecha_programada"),
            "estado": p.get("estado"),
            "vencido": bool(fp and fp <= hoy())}


def construir_estado() -> dict:
    maestro = memoria.cargar("maestro_clientes.json", {"clientes": []})
    seguimientos = memoria.cargar("seguimientos.json", {"seguimientos": []})
    presupuestos = memoria.cargar("presupuestos.json", {"presupuestos": []})
    programaciones = memoria.cargar("programaciones.json", {"programaciones": []})
    identidad = memoria.cargar("identidad.json", {"mapeo": {}, "sin_vincular": []})
    ventas = memoria.cargar("ventas.json", {"ventas": []})
    citas = memoria.cargar("citas.json", {"citas": []})
    config = memoria.cargar("config.json", {})
    informe = memoria.cargar("informe_importacion.json", {})

    ahora = datetime.now()
    clientes = maestro["clientes"]
    indice = {c["id"]: c["nombre"] for c in clientes}

    # seguimientos con derivados
    segs = []
    for s in seguimientos["seguimientos"]:
        copia = dict(s)
        if s.get("estado") in ("pendiente_respuesta", "borrador_creado"):
            d = fecha(s.get("fecha_ultima_interaccion") or s.get("fecha_ultimo_movimiento"))
            copia["dias_sin_respuesta"] = (hoy() - d).days if d else None
        else:
            copia["dias_sin_respuesta"] = None
        copia["cliente_nombre"] = indice.get(s.get("cliente_id"), "")
        copia["cliente_propiedad"] = next(
            (c.get("propiedad") for c in clientes if c["id"] == s.get("cliente_id")), "")
        copia["captacion"] = bool(s.get("captacion"))
        copia["paso_pendiente"] = _paso_pendiente_captacion(copia)
        segs.append(copia)
    segs.sort(key=lambda s: (
        {"alta": 0, "media": 1, "baja": 2}.get(s.get("prioridad"), 3),
        -(s.get("dias_sin_respuesta") or 0),
    ))

    # presupuestos con derivados
    intervalo = config.get("reglas_presupuestos", {}).get("intervalo_reclamacion_dias", 15)
    pres = []
    for p in presupuestos["presupuestos"]:
        copia = dict(p)
        hechas = [r for r in p.get("reclamaciones", [])
                  if r.get("estado") in ("enviada", "borrador_creado")]
        copia["n_reclamaciones"] = len(p.get("reclamaciones", []))
        base = fecha(p.get("fecha_reclamacion"))
        if p.get("estado") == "pendiente_firma" and base:
            prox = date.fromordinal(base.toordinal() + len(hechas) * intervalo)
            copia["proxima_reclamacion"] = prox.isoformat()
            copia["reclamacion_vencida"] = prox < hoy()
        else:
            copia["proxima_reclamacion"] = None
            copia["reclamacion_vencida"] = False
        copia["cliente_nombre"] = indice.get(p.get("cliente_id"), "")
        pres.append(copia)

    progs = []
    for prog in programaciones["programaciones"]:
        copia = dict(prog)
        fp = fecha(prog.get("fecha_programada"))
        if fp and fp < hoy() and prog.get("estado") not in ("completado", "cancelado"):
            copia["estado"] = "vencido"
        copia["cliente_nombre"] = indice.get(prog.get("cliente_id"), "")
        progs.append(copia)

    propios = [c for c in clientes if c.get("propiedad") == "propio"]
    pendientes = [s for s in segs if s.get("estado") == "pendiente_respuesta"]
    en_borrador = [s for s in segs if s.get("estado") == "borrador_creado"]
    firmadas = [p for p in presupuestos["presupuestos"]
                if p.get("estado") == "firmado" and (p.get("fecha_firma") or "").startswith(str(hoy().year))]

    metricas = {
        "clientes": len(clientes),
        "propios": len(propios),
        "ajenos": len(clientes) - len(propios),
        "prospectos": sum(1 for c in propios if c.get("tipo") == "prospecto"),
        "seguimientos_abiertos": sum(1 for s in segs
                                     if s.get("estado") not in ("cerrado", "descartado")),
        "pendientes_respuesta": len(pendientes),
        "en_borrador": len(en_borrador),
        "urgentes": sum(1 for s in pendientes if s.get("prioridad") == "alta"),
        "sin_responder_7": sum(1 for s in pendientes + en_borrador
                               if (s.get("dias_sin_respuesta") or 0) >= 7),
        "captaciones_activas": sum(1 for s in segs
                                   if s.get("captacion")
                                   and s.get("estado") not in ("cerrado", "descartado")),
        "captacion_pasos_vencidos": sum(1 for s in segs
                                        if s.get("captacion")
                                        and s.get("estado") not in ("cerrado", "descartado")
                                        and (s.get("paso_pendiente") or {}).get("vencido")),
        "sin_vincular": len(identidad.get("sin_vincular", [])),
        "presup_pendiente_firma": sum(1 for p in presupuestos["presupuestos"]
                                      if p.get("estado") == "pendiente_firma"),
        "presup_importe_pendiente": sum(p.get("importe") or 0 for p in presupuestos["presupuestos"]
                                        if p.get("estado") == "pendiente_firma"),
        "presup_importe_firmado_anno": sum(p.get("importe") or 0 for p in firmadas),
        "reclamaciones_vencidas": sum(1 for p in pres if p.get("reclamacion_vencida")),
        "programaciones_pend": sum(1 for p in progs
                                   if p.get("estado") in ("pendiente", "avisado")),
        "programaciones_vencidas": sum(1 for p in progs if p.get("estado") == "vencido"),
        "citas_programadas": sum(1 for c in citas["citas"] if c.get("estado") == "programada"),
        "citas_efectuadas": sum(1 for c in citas["citas"] if c.get("estado") == "efectuada"),
        "citas_canceladas": sum(1 for c in citas["citas"] if c.get("estado") == "cancelada"),
        "citas_modificaciones": sum(len(c.get("modificaciones", [])) for c in citas["citas"]),
    }

    return {
        "generado": ahora.isoformat(timespec="seconds"),
        "hoy": hoy().isoformat(),
        "metricas": metricas,
        "economico": construir_economico(clientes, presupuestos["presupuestos"],
                                         ventas.get("ventas", []), config),
        "clientes": clientes,
        "ventas": ventas.get("ventas", []),
        "citas": citas.get("citas", []),
        "seguimientos": segs,
        "presupuestos": pres,
        "programaciones": progs,
        "sin_vincular": identidad.get("sin_vincular", []),
        "duplicados": informe.get("posibles_duplicados", []),
        "config": {
            "empresa": config.get("empresa", {}),
            "asesor": config.get("asesor", {}),
            "objetivo_anual": config.get("objetivo_anual", {}),
        },
    }


# ── Acciones ────────────────────────────────────────────────────

def _lanzar_proceso(cmd: list) -> None:
    """Lanza un proceso en segundo plano sin bloquear la respuesta."""
    import subprocess
    try:
        subprocess.Popen(cmd, cwd=str(RAIZ),
                         creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        pass


def _lanzar_procesar_cola() -> None:
    """Lanza en segundo plano el procesado de la cola de órdenes del
    panel (scripts/procesar_cola.ps1). No bloquea la respuesta HTTP."""
    script = RAIZ / "scripts" / "procesar_cola.ps1"
    if not script.exists():
        return
    _lanzar_proceso(["powershell", "-NoProfile", "-ExecutionPolicy",
                     "Bypass", "-File", str(script), "-Silencioso"])


def _guardar_informe_importacion(informe: dict) -> None:
    memoria.guardar("informe_importacion.json", informe)


def acc_vincular(p: dict) -> str:
    valor = normalizar(p["valor"])
    tipo = p.get("tipo", "email")
    cliente_id = p["cliente_id"]
    maestro = memoria.cargar("maestro_clientes.json")
    identidad = memoria.cargar("identidad.json", {"mapeo": {}, "sin_vincular": []})
    cli = next((c for c in maestro["clientes"] if c["id"] == cliente_id), None)
    if not cli:
        return f"No existe el cliente {cliente_id}"
    if not any(f.get("valor") == valor for f in cli["fichas_contacto"]):
        cli["fichas_contacto"].append({"tipo": tipo, "valor": valor,
                                       "nombre": p.get("nombre", ""),
                                       "verificado": True})
    memoria.guardar("maestro_clientes.json", maestro)
    identidad["mapeo"][valor] = cliente_id
    identidad["sin_vincular"] = [s for s in identidad.get("sin_vincular", [])
                                 if normalizar(s["valor"]) != valor]
    memoria.guardar("identidad.json", identidad)
    anadir_registro_mes(datetime.now(), f"{cliente_id} {cli['nombre']}", "-",
                        p.get("tipo", "email"),
                        f"Vinculado contacto {p['valor']}", "vinculado")
    return f"Vinculado {p['valor']} → {cliente_id}"


def acc_crear_cliente(p: dict) -> str:
    maestro = memoria.cargar("maestro_clientes.json")
    identidad = memoria.cargar("identidad.json", {"mapeo": {}, "sin_vincular": []})
    maximo = max((int(c["id"].split("-")[1]) for c in maestro["clientes"]), default=0)
    nuevo_id = f"CLI-{maximo + 1:04d}"
    valor = normalizar(p["valor"])
    cliente = {
        "id": nuevo_id,
        "codigo_empresa": "",
        "nombre": p["nombre"].strip(),
        "direccion": p.get("direccion", ""),
        "cp": "", "poblacion": p.get("poblacion", ""),
        "edificios": [],
        "tipo": p.get("tipo", "prospecto"),
        "propiedad": "propio",
        "fichas_contacto": [{"tipo": p.get("tipo_contacto", "email"),
                             "valor": valor, "nombre": "", "verificado": True}],
        "fecha_alta": hoy().isoformat(),
        "fecha_primera_contactacion": hoy().isoformat(),
        "fecha_ultima_interaccion": None,
        "estado_seguimiento": "al_dia",
        "notas": f"Creado desde el panel el {hoy().isoformat()}",
    }
    maestro["clientes"].append(cliente)
    memoria.guardar("maestro_clientes.json", maestro, backup=True)
    identidad["mapeo"][valor] = nuevo_id
    identidad["sin_vincular"] = [s for s in identidad.get("sin_vincular", [])
                                 if normalizar(s["valor"]) != valor]
    memoria.guardar("identidad.json", identidad)
    anadir_registro_mes(datetime.now(), f"{nuevo_id} {cliente['nombre']}", "comercial",
                        p.get("tipo_contacto", "email"),
                        f"Cliente creado desde el panel ({p['valor']})", "creado")
    return f"Cliente creado: {nuevo_id}"


def acc_cambiar_propiedad(p: dict) -> str:
    maestro = memoria.cargar("maestro_clientes.json")
    cli = next((c for c in maestro["clientes"] if c["id"] == p["cliente_id"]), None)
    if not cli:
        return f"No existe el cliente {p['cliente_id']}"
    cli["propiedad"] = p["propiedad"] if p["propiedad"] in ("propio", "ajeno") else "propio"
    memoria.guardar("maestro_clientes.json", maestro)
    return f"{cli['id']} → propiedad {cli['propiedad']}"


def acc_cambiar_tipo(p: dict) -> str:
    maestro = memoria.cargar("maestro_clientes.json")
    cli = next((c for c in maestro["clientes"] if c["id"] == p["cliente_id"]), None)
    if not cli:
        return f"No existe el cliente {p['cliente_id']}"
    cli["tipo"] = p["tipo"] if p["tipo"] in ("cliente", "prospecto") else "cliente"
    memoria.guardar("maestro_clientes.json", maestro)
    return f"{cli['id']} → tipo {cli['tipo']}"


def acc_marcar_firmado(p: dict) -> str:
    presupuestos = memoria.cargar("presupuestos.json")
    pre = next((x for x in presupuestos["presupuestos"]
                if x["id"] == p["presupuesto_id"]), None)
    if not pre:
        return f"No existe el presupuesto {p['presupuesto_id']}"
    pre["estado"] = "firmado"
    pre["fecha_firma"] = p.get("fecha") or hoy().isoformat()
    memoria.guardar("presupuestos.json", presupuestos, backup=True)
    anadir_registro_mes(datetime.now(), str(pre.get("cliente_id") or pre["id"]),
                        "comercial", "email",
                        f"Presupuesto {pre['id']} marcado FIRMADO", "firmado")
    return f"{pre['id']} firmado"


def acc_cambiar_estado_presupuesto(p: dict) -> str:
    permitidos = ("enviado", "pendiente_firma", "rechazado", "anulado")
    if p.get("estado") not in permitidos:
        return f"Estado no permitido: {p.get('estado')}"
    presupuestos = memoria.cargar("presupuestos.json")
    pre = next((x for x in presupuestos["presupuestos"]
                if x["id"] == p["presupuesto_id"]), None)
    if not pre:
        return f"No existe el presupuesto {p['presupuesto_id']}"
    pre["estado"] = p["estado"]
    memoria.guardar("presupuestos.json", presupuestos, backup=True)
    return f"{pre['id']} → {p['estado']}"


def acc_responder(p: dict) -> str:
    """Acción prioridad del panel: el agente la procesará y creará
    el borrador refinado en Gmail (nunca envía)."""
    ACCIONES_DIR.mkdir(exist_ok=True)
    existentes = list(ACCIONES_DIR.glob("ACC-*.json"))
    id_acc = siguiente_id("ACC", existentes, r"ACC-(\d+)")
    orden = {
        "id": id_acc,
        "creado": datetime.now().isoformat(timespec="seconds"),
        "tipo": "responder",
        "estado": "pendiente_agente",
        "cliente_id": p.get("cliente_id"),
        "seguimiento_id": p.get("seguimiento_id"),
        "correo_origen": p.get("correo_origen", ""),
        "texto_bruto": p.get("texto", ""),
        "programar": p.get("programar") or None,
    }
    memoria.guardar(f"acciones/{id_acc}.json", orden)
    anadir_registro_mes(datetime.now(),
                        f"{p.get('cliente_id') or '-'}", "comercial", "email",
                        f"Respuesta solicitada desde el panel ({id_acc})",
                        "pendiente_agente")
    # procesado automático e inmediato de la cola (el borrador aparece
    # en Gmail en 1-2 minutos, no espera a las corridas de 7:00/16:00)
    _lanzar_procesar_cola()
    # si va programado, crear también la programación con avisos
    prog = p.get("programar")
    if prog and prog.get("fecha"):
        programaciones = memoria.cargar("programaciones.json",
                                        {"programaciones": []})
        maximo = max((int(x["id"].split("-")[1])
                      for x in programaciones["programaciones"]), default=0)
        fprog = prog["fecha"]
        programaciones["programaciones"].append({
            "id": f"PROG-{maximo + 1:04d}",
            "cliente_id": p.get("cliente_id"),
            "seguimiento_id": p.get("seguimiento_id"),
            "asunto": f"Respuesta desde panel ({id_acc})",
            "fecha_programada": fprog,
            "hora_programada": prog.get("hora", "09:00"),
            "estado": "pendiente",
            "borrador_creado": False,
            "avisos": [
                {"fecha": fprog, "tipo": "manana", "hecho": False},
                {"fecha": fprog, "tipo": "tarde_verificacion", "hecho": False},
            ],
            "creado": datetime.now().isoformat(timespec="seconds"),
        })
        memoria.guardar("programaciones.json", programaciones, backup=True)
    return f"Orden {id_acc} creada: el agente generará el borrador en Gmail"


def acc_reprogramar(p: dict) -> str:
    programaciones = memoria.cargar("programaciones.json")
    prog = next((x for x in programaciones["programaciones"]
                 if x["id"] == p["id"]), None)
    if not prog:
        return f"No existe la programación {p['id']}"
    prog["fecha_programada"] = p["fecha"]
    prog["hora_programada"] = p.get("hora", prog.get("hora_programada", "09:00"))
    prog["estado"] = "pendiente"
    prog["avisos"] = [
        {"fecha": prog["fecha_programada"], "tipo": "manana", "hecho": False},
        {"fecha": prog["fecha_programada"], "tipo": "tarde_verificacion", "hecho": False},
    ]
    memoria.guardar("programaciones.json", programaciones, backup=True)
    return f"{prog['id']} reprogramada a {prog['fecha_programada']}"


def acc_estado_programacion(p: dict) -> str:
    if p.get("estado") not in ("completado", "cancelado", "pendiente"):
        return "Estado no permitido"
    programaciones = memoria.cargar("programaciones.json")
    prog = next((x for x in programaciones["programaciones"]
                 if x["id"] == p["id"]), None)
    if not prog:
        return f"No existe la programación {p['id']}"
    prog["estado"] = p["estado"]
    memoria.guardar("programaciones.json", programaciones, backup=True)
    return f"{prog['id']} → {p['estado']}"


def acc_fusionar(p: dict) -> str:
    destino_id, absorbido_id = p["id_destino"], p["id_absorbido"]
    if destino_id == absorbido_id:
        return "No se puede fusionar un cliente consigo mismo"
    maestro = memoria.cargar("maestro_clientes.json")
    destino = next((c for c in maestro["clientes"] if c["id"] == destino_id), None)
    absorbido = next((c for c in maestro["clientes"] if c["id"] == absorbido_id), None)
    if not destino or not absorbido:
        return "No se encontraron los clientes a fusionar"

    # 1. mover fichas de contacto no duplicadas
    valores_destino = {normalizar(f["valor"]) for f in destino["fichas_contacto"]}
    for f in absorbido["fichas_contacto"]:
        if normalizar(f["valor"]) not in valores_destino:
            destino["fichas_contacto"].append(f)
            valores_destino.add(normalizar(f["valor"]))
    # 2. sumar edificios y notas
    destino["edificios"] = (destino.get("edificios") or []) + (absorbido.get("edificios") or [])
    if absorbido.get("notas"):
        destino["notas"] = (destino.get("notas", "") +
                            f" | Fusionado con {absorbido_id}: {absorbido['notas']}")
    destino["fecha_ultima_interaccion"] = max(
        destino.get("fecha_ultima_interaccion") or "",
        absorbido.get("fecha_ultima_interaccion") or "") or None
    # 3. archivar la ficha absorbida (nunca se borra sin archivar)
    (RAIZ / "datos" / "archivo" / "fusiones").mkdir(parents=True, exist_ok=True)
    memoria.guardar(f"archivo/fusiones/{absorbido_id}_{datetime.now():%Y%m%d_%H%M%S}.json",
                    absorbido)
    maestro["clientes"] = [c for c in maestro["clientes"] if c["id"] != absorbido_id]
    memoria.guardar("maestro_clientes.json", maestro, backup=True)

    # 4. reasignar referencias
    for nombre_fich, clave in (("seguimientos.json", "seguimientos"),
                               ("presupuestos.json", "presupuestos"),
                               ("programaciones.json", "programaciones")):
        fich = memoria.cargar(nombre_fich)
        if not fich:
            continue
        for reg in fich[clave]:
            if reg.get("cliente_id") == absorbido_id:
                reg["cliente_id"] = destino_id
        memoria.guardar(nombre_fich, fich, backup=True)

    # 5. identidad: toda la mapeo del absorbido pasa al destino
    identidad = memoria.cargar("identidad.json", {"mapeo": {}, "sin_vincular": []})
    identidad["mapeo"] = {k: (destino_id if v == absorbido_id else v)
                          for k, v in identidad["mapeo"].items()}
    memoria.guardar("identidad.json", identidad)
    anadir_registro_mes(datetime.now(), f"{destino_id} {destino['nombre']}", "-",
                        "-", f"Fusionadas fichas {absorbido_id} + {destino_id}",
                        "fusionado")
    return f"Fusionado {absorbido_id} en {destino_id} (ficha absorbida archivada)"


def acc_desvincular(p: dict) -> str:
    valor = normalizar(p["valor"])
    maestro = memoria.cargar("maestro_clientes.json")
    identidad = memoria.cargar("identidad.json", {"mapeo": {}, "sin_vincular": []})
    cli = next((c for c in maestro["clientes"] if c["id"] == p["cliente_id"]), None)
    if not cli:
        return f"No existe el cliente {p['cliente_id']}"
    cli["fichas_contacto"] = [f for f in cli["fichas_contacto"]
                              if normalizar(f["valor"]) != valor]
    memoria.guardar("maestro_clientes.json", maestro)
    identidad["mapeo"].pop(valor, None)
    memoria.guardar("identidad.json", identidad)
    return f"Contacto {p['valor']} desvinculado de {cli['id']}"


def acc_estado_seguimiento(p: dict) -> str:
    permitidos = ("pendiente_respuesta", "respondido", "cerrado")
    if p.get("estado") not in permitidos:
        return f"Estado no permitido: {p.get('estado')}"
    segs = memoria.cargar("seguimientos.json")
    seg = next((s for s in segs["seguimientos"] if s["id"] == p["id"]), None)
    if not seg:
        return f"No existe el seguimiento {p['id']}"
    seg["estado"] = p["estado"]
    if p["estado"] == "respondido":
        seg["fecha_ultimo_envio"] = hoy().isoformat()
        if seg.get("historial") is not None:
            seg.setdefault("historial", []).append({
                "fecha": hoy().isoformat(),
                "evento": "El asesor confirma desde el panel que lo envió a mano.",
            })
    memoria.guardar("seguimientos.json", segs, backup=True)
    anadir_registro_mes(datetime.now(), f"{seg.get('cliente_id') or seg['id']}",
                        seg.get("categoria", "-"), "email",
                        f"Seguimiento {seg['id']} marcado {p['estado']} (panel)",
                        p["estado"])
    return f"{seg['id']} → {p['estado']}"


def acc_descartar_seguimiento(p: dict) -> str:
    """Marca un seguimiento como descartado (caso resuelto sin respuesta).

    No borra nada (regla de oro nº 5): el estado queda en la memoria,
    la nota del asesor queda en el historial y en el registro mensual.
    """
    nota = (p.get("nota") or "").strip()
    if not nota:
        return "Falta la nota de descarte (describe brevemente por qué se descarta)"
    segs = memoria.cargar("seguimientos.json")
    seg = next((s for s in segs["seguimientos"] if s["id"] == p["id"]), None)
    if not seg:
        return f"No existe el seguimiento {p['id']}"
    if seg.get("estado") in ("descartado", "cerrado"):
        return f"{seg['id']} ya está {seg['estado']}"
    seg["estado"] = "descartado"
    seg["motivo_descarte"] = nota
    seg["fecha_ultimo_movimiento"] = hoy().isoformat()
    seg.setdefault("historial", []).append({
        "fecha": hoy().isoformat(),
        "evento": f"Descartado desde el panel: {nota}",
    })
    memoria.guardar("seguimientos.json", segs, backup=True)
    anadir_registro_mes(datetime.now(), f"{seg.get('cliente_id') or seg['id']}",
                        seg.get("categoria", "-"), "email",
                        f"Seguimiento {seg['id']} descartado (panel): {nota}",
                        "descartado")
    return f"{seg['id']} → descartado"


# ── Captación (rama comercial: cliente vs captación + plan de 3 pasos) ──

CONCEPTOS_CAPTACION = ("Propuesta inicial", "Recordatorio", "Cierre / último toque")


def _reglas_captacion() -> tuple[int, int]:
    """Cadencia de los pasos 2 y 3 (config.json → reglas_captacion)."""
    config = memoria.cargar("config.json", {})
    reglas = config.get("reglas_captacion", {})
    return (int(reglas.get("dias_paso2", 7)), int(reglas.get("dias_paso3", 15)))


def _crear_plan_captacion(seg: dict) -> dict:
    """Plan de 3 pasos para una captación. El paso 1 es el borrador de
    respuesta al mail entrante que ya generó el sistema: si el asesor aún
    no lo envió queda 'borrador_creado'; si ya envió, 'enviado'."""
    d2, d3 = _reglas_captacion()
    inicio = fecha(seg.get("fecha_apertura")) or hoy()
    estado_p1 = "pendiente"
    if seg.get("estado") == "borrador_creado":
        estado_p1 = "borrador_creado"
    elif seg.get("estado") == "respondido":
        estado_p1 = "enviado"
    pasos = [
        {"n": 1, "concepto": CONCEPTOS_CAPTACION[0],
         "fecha_programada": inicio.isoformat(), "estado": estado_p1,
         "borrador_id": seg.get("borrador_id"),
         "fecha_envio": seg.get("fecha_ultimo_envio") if estado_p1 == "enviado" else None},
        {"n": 2, "concepto": CONCEPTOS_CAPTACION[1],
         "fecha_programada": date.fromordinal(inicio.toordinal() + d2).isoformat(),
         "estado": "pendiente"},
        {"n": 3, "concepto": CONCEPTOS_CAPTACION[2],
         "fecha_programada": date.fromordinal(inicio.toordinal() + d2 + d3).isoformat(),
         "estado": "pendiente"},
    ]
    return {"pasos_totales": 3, "paso_actual": 1, "pasos": pasos, "estado": "activo"}


def acc_captacion_toggle(p: dict) -> str:
    """Marca/desmarca un seguimiento comercial como CAPTACIÓN.

    Regla: solo una contactación de CATEGORÍA COMERCIAL puede ser
    captación (prospecto nuevo o edificio ajeno a captar). La
    corrección la hace el asesor desde el panel."""
    segs = memoria.cargar("seguimientos.json")
    seg = next((s for s in segs["seguimientos"] if s["id"] == p["id"]), None)
    if not seg:
        return f"No existe el seguimiento {p['id']}"
    if seg.get("categoria") != "comercial":
        return ("Solo un seguimiento de categoría COMERCIAL puede marcarse "
                "como captación (recategorízalo primero si procede)")
    if seg.get("estado") in ("cerrado", "descartado"):
        return f"{seg['id']} está {seg['estado']}: no se puede modificar"
    quere = bool(p.get("captacion"))
    if quere and not seg.get("captacion"):
        seg["captacion"] = True
        seg["plan_captacion"] = _crear_plan_captacion(seg)
        evento = "Marcado como 🎯 CAPTACIÓN (plan de 3 propuestas creado)"
        texto_mensual = f"Seguimiento {seg['id']} marcado CAPTACIÓN (panel)"
    elif not quere and seg.get("captacion"):
        seg["captacion"] = False
        plan = seg.get("plan_captacion") or {}
        plan["estado"] = "cancelado"
        seg["plan_captacion"] = plan
        evento = "Pasa a gestión de CLIENTE (plan de captación cancelado, conservado en historial)"
        texto_mensual = f"Seguimiento {seg['id']} pasa a gestión de cliente (panel)"
    else:
        return f"{seg['id']} ya estaba así"
    seg["fecha_ultimo_movimiento"] = hoy().isoformat()
    seg.setdefault("historial", []).append(
        {"fecha": hoy().isoformat(), "evento": evento})
    memoria.guardar("seguimientos.json", segs, backup=True)
    anadir_registro_mes(datetime.now(), f"{seg.get('cliente_id') or seg['id']}",
                        "comercial", "email", texto_mensual,
                        "captacion" if quere else "cliente")
    return f"{seg['id']} → {'🎯 captación' if quere else '👤 cliente'}"


def acc_recategorizar_seguimiento(p: dict) -> str:
    """Cambia la categoría de un seguimiento (corrección de la
    clasificación automática). NO activa captación por sí sola."""
    permitidos = ("tecnico", "facturacion", "trabajos_pendientes",
                  "comercial", "empresa")
    if p.get("categoria") not in permitidos:
        return f"Categoría no permitida: {p.get('categoria')}"
    segs = memoria.cargar("seguimientos.json")
    seg = next((s for s in segs["seguimientos"] if s["id"] == p["id"]), None)
    if not seg:
        return f"No existe el seguimiento {p['id']}"
    if seg.get("estado") in ("cerrado", "descartado"):
        return f"{seg['id']} está {seg['estado']}: no se puede modificar"
    anterior = seg.get("categoria", "-")
    if anterior == p["categoria"]:
        return f"{seg['id']} ya era {anterior}"
    if p["categoria"] != "comercial" and seg.get("captacion"):
        return ("No se puede recategorizar una CAPTACIÓN fuera de comercial: "
                "primero desmárcala en el panel (botón 👤 Es cliente)")
    seg["categoria"] = p["categoria"]
    seg["fecha_ultimo_movimiento"] = hoy().isoformat()
    seg.setdefault("historial", []).append({
        "fecha": hoy().isoformat(),
        "evento": f"Recategorizado desde el panel: {anterior} → {p['categoria']}",
    })
    memoria.guardar("seguimientos.json", segs, backup=True)
    anadir_registro_mes(datetime.now(), f"{seg.get('cliente_id') or seg['id']}",
                        p["categoria"], "email",
                        f"Seguimiento {seg['id']} recategorizado: "
                        f"{anterior} → {p['categoria']} (panel)", "recategorizado")
    return f"{seg['id']}: {anterior} → {p['categoria']}"


def acc_captacion_paso(p: dict) -> str:
    """Marca un paso del plan de captación como enviado (o lo reabre)."""
    estados = ("pendiente", "borrador_creado", "enviado")
    if p.get("estado") not in estados:
        return f"Estado de paso no permitido: {p.get('estado')}"
    segs = memoria.cargar("seguimientos.json")
    seg = next((s for s in segs["seguimientos"] if s["id"] == p["id"]), None)
    if not seg or not seg.get("captacion"):
        return f"{p['id']} no es una captación activa"
    plan = seg.get("plan_captacion") or {}
    paso = next((x for x in plan.get("pasos", []) if x["n"] == p["n"]), None)
    if not paso:
        return f"El paso {p['n']} no existe en el plan de {p['id']}"
    paso["estado"] = p["estado"]
    if p["estado"] == "enviado":
        paso["fecha_envio"] = hoy().isoformat()
        if seg.get("estado") == "borrador_creado":
            seg["estado"] = "respondido"
            seg["fecha_ultimo_envio"] = hoy().isoformat()
    seg["fecha_ultimo_movimiento"] = hoy().isoformat()
    # paso_actual = primer paso no enviado
    no_enviados = [x for x in plan["pasos"] if x.get("estado") != "enviado"]
    plan["paso_actual"] = no_enviados[0]["n"] if no_enviados else None
    if not no_enviados:
        plan["estado"] = "completado"
        seg.setdefault("historial", []).append({
            "fecha": hoy().isoformat(),
            "evento": "🎯 Plan de captación COMPLETADO (3 pasos enviados)",
        })
    else:
        seg.setdefault("historial", []).append({
            "fecha": hoy().isoformat(),
            "evento": f"Paso {paso['n']} ({paso['concepto']}) → {paso['estado']}",
        })
    memoria.guardar("seguimientos.json", segs, backup=True)
    anadir_registro_mes(datetime.now(), f"{seg.get('cliente_id') or seg['id']}",
                        "comercial", "email",
                        f"Captación {seg['id']}: paso {paso['n']} → {paso['estado']} (panel)",
                        "paso_captacion")
    return f"{seg['id']} paso {paso['n']} → {paso['estado']}"


def acc_captacion_reprogramar(p: dict) -> str:
    """Adelanta/atrasa la fecha de un paso del plan de captación."""
    if not p.get("fecha"):
        return "Indica la nueva fecha del paso"
    segs = memoria.cargar("seguimientos.json")
    seg = next((s for s in segs["seguimientos"] if s["id"] == p["id"]), None)
    if not seg or not seg.get("captacion"):
        return f"{p['id']} no es una captación activa"
    plan = seg.get("plan_captacion") or {}
    paso = next((x for x in plan.get("pasos", []) if x["n"] == p["n"]), None)
    if not paso:
        return f"El paso {p['n']} no existe en el plan de {p['id']}"
    anterior = paso.get("fecha_programada")
    paso["fecha_programada"] = p["fecha"]
    paso["estado"] = "pendiente"
    plan["paso_actual"] = min(x["n"] for x in plan["pasos"] if x.get("estado") != "enviado") \
        if any(x.get("estado") != "enviado" for x in plan["pasos"]) else None
    seg["fecha_ultimo_movimiento"] = hoy().isoformat()
    seg.setdefault("historial", []).append({
        "fecha": hoy().isoformat(),
        "evento": f"Paso {paso['n']} reprogramado: {anterior} → {paso['fecha_programada']}",
    })
    memoria.guardar("seguimientos.json", segs, backup=True)
    anadir_registro_mes(datetime.now(), f"{seg.get('cliente_id') or seg['id']}",
                        "comercial", "email",
                        f"Captación {seg['id']}: paso {paso['n']} reprogramado "
                        f"a {paso['fecha_programada']} (panel)", "reprogramado")
    return f"{seg['id']} paso {paso['n']} → {paso['fecha_programada']}"


def construir_economico(clientes: list, presupuestos: list, ventas: list,
                        config: dict) -> dict:
    """Delegado en scripts/economico.py (compartido con sync.py)."""
    import economico
    return economico.construir_economico(clientes, presupuestos, ventas,
                                         config, hoy_d=hoy())


def acc_set_objetivo(p: dict) -> str:
    monto = p.get("monto")
    try:
        monto = round(float(str(monto).replace(".", "").replace(",", ".")), 2) \
            if str(monto).strip() else None
    except (TypeError, ValueError):
        return "Importe no válido"
    config = memoria.cargar("config.json", {})
    config["objetivo_anual"] = {
        "anno": hoy().year,
        "monto": monto,
        "reparto_mensual": None,   # si se quiere reparto a mano, se edita aquí
    }
    memoria.guardar("config.json", config)
    anadir_registro_mes(datetime.now(), "-", "-", "-",
                        f"Objetivo anual {hoy().year} fijado: "
                        f"{monto:,.0f} €" if monto else "Objetivo anual borrado",
                        "configurado")
    return (f"Objetivo anual {hoy().year} fijado en {monto:,.0f} €"
            .replace(",", ".") if monto else "Objetivo anual borrado")


def acc_crear_venta(p: dict) -> str:
    try:
        importe = round(float(str(p.get("importe", "0")).replace(".", "")
                              .replace(",", ".") or "0"), 2)
    except (TypeError, ValueError):
        return "Importe no válido"
    if not p.get("cliente_id"):
        return "Indica el cliente de la venta"
    if not p.get("fecha"):
        return "Indica la fecha de la venta"
    ventas = memoria.cargar("ventas.json", {"ventas": []})
    maximo = max((int(v["id"].split("-")[1]) for v in ventas["ventas"]), default=0)
    venta = {
        "id": f"VEN-{maximo + 1:04d}",
        "cliente_id": p["cliente_id"],
        "fecha": p["fecha"],
        "importe": importe,
        "descripcion": (p.get("descripcion") or "").strip(),
        "origen": "manual",
        "estado": "activa",
        "creado": datetime.now().isoformat(timespec="seconds"),
    }
    ventas["ventas"].append(venta)
    memoria.guardar("ventas.json", ventas, backup=True)
    anadir_registro_mes(datetime.now(), venta["cliente_id"], "comercial", "-",
                        f"Venta manual registrada: {venta['id']} "
                        f"({importe:,.0f} € el {p['fecha']})".replace(",", "."),
                        "registrada")
    return f"Venta {venta['id']} registrada: {importe:,.2f} € el {p['fecha']}"


def acc_editar_venta(p: dict) -> str:
    ventas = memoria.cargar("ventas.json", {"ventas": []})
    venta = next((v for v in ventas["ventas"] if v["id"] == p["id"]), None)
    if not venta:
        return f"No existe la venta {p.get('id')}"
    if "importe" in p:
        try:
            venta["importe"] = round(float(str(p["importe"]).replace(".", "")
                                           .replace(",", ".") or "0"), 2)
        except (TypeError, ValueError):
            return "Importe no válido"
    if p.get("fecha"):
        venta["fecha"] = p["fecha"]
    if "descripcion" in p:
        venta["descripcion"] = str(p["descripcion"]).strip()
    if p.get("cliente_id"):
        venta["cliente_id"] = p["cliente_id"]
    venta["editado"] = datetime.now().isoformat(timespec="seconds")
    memoria.guardar("ventas.json", ventas, backup=True)
    anadir_registro_mes(datetime.now(), venta["cliente_id"], "comercial", "-",
                        f"Venta {venta['id']} editada desde el panel", "editada")
    return f"Venta {venta['id']} actualizada"


def acc_eliminar_venta(p: dict) -> str:
    ventas = memoria.cargar("ventas.json", {"ventas": []})
    venta = next((v for v in ventas["ventas"] if v["id"] == p["id"]), None)
    if not venta:
        return f"No existe la venta {p.get('id')}"
    # regla: nada se borra sin archivar
    (RAIZ / "datos" / "archivo" / "ventas").mkdir(parents=True, exist_ok=True)
    memoria.guardar(f"archivo/ventas/{venta['id']}_{datetime.now():%Y%m%d_%H%M%S}.json",
                    venta)
    ventas["ventas"] = [v for v in ventas["ventas"] if v["id"] != p["id"]]
    memoria.guardar("ventas.json", ventas, backup=True)
    anadir_registro_mes(datetime.now(), venta["cliente_id"], "comercial", "-",
                        f"Venta {venta['id']} eliminada desde el panel (archivada)",
                        "eliminada")
    return f"Venta {venta['id']} eliminada (archivada en datos/archivo/ventas/)"


def acc_crear_cita(p: dict) -> str:
    """Crea la cita en Google Calendar + la registra en memoria.
    Si tiene seguimiento, lanza orden de cola para el borrador de
    aviso al cliente (nunca invitaciones automáticas)."""
    if not p.get("fecha") or not p.get("hora"):
        return "Indica fecha y hora de la cita"
    servicio = gcal.servicio_calendar()
    dur = int(p.get("duracion_min") or 60)
    evento = {"summary": p.get("titulo") or "Cita",
              "start": {"dateTime": f"{p['fecha']}T{p['hora']}:00",
                        "timeZone": gcal.ZONA_HORARIA},
              "end": {"dateTime": f"{p['fecha']}T{gcal.fin_de_cita(p['hora'], dur)}:00",
                      "timeZone": gcal.ZONA_HORARIA}}
    if p.get("ubicacion"):
        evento["location"] = p["ubicacion"]
    if p.get("descripcion"):
        evento["description"] = p["descripcion"]
    creado = servicio.events().insert(calendarId="primary", body=evento).execute()

    citas = memoria.cargar("citas.json", {"citas": []})
    maximo = max((int(c["id"].split("-")[1]) for c in citas["citas"]), default=0)
    cita = {
        "id": f"CITA-{maximo + 1:04d}",
        "cliente_id": p.get("cliente_id"),
        "seguimiento_id": p.get("seguimiento_id"),
        "titulo": p.get("titulo") or "Cita",
        "fecha": p["fecha"], "hora": p["hora"], "duracion_min": dur,
        "ubicacion": p.get("ubicacion", ""),
        "event_id": creado["id"],
        "estado": "programada",
        "modificaciones": [],
        "resultado": None,
        "borrador_id": None,
        "creado": datetime.now().isoformat(timespec="seconds"),
    }
    citas["citas"].append(cita)
    memoria.guardar("citas.json", citas)

    seg = None
    if cita["seguimiento_id"]:
        segs = memoria.cargar("seguimientos.json")
        seg = next((s for s in segs["seguimientos"]
                    if s["id"] == cita["seguimiento_id"]), None)
        if seg:
            seg.setdefault("historial", []).append({
                "fecha": hoy().isoformat(),
                "evento": f"📅 Cita creada: {cita['titulo']} el {cita['fecha']} "
                          f"a las {cita['hora']}",
            })
            memoria.guardar("seguimientos.json", segs)
    anadir_registro_mes(datetime.now(),
                        f"{cita.get('cliente_id') or '-'}", "-", "-",
                        f"Cita creada: {cita['titulo']} ({cita['fecha']} {cita['hora']})",
                        "programada")

    # borrador de aviso al cliente (si hay hilo al que avisar)
    if seg or cita.get("cliente_id"):
        ACCIONES_DIR.mkdir(exist_ok=True)
        id_acc = siguiente_id("ACC", list(ACCIONES_DIR.glob("ACC-*.json")),
                              r"ACC-(\d+)")
        memoria.guardar(f"acciones/{id_acc}.json", {
            "id": id_acc,
            "creado": datetime.now().isoformat(timespec="seconds"),
            "tipo": "cita_aviso",
            "estado": "pendiente_agente",
            "cita_id": cita["id"],
            "seguimiento_id": cita.get("seguimiento_id"),
            "cliente_id": cita.get("cliente_id"),
            "texto_guia": p.get("texto_guia") or None,
            "accion_cita": "creada",
            "evento_cita": f"{cita['titulo']} el {cita['fecha']} a las {cita['hora']}"
                           + (f" en {cita['ubicacion']}" if cita["ubicacion"] else ""),
        })
        cita["orden_mail"] = id_acc
        memoria.guardar("citas.json", citas)
        _lanzar_procesar_cola()
        return f"Cita {cita['id']} creada en Calendar + orden {id_acc} para el borrador de aviso"
    return f"Cita {cita['id']} creada en Calendar"


def acc_reprogramar_cita(p: dict) -> str:
    citas = memoria.cargar("citas.json", {"citas": []})
    cita = next((c for c in citas["citas"] if c["id"] == p["id"]), None)
    if not cita:
        return f"No existe la cita {p.get('id')}"
    if not p.get("fecha") or not p.get("hora"):
        return "Indica la nueva fecha y hora"
    dur = cita.get("duracion_min", 60)
    gcal.servicio_calendar().events().update(
        calendarId="primary", eventId=cita["event_id"],
        body={"start": {"dateTime": f"{p['fecha']}T{p['hora']}:00",
                        "timeZone": gcal.ZONA_HORARIA},
              "end": {"dateTime": f"{p['fecha']}T{gcal.fin_de_cita(p['hora'], dur)}:00",
                      "timeZone": gcal.ZONA_HORARIA}}).execute()
    cita["fecha"], cita["hora"] = p["fecha"], p["hora"]
    cita["modificaciones"].append({"fecha": hoy().isoformat(),
                                   "tipo": "reprogramada",
                                   "detalle": p.get("texto_guia") or ""})
    _cita_en_historial(cita, f"🔁 Cita reprogramada al {cita['fecha']} {cita['hora']}")
    memoria.guardar("citas.json", citas)
    anadir_registro_mes(datetime.now(), f"{cita.get('cliente_id') or '-'}",
                        "-", "-", f"Cita {cita['id']} reprogramada a {cita['fecha']} {cita['hora']}",
                        "reprogramada")
    return _orden_mail_cita(cita, "reprogramada", p.get("texto_guia"))


def acc_cancelar_cita(p: dict) -> str:
    citas = memoria.cargar("citas.json", {"citas": []})
    cita = next((c for c in citas["citas"] if c["id"] == p["id"]), None)
    if not cita:
        return f"No existe la cita {p.get('id')}"
    try:
        gcal.servicio_calendar().events().delete(
            calendarId="primary", eventId=cita["event_id"]).execute()
    except Exception:
        pass  # si ya no existe en Calendar, la memoria manda
    cita["estado"] = "cancelada"
    cita["modificaciones"].append({"fecha": hoy().isoformat(), "tipo": "cancelada",
                                   "detalle": p.get("texto_guia") or ""})
    _cita_en_historial(cita, f"❌ Cita cancelada"
                       + (f": {p['texto_guia']}" if p.get("texto_guia") else ""))
    memoria.guardar("citas.json", citas)
    anadir_registro_mes(datetime.now(), f"{cita.get('cliente_id') or '-'}",
                        "-", "-", f"Cita {cita['id']} cancelada", "cancelada")
    return _orden_mail_cita(cita, "cancelada", p.get("texto_guia"))


def acc_efectuar_cita(p: dict) -> str:
    citas = memoria.cargar("citas.json", {"citas": []})
    cita = next((c for c in citas["citas"] if c["id"] == p["id"]), None)
    if not cita:
        return f"No existe la cita {p.get('id')}"
    cita["estado"] = "efectuada"
    _cita_en_historial(cita, "✅ Cita efectuada")
    memoria.guardar("citas.json", citas)
    anadir_registro_mes(datetime.now(), f"{cita.get('cliente_id') or '-'}",
                        "-", "-", f"Cita {cita['id']} efectuada", "efectuada")
    return f"Cita {cita['id']} marcada como efectuada"


def acc_resultado_cita(p: dict) -> str:
    citas = memoria.cargar("citas.json", {"citas": []})
    cita = next((c for c in citas["citas"] if c["id"] == p["id"]), None)
    if not cita:
        return f"No existe la cita {p.get('id')}"
    if cita["estado"] != "efectuada":
        return "Solo se registra resultado en citas efectuadas"
    cita["resultado"] = {
        "dio_resultado": bool(p.get("dio_resultado")),
        "venta_id": p.get("venta_id"),
        "presupuesto_id": p.get("presupuesto_id"),
        "nota": p.get("nota") or "",
    }
    _cita_en_historial(cita, "💼 Resultado de la cita: "
                       + ("dio resultado" if p.get("dio_resultado")
                          else "sin resultado")
                       + (f" ({p.get('nota')})" if p.get("nota") else ""))
    memoria.guardar("citas.json", citas)
    anadir_registro_mes(datetime.now(), f"{cita.get('cliente_id') or '-'}",
                        "comercial", "-",
                        f"Resultado de cita {cita['id']}: "
                        + ("con resultado" if p.get("dio_resultado") else "sin resultado"),
                        "registrado")
    return f"Resultado de {cita['id']} registrado"


def _cita_en_historial(cita: dict, evento_txt: str) -> None:
    if not cita.get("seguimiento_id"):
        return
    segs = memoria.cargar("seguimientos.json")
    seg = next((s for s in segs["seguimientos"]
                if s["id"] == cita["seguimiento_id"]), None)
    if seg:
        seg.setdefault("historial", []).append(
            {"fecha": hoy().isoformat(), "evento": evento_txt})
        memoria.guardar("seguimientos.json", segs)


def _orden_mail_cita(cita: dict, accion_cita: str, texto_guia: str | None) -> str:
    """Orden de cola para el borrador de aviso/cambio/cancelación
    al cliente (solo si hay hilo: seguimiento o cliente con mail)."""
    if not cita.get("seguimiento_id") and not cita.get("cliente_id"):
        return f"Cita {cita['id']} {accion_cita} (sin hilo de cliente: sin mail)"
    ACCIONES_DIR.mkdir(exist_ok=True)
    id_acc = siguiente_id("ACC", list(ACCIONES_DIR.glob("ACC-*.json")), r"ACC-(\d+)")
    memoria.guardar(f"acciones/{id_acc}.json", {
        "id": id_acc,
        "creado": datetime.now().isoformat(timespec="seconds"),
        "tipo": "cita_aviso",
        "estado": "pendiente_agente",
        "cita_id": cita["id"],
        "seguimiento_id": cita.get("seguimiento_id"),
        "cliente_id": cita.get("cliente_id"),
        "texto_guia": texto_guia or None,
        "accion_cita": accion_cita,
        "evento_cita": f"{cita['titulo']} el {cita['fecha']} a las {cita['hora']}"
                       + (f" en {cita['ubicacion']}" if cita["ubicacion"] else ""),
    })
    cita["orden_mail"] = id_acc
    citas_mem = memoria.cargar("citas.json", {"citas": []})
    for c in citas_mem["citas"]:
        if c["id"] == cita["id"]:
            c["orden_mail"] = id_acc
    memoria.guardar("citas.json", citas_mem)
    _lanzar_procesar_cola()
    return (f"Cita {cita['id']} {accion_cita} + orden {id_acc} para el borrador al cliente")


def acc_procesar_ahora(p: dict) -> str:
    """Botón ⚡ del panel: lanza la corrida completa en segundo plano
    (con cerradura en corrida.ps1 para no duplicar)."""
    script = RAIZ / "scripts" / "corrida.ps1"
    if not script.exists():
        return "No encuentro scripts/corrida.ps1"
    _lanzar_proceso(["powershell", "-NoProfile", "-ExecutionPolicy",
                     "Bypass", "-File", str(script), "-Silencioso"])
    anadir_registro_mes(datetime.now(), "-", "-", "-",
                        "Corrida manual lanzada desde el panel",
                        "lanzada")
    return "⚡ Corrida lanzada en segundo plano — en 3-5 min verás borradores y datos al día (log en datos/corridas/)"


def acc_importar_clientes(p: dict) -> str:
    """Botón 📥 del panel: importa el Excel de entrada/ y regenera."""
    script = RAIZ / "scripts" / "importar_clientes.ps1"
    if not script.exists():
        return "No encuentro scripts/importar_clientes.ps1"
    pendientes = [f for f in (ENTRADA.glob("*.xls*") if ENTRADA.exists() else [])
                  if f.is_file()] + [f for f in (ENTRADA.glob("*.csv") if ENTRADA.exists() else []) if f.is_file()]
    if not pendientes:
        return "📥 No hay ficheros pendientes en la carpeta entrada/ (suéltalos ahí primero)"
    _lanzar_proceso(["powershell", "-NoProfile", "-ExecutionPolicy",
                     "Bypass", "-File", str(script), "-Silencioso"])
    return "📥 Importación lanzada en segundo plano — el informe saldrá en el panel en ~1 min"


ACCIONES = {
    "vincular": acc_vincular,
    "desvincular": acc_desvincular,
    "crear_cliente": acc_crear_cliente,
    "cambiar_propiedad": acc_cambiar_propiedad,
    "cambiar_tipo": acc_cambiar_tipo,
    "marcar_firmado": acc_marcar_firmado,
    "cambiar_estado_presupuesto": acc_cambiar_estado_presupuesto,
    "responder": acc_responder,
    "reprogramar": acc_reprogramar,
    "estado_programacion": acc_estado_programacion,
    "estado_seguimiento": acc_estado_seguimiento,
    "descartar_seguimiento": acc_descartar_seguimiento,
    "captacion_toggle": acc_captacion_toggle,
    "recategorizar_seguimiento": acc_recategorizar_seguimiento,
    "captacion_paso": acc_captacion_paso,
    "captacion_reprogramar": acc_captacion_reprogramar,
    "set_objetivo": acc_set_objetivo,
    "crear_venta": acc_crear_venta,
    "editar_venta": acc_editar_venta,
    "eliminar_venta": acc_eliminar_venta,
    "crear_cita": acc_crear_cita,
    "reprogramar_cita": acc_reprogramar_cita,
    "cancelar_cita": acc_cancelar_cita,
    "efectuar_cita": acc_efectuar_cita,
    "resultado_cita": acc_resultado_cita,
    "procesar_ahora": acc_procesar_ahora,
    "importar_clientes": acc_importar_clientes,
    "fusionar": acc_fusionar,
}


# ── Servidor HTTP ───────────────────────────────────────────────

class Manejador(BaseHTTPRequestHandler):

    def _json(self, codigo: int, datos) -> None:
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self) -> None:
        ruta = urlparse(self.path).path
        if ruta == "/api/estado":
            self._json(200, construir_estado())
        elif ruta.startswith("/api/hilo/"):
            thread_id = ruta.rsplit("/", 1)[-1]
            try:
                self._json(200, {"ok": True,
                                 "mensajes": gcal.hilo_para_panel(thread_id)})
            except Exception as exc:  # noqa: BLE001
                self._json(500, {"ok": False,
                                 "error": f"No se pudo leer el hilo: {exc}"})
        elif ruta.startswith("/api/ocupacion"):
            params = parse_qs(urlparse(self.path).query)
            fecha = (params.get("fecha") or [""])[0]
            try:
                self._json(200, {"ok": True, "fecha": fecha,
                                 "bloques": gcal.eventos_del_dia(fecha)})
            except Exception as exc:  # noqa: BLE001
                self._json(500, {"ok": False,
                                 "error": f"No se pudo leer la agenda: {exc}"})
        elif ruta.startswith("/api/agenda"):
            eventos = gcal.agenda_proxima(14)
            del_sistema = {c.get("event_id") for c in
                           memoria.cargar("citas.json", {"citas": []})["citas"]}
            for ev in eventos:
                ev["del_sistema"] = ev["event_id"] in del_sistema
            self._json(200, {"ok": True, "eventos": eventos})
        elif ruta in ("/", "/index.html"):
            if INDICE_HTML.exists():
                cuerpo = INDICE_HTML.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)
            else:
                self._json(404, {"error": "falta dashboard/index.html"})
        else:
            self._json(404, {"error": f"ruta desconocida {ruta}"})

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/accion":
            self._json(404, {"error": "ruta desconocida"})
            return
        try:
            largo = int(self.headers.get("Content-Length", 0))
            peticion = json.loads(self.rfile.read(largo).decode("utf-8"))
            tipo = peticion.get("tipo", "")
            if tipo not in ACCIONES:
                self._json(400, {"ok": False, "mensaje": f"Acción desconocida: {tipo}"})
                return
            mensaje = ACCIONES[tipo](peticion)
            self._json(200, {"ok": True, "mensaje": mensaje,
                             "estado": construir_estado()})
        except Exception as exc:  # noqa: BLE001 — responder siempre JSON
            self._json(500, {"ok": False, "mensaje": f"Error interno: {exc}"})

    def log_message(self, formato: str, *args) -> None:  # silenciar logs
        pass


def main() -> int:
    try:
        servidor = ThreadingHTTPServer((HOST, PUERTO), Manejador)
    except OSError:
        print(f"[i] El panel ya está en marcha en http://{HOST}:{PUERTO}")
        return 1
    print(f"[OK] Panel de Gestión en http://{HOST}:{PUERTO}  (Ctrl+C para cerrar)")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\n[OK] Panel cerrado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
