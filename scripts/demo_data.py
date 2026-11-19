# -*- coding: utf-8 -*-
"""demo_data.py — Genera un dataset FICTICIO en datos/ para probar el
sistema sin tener datos reales de ningún cliente.

Todo lo que genera usa nombres, direcciones, teléfonos y correos
inventados. Ideal para: primeras pruebas, capturas, demostraciones.

Uso:
    python scripts/demo_data.py            # genera (con backup si ya había datos)
    python scripts/demo_data.py --solo     # no sobreescribe si ya existe config.json

El dataset se generó pensado para el panel (dashboard/): pendientes,
borradores, presupuestos con reclamación, captaciones con plan de 3
pasos, ventas, citas y programaciones.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
HOY = date.today()

AVISO = ("Estos datos son FICTICIOS (generados por scripts/demo_data.py). "
         "Cuando importes tu cartera real, el importador los sustituirá.")


def f(offset: int) -> str:
    """Fecha relativa a hoy en ISO (offset en días)."""
    return (HOY + timedelta(days=offset)).isoformat()


def demo_config() -> dict:
    return {
        "_comentario": AVISO,
        "empresa": {
            "nombre": "Eleva Servicios S.L.",
            "dominios": ["elevaservicios.com"],
            "contactos_corporativos": [
                {"nombre": "Marta Ruiz", "email": "averias@elevaservicios.com",
                 "area": "Averías 24 h / Reclamaciones", "telefono": "600 111 222"},
                {"nombre": "Joan Peris", "email": "administracion@elevaservicios.com",
                 "area": "Administración — estado de trabajos", "telefono": None},
                {"nombre": "Silvia Redondo", "email": "facturacion@elevaservicios.com",
                 "area": "Facturación", "telefono": None},
                {"nombre": "Pablo Navarro", "email": "tecnico@elevaservicios.com",
                 "area": "Departamento técnico", "telefono": None},
            ],
        },
        "asesor": {
            "nombre": "Alex Ferrer",
            "cargo": "Asesor comercial",
            "email": "alex.ferrer@elevaservicios.com",
        },
        "reglas_presupuestos": {
            "ventana_firma_default_dias": 90,
            "intervalo_reclamacion_dias": 15,
            "max_reclamaciones": None,
        },
        "reglas_captacion": {"dias_paso2": 7, "dias_paso3": 15},
        "objetivo_anual": {"anno": HOY.year, "monto": 120000.0, "reparto_mensual": None},
        "regex_vencimiento": "Vencimiento\\s*([0-9]{1,2}-[0-9]{1,2}-[0-9]{2,4})",
        "automatizacion": {"corridas": ["07:00", "16:00"], "modo": "agentic-headless"},
    }


def demo_clientes() -> dict:
    return {"version": 1, "clientes": [
        {"id": "CLI-0001", "nombre": "Comunidad C/ Alcalde Reig, 8 (Valencia)",
         "tipo": "cliente", "propiedad": "propio", "estado_seguimiento": "activo",
         "direccion": "C/ Alcalde Reig, 8", "poblacion": "Valencia", "cp": "46006",
         "codigo_empresa": "demo-001", "demo": True,
         "fecha_alta": f(-400), "fecha_primera_contactacion": f(-380),
         "fecha_ultima_interaccion": f(-1),
         "fichas_contacto": [
             {"tipo": "telefono", "valor": "600 123 456", "nombre": "Presidencia", "verificado": True},
             {"tipo": "email", "valor": "admin.reig8@example.com", "nombre": "Administrador", "verificado": True}],
         "edificios": [], "notas": "2 ascensores (escalera A y B). Cliente desde hace años."},
        {"id": "CLI-0002", "nombre": "Residencial Los Chopos (Torrent)",
         "tipo": "cliente", "propiedad": "propio", "estado_seguimiento": "activo",
         "direccion": "Av. Olivar del Silo, 22", "poblacion": "Torrent", "cp": "46900",
         "codigo_empresa": "demo-002", "demo": True,
         "fecha_alta": f(-300), "fecha_primera_contactacion": f(-280),
         "fecha_ultima_interaccion": f(-20),
         "fichas_contacto": [
             {"tipo": "email", "valor": "presidencia.chopos@example.com", "nombre": "Presidenta", "verificado": True}],
         "edificios": [], "notas": "Contrato de mantenimiento vence en ~2 meses. Presupuesto en firma."},
        {"id": "CLI-0003", "nombre": "Edificio Mirasol (Paterna)",
         "tipo": "cliente", "propiedad": "propio", "estado_seguimiento": "activo",
         "direccion": "C/ Blasco Ibáñez, 14", "poblacion": "Paterna", "cp": "46980",
         "codigo_empresa": "demo-003", "demo": True,
         "fecha_alta": f(-500), "fecha_primera_contactacion": f(-480),
         "fecha_ultima_interaccion": f(-3),
         "fichas_contacto": [
             {"tipo": "telefono", "valor": "600 234 567", "nombre": "Administración", "verificado": True}],
         "edificios": [], "notas": "Firmó mantenimiento confort este año."},
        {"id": "CLI-0004", "nombre": "Grupo Textil Sorolla S.L. (Valencia)",
         "tipo": "cliente", "propiedad": "propio", "estado_seguimiento": "activo",
         "direccion": "C/ Ruiz de Lihory, 3", "poblacion": "Valencia", "cp": "46015",
         "codigo_empresa": "demo-004", "demo": True,
         "fecha_alta": f(-200), "fecha_primera_contactacion": f(-190),
         "fecha_ultima_interaccion": f(-2),
         "fichas_contacto": [
             {"tipo": "email", "valor": "compras@textilsorolla.example.com", "nombre": "Compras", "verificado": True},
             {"tipo": "telefono", "valor": "600 345 678", "nombre": "Gerencia", "verificado": True}],
         "edificios": [], "notas": "Montacargas y 1 ascensor de personal."},
        {"id": "CLI-0005", "nombre": "Comunidad Av. del Puerto, 120 (Valencia)",
         "tipo": "prospecto", "propiedad": "ajeno", "estado_seguimiento": "captacion",
         "direccion": "Av. del Puerto, 120", "poblacion": "Valencia", "cp": "46022",
         "codigo_empresa": "demo-005", "demo": True,
         "fecha_alta": f(-25), "fecha_primera_contactacion": f(-12),
         "fecha_ultima_interaccion": f(-2),
         "fichas_contacto": [
             {"tipo": "email", "valor": "administrador.puerto120@example.com", "nombre": "Administrador", "verificado": True}],
         "edificios": [], "notas": "Edificio ajeno con mantenedor que va tarde en averías. Captación."},
        {"id": "CLI-0006", "nombre": "Cdad. Prop. C/ Sagunto, 45 (Valencia)",
         "tipo": "prospecto", "propiedad": "propio", "estado_seguimiento": "captacion",
         "direccion": "C/ Sagunto, 45", "poblacion": "Valencia", "cp": "46009",
         "codigo_empresa": "demo-006", "demo": True,
         "fecha_alta": f(-15), "fecha_primera_contactacion": f(-9),
         "fecha_ultima_interaccion": f(-1),
         "fichas_contacto": [
             {"tipo": "email", "valor": "sagunto45@example.com", "nombre": "Presidencia", "verificado": True}],
         "edificios": [], "notas": "Cliente que pidió información y aún no tiene contrato."},
        {"id": "CLI-0007", "nombre": "Residencial Turia Verde (Mislata)",
         "tipo": "cliente", "propiedad": "propio", "estado_seguimiento": "activo",
         "direccion": "C/ Cuenca, 11", "poblacion": "Mislata", "cp": "46920",
         "codigo_empresa": "demo-007", "demo": True,
         "fecha_alta": f(-600), "fecha_primera_contactacion": f(-590),
         "fecha_ultima_interaccion": f(-40),
         "fichas_contacto": [
             {"tipo": "telefono", "valor": "600 456 789", "nombre": "Conserjería", "verificado": True}],
         "edificios": [], "notas": "Revisión semestral programada."},
        {"id": "CLI-0008", "nombre": "Hotel Playa Azul (Valencia)",
         "tipo": "cliente", "propiedad": "ajeno", "estado_seguimiento": "inactivo",
         "direccion": "Paseo Marítimo, 55", "poblacion": "Valencia", "cp": "46011",
         "codigo_empresa": "demo-008", "demo": True,
         "fecha_alta": f(-700), "fecha_primera_contactacion": f(-650),
         "fecha_ultima_interaccion": f(-90),
         "fichas_contacto": [
             {"tipo": "email", "valor": "mantenimiento@playaazul.example.com", "nombre": "Mantenimiento", "verificado": False}],
         "edificios": [], "notas": "Edificio ajeno, caso cerrado sin avance."},
    ]}


def demo_seguimientos() -> dict:
    return {"version": 1, "seguimientos": [
        {"id": "SEG-0001", "cliente_id": "CLI-0001", "canal": "email",
         "categoria": "tecnico", "prioridad": "alta", "nuevo": True,
         "estado": "pendiente_respuesta", "borrador_creado": True,
         "borrador_id": "borrador-demo-1",
         "asunto": "Ascensor de la escalera B parado",
         "descripcion": "La presidencia avisa: ascensor parado desde esta mañana "
                        "en la escalera B. Reclaman respuesta urgente.",
         "edificio": "C/ Alcalde Reig, 8 (Valencia)",
         "correo_origen": "admin.reig8@example.com",
         "thread_id": "demo-thread-1",
         "fecha_apertura": f(-1), "fecha_ultima_interaccion": f(-1),
         "fecha_ultimo_movimiento": f(-1), "fecha_ultimo_envio": None,
         "proximo_paso": "Enviar el borrador preparado",
         "presupuesto": None, "captacion": False, "plan_captacion": None,
         "continua_de": None, "notas": None,
         "historial": [{"fecha": f(-1),
                        "evento": "Mail entrante clasificado como TÉCNICO (prioridad alta). "
                                  "Borrador de respuesta preparado."}]},
        {"id": "SEG-0002", "cliente_id": "CLI-0002", "canal": "email",
         "categoria": "comercial", "prioridad": "media", "nuevo": False,
         "estado": "borrador_creado", "borrador_creado": True,
         "borrador_id": "borrador-demo-2",
         "asunto": "Presupuesto de mantenimiento — Renovación del contrato",
         "descripcion": "La junta pide detalle del presupuesto de renovación antes de la reunión.",
         "edificio": "Av. Olivar del Silo, 22 (Torrent)",
         "correo_origen": "presidencia.chopos@example.com",
         "thread_id": "demo-thread-2",
         "fecha_apertura": f(-20), "fecha_ultima_interaccion": f(-4),
         "fecha_ultimo_movimiento": f(-4), "fecha_ultimo_envio": None,
         "proximo_paso": "Revisar y enviar el borrador con el detalle pedido",
         "presupuesto": "PRE-0001", "captacion": False, "plan_captacion": None,
         "continua_de": None, "notas": None,
         "historial": [
             {"fecha": f(-20), "evento": "Solicitud de renovación de mantenimiento."},
             {"fecha": f(-4), "evento": "Piden detalle del presupuesto. Borrador preparado."}]},
        {"id": "SEG-0003", "cliente_id": "CLI-0004", "canal": "email",
         "categoria": "facturacion", "prioridad": "baja", "nuevo": False,
         "estado": "respondido", "borrador_creado": False,
         "borrador_id": None,
         "asunto": "Factura de octubre — desglose",
         "descripcion": "Pedían desglose de la factura de octubre. Respondido con el desglose adjunto.",
         "edificio": "C/ Ruiz de Lihory, 3 (Valencia)",
         "correo_origen": "compras@textilsorolla.example.com",
         "thread_id": "demo-thread-3",
         "fecha_apertura": f(-8), "fecha_ultima_interaccion": f(-5),
         "fecha_ultimo_movimiento": f(-5), "fecha_ultimo_envio": f(-5),
         "proximo_paso": None,
         "presupuesto": None, "captacion": False, "plan_captacion": None,
         "continua_de": None, "notas": None,
         "historial": [
             {"fecha": f(-8), "evento": "Mail entrante clasificado como FACTURACIÓN."},
             {"fecha": f(-5), "evento": "Borrador revisado y enviado a mano por el asesor."}]},
        {"id": "SEG-0004", "cliente_id": "CLI-0005", "canal": "email",
         "categoria": "comercial", "prioridad": "media", "nuevo": False,
         "estado": "respondido", "borrador_creado": False,
         "borrador_id": None,
         "asunto": "Propuesta de mantenimiento",
         "descripcion": "Captación: comunidad ajena descontenta con el mantenedor actual.",
         "edificio": "Av. del Puerto, 120 (Valencia)",
         "correo_origen": "administrador.puerto120@example.com",
         "thread_id": "demo-thread-4",
         "fecha_apertura": f(-12), "fecha_ultima_interaccion": f(-2),
         "fecha_ultimo_movimiento": f(-2), "fecha_ultimo_envio": f(-12),
         "proximo_paso": "Paso 2: recordatorio",
         "presupuesto": None, "captacion": True,
         "plan_captacion": {"pasos_totales": 3, "paso_actual": 2, "estado": "activo",
                            "pasos": [
                                {"n": 1, "concepto": "Propuesta inicial",
                                 "fecha_programada": f(-12), "estado": "enviado",
                                 "borrador_id": "borrador-demo-4", "fecha_envio": f(-12)},
                                {"n": 2, "concepto": "Recordatorio",
                                 "fecha_programada": f(-5), "estado": "pendiente",
                                 "borrador_id": None, "fecha_envio": None},
                                {"n": 3, "concepto": "Cierre / último toque",
                                 "fecha_programada": f(10), "estado": "pendiente",
                                 "borrador_id": None, "fecha_envio": None}]},
         "continua_de": None, "notas": None,
         "historial": [
             {"fecha": f(-12), "evento": "Propuesta inicial enviada (paso 1 del plan de captación)."},
             {"fecha": f(-2), "evento": "Marcado como 🎯 CAPTACIÓN."}]},
        {"id": "SEG-0005", "cliente_id": "CLI-0006", "canal": "email",
         "categoria": "comercial", "prioridad": "baja", "nuevo": False,
         "estado": "borrador_creado", "borrador_creado": True,
         "borrador_id": "borrador-demo-5",
         "asunto": "Información sobre servicios",
         "descripcion": "Prospecto pidió información. Borrador con la presentación de servicios listo.",
         "edificio": "C/ Sagunto, 45 (Valencia)",
         "correo_origen": "sagunto45@example.com",
         "thread_id": "demo-thread-5",
         "fecha_apertura": f(-9), "fecha_ultima_interaccion": f(-1),
         "fecha_ultimo_movimiento": f(-1), "fecha_ultimo_envio": None,
         "proximo_paso": "Enviar el borrador de bienvenida",
         "presupuesto": None, "captacion": True,
         "plan_captacion": {"pasos_totales": 3, "paso_actual": 1, "estado": "activo",
                            "pasos": [
                                {"n": 1, "concepto": "Propuesta inicial",
                                 "fecha_programada": f(-9), "estado": "borrador_creado",
                                 "borrador_id": "borrador-demo-5", "fecha_envio": None},
                                {"n": 2, "concepto": "Recordatorio",
                                 "fecha_programada": f(-2), "estado": "pendiente",
                                 "borrador_id": None, "fecha_envio": None},
                                {"n": 3, "concepto": "Cierre / último toque",
                                 "fecha_programada": f(13), "estado": "pendiente",
                                 "borrador_id": None, "fecha_envio": None}]},
         "continua_de": None, "notas": None,
         "historial": [{"fecha": f(-9),
                        "evento": "Mail entrante clasificado como COMERCIAL (captación)."}]},
        {"id": "SEG-0006", "cliente_id": "CLI-0008", "canal": "email",
         "categoria": "comercial", "prioridad": "baja", "nuevo": False,
         "estado": "descartado", "borrador_creado": False,
         "borrador_id": None,
         "asunto": "Consulta sobre cambio de mantenedor",
         "descripcion": "Consulta inicial sin respuesta pese a dos contactos.",
         "edificio": "Paseo Marítimo, 55 (Valencia)",
         "correo_origen": "mantenimiento@playaazul.example.com",
         "thread_id": "demo-thread-6",
         "fecha_apertura": f(-90), "fecha_ultima_interaccion": f(-80),
         "fecha_ultimo_movimiento": f(-80), "fecha_ultimo_envio": None,
         "proximo_paso": None,
         "presupuesto": None, "captacion": False, "plan_captacion": None,
         "continua_de": None,
         "motivo_descarte": "Sin interés tras dos contactos; hotel con contrato en vigor.",
         "notas": None,
         "historial": [{"fecha": f(-80),
                        "evento": "Descartado desde el panel: sin interés tras dos contactos."}]},
    ]}


def demo_presupuestos() -> dict:
    return {"version": 1, "presupuestos": [
        {"id": "PRE-0001", "cliente_id": "CLI-0002",
         "cliente_nombre": "Residencial Los Chopos (Torrent)",
         "titulo": "Mantenimiento semi riesgo — Residencial Los Chopos, Torrent",
         "thread_id": "demo-thread-2",
         "fecha_envio": f(-45), "fecha_reclamacion": f(-20),
         "fecha_vencimiento_contrato": "2027-02",
         "importe": 12400.0, "estado": "pendiente_firma",
         "reclamaciones": [
             {"fecha": f(-20), "estado": "enviada",
              "nota": "Recordatorio 1: pregunta por el estado de la firma."},
             {"fecha": f(-5), "estado": "borrador_creado",
              "nota": "Recordatorio 2 preparado en el hilo, pendiente de envío."}],
         "notas": f"{AVISO} La junta revisa el detalle en la próxima reunión.",
         "demo": True},
        {"id": "PRE-0002", "cliente_id": "CLI-0003",
         "cliente_nombre": "Edificio Mirasol (Paterna)",
         "titulo": "Mantenimiento confort — Edificio Mirasol, Paterna",
         "thread_id": "demo-thread-7",
         "fecha_envio": f(-120), "fecha_reclamacion": f(-90),
         "fecha_vencimiento_contrato": "2027-09",
         "importe": 18600.0, "estado": "firmado",
         "fecha_firma": f(-65),
         "reclamaciones": [{"fecha": f(-90), "estado": "enviada", "nota": "Único recordatorio antes de la firma."}],
         "notas": f"{AVISO} Firmado en el año en curso (cuenta para el objetivo anual).",
         "demo": True},
        {"id": "PRE-0003", "cliente_id": "CLI-0006",
         "cliente_nombre": "Cdad. Prop. C/ Sagunto, 45 (Valencia)",
         "titulo": "Presupuesto inicial de mantenimiento — C/ Sagunto, 45",
         "thread_id": "demo-thread-8",
         "fecha_envio": f(-16), "fecha_reclamacion": None,
         "fecha_vencimiento_contrato": None,
         "importe": 5200.0, "estado": "pendiente_firma",
         "reclamaciones": [],
         "notas": f"{AVISO} Primera reclamación prevista según la ventana configurada.",
         "demo": True},
    ]}


def demo_programaciones() -> dict:
    return {"version": 1, "programaciones": [
        {"id": "PROG-0001", "cliente_id": "CLI-0007",
         "fecha_programada": f(1), "hora_programada": "09:00",
         "estado": "pendiente",
         "descripcion": "Aviso: revisión semestral del ascensor mañana a las 9:00.",
         "avisos": [{"fecha": f(1), "tipo": "manana", "hecho": False},
                    {"fecha": f(1), "tipo": "tarde_verificacion", "hecho": False}],
         "notas": None},
        {"id": "PROG-0002", "cliente_id": "CLI-0001",
         "fecha_programada": f(-3), "hora_programada": "09:00",
         "estado": "vencido",
         "descripcion": "Aviso: visita técnica pendiente de programar fecha.",
         "avisos": [{"fecha": f(-3), "tipo": "manana", "hecho": True},
                    {"fecha": f(-3), "tipo": "tarde_verificacion", "hecho": False}],
         "notas": "El aviso salió por la mañana pero la visita sigue sin agendar."},
    ]}


def demo_ventas() -> dict:
    return {"version": 1, "ventas": [
        {"id": "VEN-0001", "cliente_id": "CLI-0004", "fecha": f(-48),
         "importe": 3400.0, "descripcion": "Puertas automáticas en 2 ascensores",
         "origen": "manual", "estado": "activa",
         "creado": f(-48) + "T10:30:00"},
        {"id": "VEN-0002", "cliente_id": "CLI-0003", "fecha": f(-14),
         "importe": 950.0, "descripcion": "Engrase y ajuste de frenos (intervención puntual)",
         "origen": "manual", "estado": "activa",
         "creado": f(-14) + "T12:00:00"},
    ]}


def demo_citas() -> dict:
    return {"version": 1, "citas": [
        {"id": "CITA-0001", "cliente_id": "CLI-0002", "seguimiento_id": "SEG-0002",
         "titulo": "Reunión con la junta — detalle del presupuesto",
         "fecha": f(5), "hora": "18:30", "duracion_min": 60,
         "ubicacion": "Av. Olivar del Silo, 22 (Torrent)",
         "event_id": None, "estado": "programada", "modificaciones": [],
         "resultado": None, "borrador_id": None, "creado": f(-1) + "T09:00:00"},
        {"id": "CITA-0002", "cliente_id": "CLI-0003", "seguimiento_id": None,
         "titulo": "Visita comercial — presentación de servicios",
         "fecha": f(-20), "hora": "10:00", "duracion_min": 60,
         "ubicacion": "C/ Blasco Ibáñez, 14 (Paterna)",
         "event_id": None, "estado": "efectuada", "modificaciones": [],
         "resultado": {"dio_resultado": True, "venta_id": "VEN-0002",
                       "presupuesto_id": "PRE-0002",
                       "nota": "De la visita salió el ajuste puntual y la firma del confort."},
         "borrador_id": None, "creado": f(-25) + "T17:00:00"},
    ]}


def demo_identidad() -> dict:
    return {"version": 1, "mapeo": {}, "sin_vincular": []}


def demo_informe() -> dict:
    return {"posibles_duplicados": []}


def demo_mes() -> str:
    return f"""# Registro — {HOY.year}-{HOY.month:02d}

