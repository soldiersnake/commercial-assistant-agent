# -*- coding: utf-8 -*-
"""sync.py — Genera las VISTAS desde la memoria (datos/).

Hoy genera el Excel de gestión `excel/gestion_clientes.xlsx` con
hojas: Clientes · Seguimientos · Presupuestos · Programaciones ·
Resumen. Más adelante este mismo script también refrescará el
dashboard. Las vistas NUNCA se editan a mano: se regeneran aquí.

Uso:  .venv\\Scripts\\python.exe scripts\\sync.py
"""
from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import memoria  # noqa: E402
import economico  # noqa: E402

from openpyxl import Workbook  # noqa: E402
from openpyxl.styles import Alignment, Font, PatternFill  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402

EXCEL_DIR = RAIZ / "excel"

AZUL = "1F4E78"
GRIS = "F2F2F2"
ROJO = "C00000"
AMBAR = "BF8F00"


def hoy() -> date:
    return date.today()


def fecha_iso_a_date(valor: str | None) -> date | None:
    if not valor:
        return None
    try:
        return date.fromisoformat(valor[:10])
    except ValueError:
        return None


def fmt(valor: str | None) -> str:
    """ISO → dd/mm/aaaa legible."""
    d = fecha_iso_a_date(valor)
    return d.strftime("%d/%m/%Y") if d else ""


def dias_desde(valor: str | None) -> int | None:
    d = fecha_iso_a_date(valor)
    return (hoy() - d).days if d else None


def nombre_cliente(id_cliente: str | None, indice: dict) -> str:
    if not id_cliente:
        return ""
    return f"{id_cliente} {indice.get(id_cliente, '(desconocido)')}"


# ── Estilos ──────────────────────────────────────────────────────

def cabecera(hoja, titulos: list[str]) -> None:
    for j, titulo in enumerate(titulos, start=1):
        celda = hoja.cell(row=1, column=j, value=titulo)
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor=AZUL)
        celda.alignment = Alignment(horizontal="center", vertical="center",
                                    wrap_text=True)
    hoja.freeze_panes = "A2"
    hoja.auto_filter.ref = f"A1:{get_column_letter(len(titulos))}1"
    hoja.row_dimensions[1].height = 26


def anchos(hoja, anchos_cols: list[int]) -> None:
    for j, ancho in enumerate(anchos_cols, start=1):
        hoja.column_dimensions[get_column_letter(j)].width = ancho


def resaltar(celda, color: str, negrita: bool = False) -> None:
    if color:
        celda.fill = PatternFill("solid", fgColor=color)
    if negrita:
        celda.font = Font(bold=True)


# ── Hojas ────────────────────────────────────────────────────────

def hoja_clientes(libro: Workbook, maestro: dict) -> None:
    hoja = libro.active
    hoja.title = "Clientes"
    titulos = ["ID", "Cód. empresa", "Nombre", "Tipo", "Propiedad",
               "Población", "Domicilio", "Emails", "Teléfonos",
               "Edificios", "Últ. interacción", "Estado", "Notas"]
    cabecera(hoja, titulos)
    for cli in maestro["clientes"]:
        emails = [f["valor"] for f in cli["fichas_contacto"] if f["tipo"] == "email"]
        tels = [f["valor"] for f in cli["fichas_contacto"] if f["tipo"] == "telefono"]
        edificios = ", ".join(e["nombre"] for e in cli.get("edificios", []))
        fila = hoja.max_row + 1
        valores = [cli["id"], cli.get("codigo_empresa", ""), cli["nombre"],
                   cli["tipo"], cli["propiedad"], cli.get("poblacion", ""),
                   cli.get("direccion", ""), "; ".join(emails), "; ".join(tels),
                   edificios, fmt(cli.get("fecha_ultima_interaccion")),
                   cli.get("estado_seguimiento", ""), cli.get("notas", "")]
        for j, valor in enumerate(valores, start=1):
            celda = hoja.cell(row=fila, column=j, value=valor)
            if cli.get("demo"):
                resaltar(celda, GRIS)
            if j == 5:  # propiedad
                resaltar(celda, "D9E1F2" if valor == "propio" else "FCE4D6")
            if j == 13 and valor == "pendiente_respuesta":
                resaltar(celda, "FBE2D5")
    anchos(hoja, [10, 11, 32, 10, 10, 13, 30, 34, 26, 18, 13, 12, 18, 36])


