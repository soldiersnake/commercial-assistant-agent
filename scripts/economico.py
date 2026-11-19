# -*- coding: utf-8 -*-
"""economico.py — Cálculos del módulo económico (Fase 5).

Funciones puras compartidas por el servidor del panel (dashboard/)
y el generador del Excel (scripts/sync.py). Solo computa clientes
PROPIOS, como acordamos (los ajenos no son cartera del asesor).
"""
from __future__ import annotations

from datetime import date


def _fecha(valor: str | None) -> date | None:
    if not valor:
        return None
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError:
        return None


def es_bisiesto(anno: int) -> bool:
    return anno % 4 == 0 and (anno % 100 != 0 or anno % 400 == 0)


def construir_economico(clientes: list, presupuestos: list, ventas: list,
                        config: dict, hoy_d: date | None = None) -> dict:
    """ventas = ventas MANUALES del CRUD (presupuestos firmados cuentan
    por su lado como automáticas). Ambas se suman en el total anual,
    en por_mes y en el ranking."""
    hoy_d = hoy_d or date.today()
    anno = hoy_d.year
    fichas = {c["id"]: c for c in clientes}
    propios = {c["id"] for c in clientes if c.get("propiedad") == "propio"}

    embudo = {estado: {"n": 0, "euros": 0.0}
              for estado in ("enviado", "pendiente_firma", "firmado",
                             "rechazado", "anulado")}
    por_mes_auto = [0.0] * 12
    por_mes_manual = [0.0] * 12
    firmado_anno = 0.0        # automáticas (presupuestos firmados)
    manual_anno = 0.0         # manuales (introducidas a mano)
    firmas_cliente: dict[str, dict] = {}
    captacion = []

    for pre in presupuestos:
        cli = fichas.get(pre.get("cliente_id") or "")
        if cli is None or cli["id"] not in propios:
            continue
        estado = pre.get("estado", "")
        importe = pre.get("importe") or 0.0
        if estado in embudo:
            embudo[estado]["n"] += 1
            embudo[estado]["euros"] += importe
        if estado == "firmado":
            fecha_f = _fecha(pre.get("fecha_firma"))
            if fecha_f and fecha_f.year == anno:
                firmado_anno += importe
                por_mes_auto[fecha_f.month - 1] += importe
                dato = firmas_cliente.setdefault(cli["id"], {
                    "cliente_id": cli["id"], "nombre": cli.get("nombre", ""),
                    "n_firmas": 0, "importe": 0.0})
                dato["n_firmas"] += 1
                dato["importe"] += importe
        elif estado == "pendiente_firma" and cli.get("tipo") == "prospecto":
            envio = _fecha(pre.get("fecha_envio"))
            captacion.append({
                "presupuesto_id": pre.get("id", ""),
                "cliente_id": cli["id"], "nombre": cli.get("nombre", ""),
                "titulo": pre.get("titulo", ""), "importe": importe,
                "fecha_envio": pre.get("fecha_envio"),
                "dias_pendiente": (hoy_d - envio).days if envio else None,
                "proxima_reclamacion": pre.get("proxima_reclamacion"),
                "reclamacion_vencida": pre.get("reclamacion_vencida", False),
            })

    for venta in ventas:
        if venta.get("estado", "activa") != "activa":
            continue
        cli = fichas.get(venta.get("cliente_id") or "")
        if cli is None or cli["id"] not in propios:
            continue
        fecha_v = _fecha(venta.get("fecha"))
        importe = venta.get("importe") or 0.0
        if fecha_v and fecha_v.year == anno:
            manual_anno += importe
            por_mes_manual[fecha_v.month - 1] += importe
            dato = firmas_cliente.setdefault(cli["id"], {
                "cliente_id": cli["id"], "nombre": cli.get("nombre", ""),
                "n_firmas": 0, "importe": 0.0})
            dato["n_firmas"] += 1
            dato["importe"] += importe

    por_mes_total = [por_mes_auto[i] + por_mes_manual[i] for i in range(12)]
    total_anno = firmado_anno + manual_anno

    firmados = embudo["firmado"]["n"]
    resueltos = firmados + embudo["rechazado"]["n"]
    tasa = round(100 * firmados / resueltos) if resueltos else None

    objetivo = config.get("objetivo_anual", {}) or {}
    objetivo_monto = objetivo.get("monto") if objetivo.get("anno") == anno else None
    firmado_mes = por_mes_total[hoy_d.month - 1]
    proyeccion = None
    progreso = None
    mes_pct = None
    if objetivo_monto:
        progreso = round(100 * total_anno / objetivo_monto, 1)
        objetivo_mes = objetivo_monto / 12
        mes_pct = round(100 * firmado_mes / objetivo_mes, 1) if objetivo_mes else None
        dias_transcurridos = (hoy_d - date(anno, 1, 1)).days + 1
        dias_anno = 366 if es_bisiesto(anno) else 365
        proyeccion = round(total_anno / dias_transcurridos * dias_anno, 0) \
            if dias_transcurridos and total_anno else 0.0

    ranking = sorted(firmas_cliente.values(),
                     key=lambda r: (-r["importe"], r.get("nombre", "")))[:15]
    captacion.sort(key=lambda c: (-(c["importe"] or 0), -(c["dias_pendiente"] or 0)))
    potencial = embudo["pendiente_firma"]["euros"] + \
        sum(c["importe"] or 0 for c in captacion)

    return {
        "anno": anno,
        "objetivo_monto": objetivo_monto,
        "firmado_anno": firmado_anno,
        "manual_anno": manual_anno,
        "total_anno": total_anno,
        "firmado_mes": firmado_mes,
        "por_mes": por_mes_total,
        "por_mes_auto": por_mes_auto,
        "por_mes_manual": por_mes_manual,
        "embudo": embudo,
        "tasa_firma": tasa,
        "ranking": ranking,
        "captacion": captacion,
        "potencial": potencial,
        "proyeccion": proyeccion,
        "progreso": progreso,
        "mes_pct": mes_pct,
    }