> ⚠️ {AVISO}

| Fecha | Caso | Categoría | Acción | Resultado |
|---|---|---|---|---|
| {f(-1)} | SEG-0001 (CLI-0001) | tecnico | Mail entrante clasificado (ascensor parado) | borrador_creado |
| {f(-4)} | SEG-0002 (CLI-0002) | comercial | Borrador con detalle del presupuesto | borrador_creado |
| {f(-5)} | SEG-0003 (CLI-0004) | facturación | Desglose de factura enviado a mano | respondido |
| {f(-12)} | SEG-0004 (CLI-0005) | comercial | Propuesta inicial de captación (paso 1) | enviado |
| {f(-48)} | VEN-0001 (CLI-0004) | comercial | Venta manual: puertas automáticas | registrada |
| {f(-65)} | PRE-0002 (CLI-0003) | comercial | Presupuesto firmado (confort) | firmado |
"""


def demo_lecciones() -> str:
    return """# Lecciones del asistente (demo)

> ⚠️ {aviso}

Cuando el asesor corrija un borrador, registra aquí qué cambió y por qué,
para que el agente ajuste el tono y la forma.

**Ejemplos de formato:**
- 2026-11-18 — En derivaciones a Facturación, el asesor prefiere empezar por
  el resumen del caso y dejar el saludo formal al final.