def hoja_seguimientos(libro: Workbook, seguimientos: dict, indice_cli: dict) -> None:
    hoja = libro.create_sheet("Seguimientos")
    titulos = ["ID", "Cliente", "Fecha apertura", "Descripción", "Tipo",
               "Categoría", "Prioridad", "Edificio", "Estado",
               "Presup. pedido", "Últ. interacción", "Últ. envío",
               "Días sin responder", "Próximo paso", "Origen",
               "Captación", "Paso del plan"]
    cabecera(hoja, titulos)
    ETIQUETAS_ESTADO = {"pendiente_respuesta": "⏳ Pendiente",
                        "borrador_creado": "🟡 En borrador",
                        "respondido": "✅ Respondido",
                        "descartado": "🚫 Descartado",
                        "cerrado": "Cerrado"}
    orden = {"alta": 0, "media": 1, "baja": 2, None: 3}
    registros = sorted(seguimientos["seguimientos"],
                       key=lambda s: (orden.get(s.get("prioridad"), 3),
                                      -(dias_desde(s.get("fecha_ultima_interaccion")
                                                   or s.get("fecha_ultimo_movimiento")) or 0)))
    for seg in registros:
        estado = seg.get("estado", "pendiente_respuesta")
        pendiente = estado in ("pendiente_respuesta", "borrador_creado")
        dias = dias_desde(seg.get("fecha_ultima_interaccion")
                          or seg.get("fecha_ultimo_movimiento")) if pendiente else None
        presupuesto = seg.get("presupuesto", {})
        motivo_desc = seg.get("motivo_descarte") or ""
        desc_txt = (seg.get("descripcion") or seg.get("asunto", ""))
        if motivo_desc:
            desc_txt = f"{desc_txt} 🚫 Descartado: {motivo_desc}"
        plan_cap = seg.get("plan_captacion") or {}
        paso_txt = ""
        if seg.get("captacion") and plan_cap.get("pasos"):
            no_enviados = [p for p in plan_cap["pasos"] if p.get("estado") != "enviado"]
            if no_enviados:
                p_paso = no_enviados[0]
                paso_txt = (f"{p_paso['n']}/3 {p_paso.get('concepto', '')} "
                            f"({fmt(p_paso.get('fecha_programada'))})")
            else:
                paso_txt = "3/3 completado"
        fila = hoja.max_row + 1
        valores = [
            seg["id"], nombre_cliente(seg.get("cliente_id"), indice_cli),
            fmt(seg.get("fecha_apertura")),
            desc_txt,
            "NUEVO" if seg.get("nuevo") else f"continúa ({seg.get('continua_de')})",
            seg.get("categoria", ""), (seg.get("prioridad") or "").upper(),
            seg.get("edificio") or "", ETIQUETAS_ESTADO.get(estado, estado),
            "Sí" if presupuesto.get("pedido") else "",
            fmt(seg.get("fecha_ultima_interaccion") or seg.get("fecha_ultimo_movimiento")),
            fmt(seg.get("fecha_ultimo_envio")),
            dias if dias is not None else "",
            seg.get("proximo_paso", ""), seg.get("correo_origen", ""),
            "🎯 Sí" if seg.get("captacion") else "", paso_txt,
        ]
        for j, valor in enumerate(valores, start=1):
            celda = hoja.cell(row=fila, column=j, value=valor)
            if seg.get("categoria") == "empresa":
                resaltar(celda, "E4DFEC")           # morado: interno
            elif estado == "borrador_creado":
                resaltar(celda, "FFF2CC")           # amarillo: borrador por enviar
            elif pendiente:
                if seg.get("prioridad") == "alta":
                    resaltar(celda, "F8CBAD")       # naranja: urgente
                elif dias is not None and dias >= 7:
                    resaltar(celda, "FFF2CC")       # amarillo: >7 días
            if j == 9 and estado in ("pendiente_respuesta", "borrador_creado"):
                celda.font = Font(bold=True)


def hoja_presupuestos(libro: Workbook, presupuestos: dict, indice_cli: dict,
                      reglas: dict) -> None:
    hoja = libro.create_sheet("Presupuestos")
    titulos = ["ID", "Cliente", "Referencia", "Título", "Importe (€)",
               "Fecha envío", "Vencimiento", "Fecha reclamación",
               "Próx. reclamación", "Nº reclamaciones", "Estado",
               "Fecha firma", "Notas"]
    cabecera(hoja, titulos)
    intervalo = reglas.get("intervalo_reclamacion_dias", 15)
    for pre in presupuestos["presupuestos"]:
        hechas = [r for r in pre.get("reclamaciones", [])
                  if r.get("estado") in ("enviada", "borrador_creado")]
        base = fecha_iso_a_date(pre.get("fecha_reclamacion"))
        proxima = ""
        if pre.get("estado") == "pendiente_firma" and base:
            prox = date.fromordinal(base.toordinal() + len(hechas) * intervalo)
            proxima = prox.strftime("%d/%m/%Y")
            if prox < hoy():
                proxima = f"{proxima} ¡VENCIDA!"
        fila = hoja.max_row + 1
        valores = [
            pre["id"], nombre_cliente(pre.get("cliente_id"), indice_cli),
            pre.get("referencia", ""), pre.get("titulo", ""),
            pre.get("importe", ""), fmt(pre.get("fecha_envio")),
            fmt(pre.get("fecha_vencimiento")), fmt(pre.get("fecha_reclamacion")),
            proxima, len(pre.get("reclamaciones", [])),
            pre.get("estado", ""), fmt(pre.get("fecha_firma")),
            pre.get("notas", ""),
        ]
        for j, valor in enumerate(valores, start=1):
            celda = hoja.cell(row=fila, column=j, value=valor)
            estado = pre.get("estado")
            if j == 11:
                color = {"pendiente_firma": "FFF2CC", "firmado": "C6EFCE",
                         "rechazado": "F8CBAD", "anulado": GRIS}.get(estado)
                resaltar(celda, color, negrita=True)
            if pre.get("estado") == "pendiente_firma" and "¡VENCIDA!" in str(proxima) \
                    and j in (8, 9, 10, 11):
                resaltar(celda, "FFC7CE")


def hoja_programaciones(libro: Workbook, programaciones: dict,
                        indice_cli: dict) -> None:
    hoja = libro.create_sheet("Programaciones")
    titulos = ["ID", "Cliente", "Asunto", "Fecha programada", "Hora",
               "Estado", "Borrador creado"]
    cabecera(hoja, titulos)
    registros = sorted(programaciones["programaciones"],
                       key=lambda p: p.get("fecha_programada") or "")
    for prog in registros:
        fila = hoja.max_row + 1
        valores = [
            prog["id"], nombre_cliente(prog.get("cliente_id"), indice_cli),
            prog.get("asunto", ""), fmt(prog.get("fecha_programada")),
            prog.get("hora_programada", ""), prog.get("estado", ""),
            "Sí" if prog.get("borrador_creado") else "",
        ]
        for j, valor in enumerate(valores, start=1):
            celda = hoja.cell(row=fila, column=j, value=valor)
            estado = prog.get("estado")
            if j == 6:
                color = {"pendiente": "DDEBF7", "avisado": "DDEBF7",
                         "vencido": "FFC7CE", "completado": "C6EFCE",
                         "cancelado": GRIS}.get(estado)
                resaltar(celda, color, negrita=(estado == "vencido"))
            # vencida = fecha pasada y no completada ni cancelada
            fp = fecha_iso_a_date(prog.get("fecha_programada"))
            if fp and fp < hoy() and estado not in ("completado", "cancelado") and j != 6:
                resaltar(celda, "FFC7CE")