- 2026-11-17 — Al citar importes, usar punto como separador de miles
  (12.400 €) y no coma.
""".format(aviso=AVISO)


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera datos FICTICIOS para probar el panel.")
    parser.add_argument("--solo", action="store_true",
                        help="no sobreescribe ficheros que ya existan")
    args = parser.parse_args()

    ficheros = {
        "config.json": demo_config(),
        "maestro_clientes.json": demo_clientes(),
        "seguimientos.json": demo_seguimientos(),
        "presupuestos.json": demo_presupuestos(),
        "programaciones.json": demo_programaciones(),
        "ventas.json": demo_ventas(),
        "citas.json": demo_citas(),
        "identidad.json": demo_identidad(),
        "informe_importacion.json": demo_informe(),
    }

    DATOS.mkdir(exist_ok=True)
    (DATOS / "archivo").mkdir(exist_ok=True)
    for nombre, datos in ficheros.items():
        fich = DATOS / nombre
        if args.solo and fich.exists():
            print(f"[--] {nombre} ya existe, no se toca (--solo)")
            continue
        if fich.exists():
            marca = f"archivo/{nombre}_{date.today().isoformat()}.json"
            (DATOS / marca).write_text(fich.read_text(encoding="utf-8"), encoding="utf-8")
        fich.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] {nombre} (ficticio)")

    for rel, texto in [("meses/%s-%02d.md" % (HOY.year, HOY.month), demo_mes()),
                       ("memoria/lecciones.md", demo_lecciones())]:
        fich = DATOS / rel
        if args.solo and fich.exists():
            print(f"[--] {rel} ya existe, no se toca (--solo)")
            continue
        fich.parent.mkdir(parents=True, exist_ok=True)
        fich.write_text(texto, encoding="utf-8")
        print(f"[OK] {rel} (ficticio)")

    print()
    print("Datos ficticios listos. Abre el panel: Panel de Gestion.bat")
    print("(datos/config.json está excluido del git: nunca se publicará)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