def hoja_economico(libro: Workbook, economico: dict, maestro: dict) -> None:
    hoja = libro.create_sheet("Economico")
    anchos(hoja, [46, 16, 16, 34])
    fila = 1

    def titulo(texto: str) -> None:
        nonlocal fila
        celda = hoja.cell(row=fila, column=1, value=texto)
        celda.font = Font(bold=True, color="FFFFFF", size=12)
        celda.fill = PatternFill("solid", fgColor=AZUL)
        fila += 1

    def linea(etiqueta: str, valor, color: str = "", negrita: bool = False) -> None:
        nonlocal fila
        hoja.cell(row=fila, column=1, value=etiqueta)
        celda = hoja.cell(row=fila, column=2, value=valor)
        resaltar(celda, color, negrita)
        fila += 1

    e = economico
    titulo(f"EMBUDO DE PRESUPUESTOS {e['anno']} (solo clientes propios)")
    for estado in ("enviado", "pendiente_firma", "firmado", "rechazado", "anulado"):
        dato = e["embudo"][estado]
        linea(f"  · {estado}", f"{dato['n']}  ({dato['euros']:,.0f} €)".replace(",", "."))
    linea("Tasa de firma", f"{e['tasa_firma']}%" if e["tasa_firma"] is not None else "—")
    fila += 1

    titulo(f"OBJETIVO ANUAL {e['anno']}")
    if e["objetivo_monto"]:
        linea("Objetivo", f"{e['objetivo_monto']:,.0f} €".replace(",", "."))
        linea("Firmado en el año",
              f"{e['firmado_anno']:,.0f} € ({e['progreso']}%)".replace(",", "."),
              negrita=True)
        linea("Firmado este mes",
              f"{e['firmado_mes']:,.0f} € ({e['mes_pct']}% del objetivo mensual)".replace(",", "."))
        if e["proyeccion"] is not None:
            linea("Proyección a fin de año",
                  f"{e['proyeccion']:,.0f} €".replace(",", "."))
    else:
        linea("Objetivo", "sin fijar (se fija desde el panel)")
    fila += 1

    titulo(f"RANKING ANUAL DE FIRMAS {e['anno']}")
    if e["ranking"]:
        for i, r in enumerate(e["ranking"], start=1):
            linea(f"  {i}. {r['nombre']}",
                  f"{r['n_firmas']} firma(s) · {r['importe']:,.0f} €".replace(",", "."),
                  color="C6EFCE" if i <= 3 else "")
    else:
        linea("Sin firmas registradas este año", "")
    fila += 1

    titulo("CAPTACIÓN: DINERO EN JUEGO (prospectos con oferta sin firmar)")
    if e["captacion"]:
        for c in e["captacion"]:
            linea(f"  · {c['nombre']} — {(c['titulo'] or c['presupuesto_id'])[:40]}",
                  f"{(c['importe'] or 0):,.0f} € · {c['dias_pendiente'] or 0} días".replace(",", "."),
                  color="F8CBAD" if (c["dias_pendiente"] or 0) >= 15 else "")
    else:
        linea("Sin ofertas de captación pendientes", "")
    fila += 1

    titulo(f"VENTAS FACTURADAS {e['anno']} — POR MES")
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
             "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    for i in range(12):
        if e["por_mes"][i] or e["por_mes_manual"][i]:
            linea(f"  · {meses[i]}",
                  f"total {e['por_mes'][i]:,.0f} € "
                  f"(auto {e['por_mes_auto'][i]:,.0f} € · manual {e['por_mes_manual'][i]:,.0f} €)"
                  .replace(",", "."),
                  negrita=(i == (hoy().month - 1)))
    linea("Total del año",
          f"{e['total_anno']:,.0f} € (auto {e['firmado_anno']:,.0f} € · "
          f"manual {e['manual_anno']:,.0f} €)".replace(",", "."),
          negrita=True)
    fila += 1

    titulo("VENTAS MANUALES REGISTRADAS (introducidas a mano)")
    fichas = {c["id"]: c.get("nombre", "") for c in maestro["clientes"]}
    manuales = sorted(economico.get("ventas_manual", []),
                      key=lambda v: v.get("fecha") or "", reverse=True)
    if manuales:
        for v in manuales:
            linea(f"  · {v.get('fecha', '')} — {fichas.get(v.get('cliente_id'), v.get('cliente_id'))}",
                  f"{(v.get('importe') or 0):,.0f} € · {(v.get('descripcion') or '')[:40]}".replace(",", "."))
    else:
        linea("Sin ventas manuales registradas", "")
    fila += 1

    hoja.cell(row=fila, column=1,
              value=f"Generado automáticamente el {datetime.now():%d/%m/%Y %H:%M} — no editar a mano")


def hoja_citas(libro: Workbook, citas: dict, maestro: dict) -> None:
    hoja = libro.create_sheet("Citas")
    anchos(hoja, [10, 11, 12, 7, 30, 22, 26, 13, 14, 30])
    cabecera(hoja, ["ID", "Fecha", "Hora", "Dur.", "Título", "Cliente",
                    "Ubicación", "Estado", "Mods", "Resultado"])
    fichas = {c["id"]: c.get("nombre", "") for c in maestro["clientes"]}
    registros = sorted(citas["citas"],
                       key=lambda c: ((c.get("fecha") or ""), (c.get("hora") or "")))
    for cita in registros:
        fila = hoja.max_row + 1
        resultado = ""
        if cita.get("resultado"):
            r = cita["resultado"]
            resultado = ("con resultado" if r.get("dio_resultado")
                         else "sin resultado")
            if r.get("nota"):
                resultado += f" — {r['nota']}"
            if r.get("venta_id"):
                resultado += f" ({r['venta_id']})"
        valores = [cita["id"], fmt(cita.get("fecha")), cita.get("hora", ""),
                   cita.get("duracion_min", 60), cita.get("titulo", ""),
                   fichas.get(cita.get("cliente_id"), cita.get("cliente_id") or ""),
                   cita.get("ubicacion", ""), cita.get("estado", ""),
                   len(cita.get("modificaciones", [])), resultado]
        for j, valor in enumerate(valores, start=1):
            celda = hoja.cell(row=fila, column=j, value=valor)
            estado = cita.get("estado", "")
            if j == 8:
                resaltar(celda, {"programada": "DDEBF7", "efectuada": "C6EFCE",
                                 "cancelada": "FFC7CE"}.get(estado), negrita=True)


def hoja_resumen(libro: Workbook, maestro: dict, seguimientos: dict,
                 presupuestos: dict, programaciones: dict,
                 identidad: dict, economico_datos: dict) -> None:
    hoja = libro.create_sheet("Resumen")
    anchos(hoja, [46, 16, 16, 30])
    fila = 1

    def titulo(texto: str) -> None:
        nonlocal fila
        celda = hoja.cell(row=fila, column=1, value=texto)
        celda.font = Font(bold=True, color="FFFFFF", size=12)
        celda.fill = PatternFill("solid", fgColor=AZUL)
        fila += 1

    def linea(etiqueta: str, valor, color: str = "", negrita: bool = False) -> None:
        nonlocal fila
        hoja.cell(row=fila, column=1, value=etiqueta)
        celda = hoja.cell(row=fila, column=2, value=valor)
        resaltar(celda, color, negrita)
        fila += 1

    clientes = maestro["clientes"]
    propios = [c for c in clientes if c.get("propiedad") == "propio"]
    ajenos = [c for c in clientes if c.get("propiedad") == "ajeno"]
    prospectos = [c for c in propios if c.get("tipo") == "prospecto"]

    titulo("CLIENTES")
    linea("Total cartera", len(clientes))
    linea("Propios", len(propios))
    linea("Ajenos (compartidos)", len(ajenos))
    linea("Prospectos de captación (propios)", len(prospectos))
    linea("Contactos sin vincular (❓)",
          len(identidad.get("sin_vincular", [])),
          color="FFC7CE" if identidad.get("sin_vincular") else "")
    fila += 1

    titulo("SEGUIMIENTOS")
    abiertos = [s for s in seguimientos["seguimientos"]
                if s.get("estado") not in ("cerrado", "descartado")]
    pendientes = [s for s in abiertos if s.get("estado") == "pendiente_respuesta"]
    linea("Abiertos", len(abiertos))
    linea("Pendientes de respuesta", len(pendientes),
          color="FFF2CC" if pendientes else "", negrita=True)
    en_borrador = [s for s in abiertos if s.get("estado") == "borrador_creado"]
    linea("En borrador (por enviar)", len(en_borrador),
          color="FFF2CC" if en_borrador else "")
    for categoria in ("tecnico", "facturacion", "trabajos_pendientes",
                      "comercial", "empresa"):
        n = sum(1 for s in abiertos if s.get("categoria") == categoria)
        if n:
            linea(f"  · {categoria}", n)
    captaciones = [s for s in abiertos if s.get("captacion")]
    if captaciones:
        pasos_vencidos = 0
        for s_cap in captaciones:
            plan = s_cap.get("plan_captacion") or {}
            for p_paso in plan.get("pasos", []):
                if p_paso.get("estado") in ("pendiente", "borrador_creado"):
                    d_paso = fecha_iso_a_date(p_paso.get("fecha_programada"))
                    if d_paso and d_paso <= hoy():
                        pasos_vencidos += 1
        linea("🎯 Captaciones activas", len(captaciones))
        linea("Pasos de captación vencidos", pasos_vencidos,
              color="FFC7CE" if pasos_vencidos else "")
    urgentes = [s for s in pendientes if s.get("prioridad") == "alta"]
    linea("Urgentes (prioridad alta)", len(urgentes),
          color="F8CBAD" if urgentes else "", negrita=True)
    viejos = [s for s in pendientes
              if (dias_desde(s.get("fecha_ultima_interaccion")) or 0) >= 7]
    linea("Sin responder más de 7 días", len(viejos),
          color="FFF2CC" if viejos else "")
    fila += 1

    titulo("PRESUPUESTOS")
    estados = {}
    importes = {}
    for pre in presupuestos["presupuestos"]:
        estado = pre.get("estado", "")
        estados[estado] = estados.get(estado, 0) + 1
        importes[estado] = importes.get(estado, 0) + (pre.get("importe") or 0)
    for estado in ("firmado", "pendiente_firma", "enviado", "rechazado", "anulado"):
        if estado in estados:
            linea(f"  · {estado}",
                  f"{estados[estado]}  ({importes[estado]:,.0f} €)".replace(",", "."))
    pend_firma = economico_datos["embudo"]["pendiente_firma"]["euros"]
    linea("Total pendiente de firma", f"{pend_firma:,.0f} €".replace(",", "."),
          negrita=True)
    linea("Firmado en el año (auto + manual)",
          f"{economico_datos['total_anno']:,.0f} €".replace(",", "."),
          negrita=True)
    fila += 1

    titulo("PROGRAMACIONES")
    abiertas = [p for p in programaciones["programaciones"]
                if p.get("estado") not in ("completado", "cancelado")]
    vencidas = [p for p in abiertas
                if (fecha_iso_a_date(p.get("fecha_programada")) or hoy()) < hoy()]
    prox7 = [p for p in abiertas
             if p.get("fecha_programada")
             and 0 <= (fecha_iso_a_date(p["fecha_programada"]) - hoy()).days <= 7]
    linea("Abiertas", len(abiertas))
    linea("Próximos 7 días", len(prox7), color="DDEBF7")
    linea("VENCIDAS SIN ENVIAR", len(vencidas),
          color="FFC7CE" if vencidas else "", negrita=True)

    # pie
    fila += 1
    hoja.cell(row=fila, column=1,
              value=f"Generado automáticamente el {datetime.now():%d/%m/%Y %H:%M} — no editar a mano")


def main() -> int:
    maestro = memoria.cargar("maestro_clientes.json", {"clientes": []})
    seguimientos = memoria.cargar("seguimientos.json", {"seguimientos": []})
    presupuestos = memoria.cargar("presupuestos.json", {"presupuestos": []})
    programaciones = memoria.cargar("programaciones.json", {"programaciones": []})
    ventas = memoria.cargar("ventas.json", {"ventas": []})
    identidad = memoria.cargar("identidad.json", {"mapeo": {}, "sin_vincular": []})
    config = memoria.cargar("config.json", {})

    indice_cli = {c["id"]: c["nombre"] for c in maestro["clientes"]}

    libro = Workbook()
    hoja_clientes(libro, maestro)
    hoja_seguimientos(libro, seguimientos, indice_cli)
    hoja_presupuestos(libro, presupuestos, indice_cli,
                      config.get("reglas_presupuestos", {}))
    economico_datos = economico.construir_economico(
        maestro["clientes"], presupuestos["presupuestos"], ventas["ventas"], config)
    economico_datos["ventas_manual"] = [v for v in ventas["ventas"]
                                        if v.get("estado", "activa") == "activa"]
    hoja_economico(libro, economico_datos, maestro)
    hoja_citas(libro, memoria.cargar("citas.json", {"citas": []}), maestro)
    hoja_programaciones(libro, programaciones, indice_cli)
    hoja_resumen(libro, maestro, seguimientos, presupuestos,
                 programaciones, identidad, economico_datos)

    EXCEL_DIR.mkdir(exist_ok=True)
    destino = EXCEL_DIR / "gestion_clientes.xlsx"
    libro.save(destino)
    print(f"[OK] Excel generado: {destino}")
    print(f"     {len(maestro['clientes'])} clientes · "
          f"{len(seguimientos['seguimientos'])} seguimientos · "
          f"{len(presupuestos['presupuestos'])} presupuestos · "
          f"{len(programaciones['programaciones'])} programaciones")
    return 0


if __name__ == "__main__":
    sys.exit(main())
