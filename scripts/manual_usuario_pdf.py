# -*- coding: utf-8 -*-
"""manual_usuario_pdf.py — Genera docs/manual_usuario.pdf (manual
ilustrado del panel para el asesor) con las capturas anonimizadas de
docs/manual/img/.

Regenerar tras cambiar la interfaz del panel:
    .venv\\Scripts\\python.exe scripts\\manual_usuario_pdf.py

Las capturas se hacen con el MCP playwright (ver PLAN.md D33) y se
ANONIMIZAN antes de guardar (nombres/mails/importes ficticios), para
que el PDF pueda ir al git y compartirse. El mapa de anonimización
vive fuera del repo (temp), se genera desde datos/ con un script
desechable — nunca se suben datos reales.
"""
from pathlib import Path

import json

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

RAIZ = Path(__file__).resolve().parent.parent
IMG = RAIZ / "docs" / "manual" / "img"
SALIDA = RAIZ / "docs" / "manual_usuario.pdf"

_CFG = RAIZ / "datos" / "config.json"
cfg = json.loads(_CFG.read_text(encoding="utf-8")) if _CFG.exists() else {}

AZUL = colors.HexColor("#2c5f8a")
AZUL_CLARO = colors.HexColor("#e8f1f8")
GRIS = colors.HexColor("#5a6a7a")
ROJO = colors.HexColor("#c62828")

est_titulo = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=22,
                            textColor=colors.white, alignment=1)
est_sub = ParagraphStyle("s", fontName="Helvetica", fontSize=12,
                         textColor=colors.white, alignment=1)
est_h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=15,
                        textColor=AZUL, spaceBefore=14, spaceAfter=6)
est_h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12,
                        textColor=GRIS, spaceBefore=10, spaceAfter=4)
est_p = ParagraphStyle("p", fontName="Helvetica", fontSize=10.5,
                       leading=15, spaceAfter=6)
est_li = ParagraphStyle("li", fontName="Helvetica", fontSize=10.5,
                        leading=15, leftIndent=14, spaceAfter=3)
est_nota = ParagraphStyle("n", fontName="Helvetica-Oblique", fontSize=9.5,
                          textColor=GRIS, leading=13, spaceAfter=6)
est_alerta = ParagraphStyle("a", fontName="Helvetica-Bold", fontSize=10.5,
                            textColor=ROJO, leading=14, spaceAfter=6)


def p(txt, estilo=est_p):
    return Paragraph(txt, estilo)


def li(txt):
    return Paragraph(f"• {txt}", est_li)


def img(nombre, ancho_cm=17.0):
    """Captura escalada al ancho útil con borde."""
    ruta = IMG / nombre
    im = Image(str(ruta))
    ratio = im.imageHeight / im.imageWidth
    im.drawWidth = ancho_cm * cm
    im.drawHeight = ancho_cm * cm * ratio
    marco = Table([[im]], colWidths=[ancho_cm * cm + 8])
    marco.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#90a4ae")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return marco


def pie(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GRIS)
    canvas.drawString(2 * cm, 1.1 * cm,
                      "Panel de Gestión · Manual de usuario")
    canvas.drawRightString(A4[0] - 2 * cm, 1.1 * cm, f"Página {doc.page}")
    canvas.restoreState()


def portada():
    t = Table([[Paragraph("Panel de Gestión", est_titulo)],
               [Paragraph("Manual de usuario", est_sub)],
               [Paragraph(cfg.get("asesor", {}).get("nombre", "Asesor comercial"), est_sub)],
               [Paragraph("Versión de noviembre 2026 (datos ficticios en las capturas)", est_sub)]],
              colWidths=[17 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AZUL),
        ("TOPPADDING", (0, 0), (-1, 0), 60), ("BOTTOMPADDING", (0, -1), (-1, -1), 60),
        ("TOPPADDING", (0, 1), (-1, -1), 10),
    ]))
    return [Spacer(1, 3 * cm), t, Spacer(1, 1 * cm),
            p("Este manual explica, con imágenes reales de la aplicación "
              "(nombres anonimizados), cómo usar el Panel de Gestión en el "
              "trabajo de todos los días: qué mira usted, qué hace usted y "
              "qué hace solo el sistema.", est_p),
            PageBreak()]


def indice():
    contenido = [
        "1. Arrancar la aplicación y su rutina diaria",
        "2. La pantalla principal: chips y pestañas",
        "3. Seguimientos: su mesa de trabajo",
        "4. Responder, ver el hilo y cerrar casos",
        "5. Captación: cliente o captación, y el plan de 3 propuestas",
        "6. Clientes y vinculaciones",
        "7. Presupuestos y módulo económico",
        "8. Citas y programaciones",
        "9. Reglas de oro (lo que el sistema nunca hace)",
        "10. Si algo falla",
    ]
    return [p("Índice", est_h1)] + [li(x) for x in contenido] + [PageBreak()]


def seccion1():
    return [
        p("1. Arrancar la aplicación y su rutina diaria", est_h1),
        p("Para abrir el panel, doble clic en <b>Panel de Gestion.bat</b> "
          "(icono del escritorio). Se abre en su navegador en "
          "http://127.0.0.1:8765 — todo funciona en su PC, nada sale a internet."),
        p("Su rutina no necesita memoria:"),
        li("Por la mañana (7:00) y por la tarde (16:00) el asistente procesa "
           "solo el correo: clasifica, abre o actualiza casos y deja borradores "
           "en Gmail."),
        li("Usted revisa los borradores en Gmail, los corrige si quiere y los "
           "ENVÍA usted a mano. El sistema nunca envía."),
        li("Si quiere procesar fuera de hora: botón <b>Procesar ahora</b> "
          "(arriba a la derecha del panel)."),
        li("Los casos urgentes saltan en rojo en los chips de arriba."),
        p("El asistente también le prepara borradores cada vez que usted pide "
          "algo desde el panel (Responder, Agendar cita...). Aparecen en Gmail "
          "en 1-2 minutos."),
        img("00-general.png"),
        p("Vista general del panel: chips de estado arriba, pestañas y la "
          "tabla de Seguimientos debajo.", est_nota),
        PageBreak(),
    ]


def seccion2():
    return [
        p("2. La pantalla principal: chips y pestañas", est_h1),
        p("Los <b>chips</b> de la parte superior resumen su día. Lo que se "
          "pone en rojo pide su atención: pendientes de respuesta, urgentes, "
          "mails de más de 7 días sin responder, programaciones vencidas, "
          "pasos de captación vencidos y contactos sin vincular."),
        p("Las <b>pestañas</b> organizan todo su negocio:"),
        li("<b>Seguimientos</b>: los casos abiertos (su mesa de trabajo diaria)."),
        li("<b>Clientes</b>: su cartera completa, con fichas por cliente."),
        li("<b>Presupuestos</b>: ofertas y su módulo económico (objetivo, "
           "embudo, ventas)."),
        li("<b>Programaciones</b>: envíos aplazados con aviso."),
        li("<b>Citas</b>: su agenda con Calendar, vinculada a los casos."),
        li("<b>Vinculaciones</b>: contactos que el sistema no ha sabido "
           "emparejar y posibles duplicados."),
        p("El panel se refresca solo cada 30 segundos. Si usted está "
          "escribiendo o tiene un modal abierto, espera sin molestar."),
        PageBreak(),
    ]


def seccion3():
    return [
        p("3. Seguimientos: su mesa de trabajo", est_h1),
        p("Cada fila es un CASO: un asunto de un cliente que hay que atender. "
          "De izquierda a derecha:"),
        li("<b>Cliente</b>: nombre, código y el mail desde el que escribió "
           "(así ve de un vistazo a quién va a responder)."),
        li("<b>Caso</b>: descripción en lenguaje claro, próximo paso, edificio "
           "y las acciones principales: ver el <b>Hilo</b> y <b>Responder</b>."),
        li("<b>Categoría, Prioridad, Estado</b>: prioridad ALTA en naranja; "
           "estado En borrador (amarillo) hasta que usted envía."),
        li("<b>Días</b>: días sin respuesta — 7 o más se pone en rojo."),
        li("<b>A la derecha</b>, las acciones secundarias en dos filas: "
           "Envié, Cita, Descartar (rojo), Captación, Categoría."),
        p("Con los <b>filtros</b> de arriba puede buscar por texto y filtrar "
          "por categoría, estado (incluidos los Descartados) y prioridad."),
        img("00-general.png"),
        p("Fíjese en el caso rojo: es el botón <b>Descartar</b>, que cierra el "
          "caso sin responder cuando no hace falta contestar (hilo ya "
          "resuelto, mail informativo...). Se archiva con un motivo y nunca "
          "se borra.", est_nota),
        PageBreak(),
    ]


def seccion4():
    return [
        p("4. Responder, ver el hilo y cerrar casos", est_h1),
        p("<b>Responder</b> (debajo del texto del caso): escribe su respuesta "
          "como le salga. El asistente la corrige (usted, trato de usted, "
          "estructura), añade el contexto del caso y la deja como BORRADOR en "
          "el hilo de Gmail. Usted la revisa y la envía."),
        img("01-responder.png"),
        Spacer(1, 8),
        p("Si quiere que el borrador salga otro día, marque <b>Programar el "
          "envío</b>: ese día habrá aviso y, si al final del día no se envió, "
          "alerta roja."),
        p("<b>Ver el hilo</b> (botón Hilo): la conversación completa, con lo "
          "más NUEVO primero. El botón de invertir orden cambia el orden si "
          "prefiere leer de la más antigua a la más nueva. El borrador "
          "pendiente se ve con su etiqueta amarilla."),
        img("02-hilo.png"),
        Spacer(1, 8),
        p("<b>Ya lo envié</b> (botón verde de la botonera): cuando haya enviado "
          "el borrador a mano, púlselo para que el caso pase a respondido "
          "(el asistente también lo detecta solo leyendo el hilo)."),
        p("<b>Descartar</b> (botón rojo): cierra el caso SIN responder. Pide "
          "un motivo, que queda archivado en el historial y en el registro "
          "mensual. Un caso descartado no se reabre: si el cliente vuelve a "
          "escribir del tema, se abre un caso nuevo."),
        img("03-descartar.png"),
        Spacer(1, 8),
        p("<b>Categoría</b> (botón Categoría): si el sistema clasificó mal el "
          "mail (por ejemplo, puso Técnico cuando era Comercial), corríjalo "
          "aquí."),
        img("04-recategorizar.png"),
        PageBreak(),
    ]


def seccion5():
    return [
        p("5. Captación: cliente o captación, y el plan de 3 propuestas", est_h1),
        p("En los casos <b>Comerciales</b> aparece el botón <b>Captación</b>. "
          "Es para la primera contactación de un posible cliente nuevo (o de "
          "un edificio gestionado por otra empresa). Al pulsarlo, el caso se "
          "marca como captación y se crea un <b>plan de 3 propuestas</b>:"),
        li("<b>Paso 1 — Propuesta inicial</b>: es el borrador de respuesta al "
           "mail que ya genera el sistema."),
        li("<b>Paso 2 — Recordatorio</b>: a los 7 días, el asistente deja otro "
           "borrador listo en el hilo."),
        li("<b>Paso 3 — Cierre</b>: a los 15 días, un último toque amable."),
        p("Cada paso aparece en la fila del caso (con su fecha, y en rojo si "
          "está vencido). Usted envía el borrador en Gmail y pulsa "
          "<b>Paso enviado</b> en el panel; también puede adelantar o atrasar "
          "la fecha de un paso con el botón de fecha. Si firma el "
          "presupuesto, el plan se cierra solo."),
        img("05-captacion-fila.png"),
        Spacer(1, 8),
        p("Si se equivoca y el caso era de un cliente YA existente, pulse "
          "<b>Cliente</b> y la captación se cancela (todo queda en el "
          "historial, nada se pierde). El botón de Captación solo aparece en "
          "casos Comerciales: si el caso estaba mal categorizado, primero "
          "corríjalo con el botón Categoría."),
        PageBreak(),
    ]


def seccion6():
    return [
        p("6. Clientes y vinculaciones", est_h1),
        p("La pestaña <b>Clientes</b> muestra su cartera (buscador por "
          "nombre, dirección, población o código). En la <b>Ficha</b> de cada "
          "cliente: sus emails y teléfonos (puede añadir o quitar), "
          "propio/ajeno, tipo cliente/prospecto, sus casos abiertos y notas."),
        img("06-clientes.png"),
        Spacer(1, 8),
        img("07-ficha.png"),
        Spacer(1, 8),
        p("La pestaña <b>Vinculaciones</b> recoge los contactos que llegaron "
          "de direcciones desconocidas: vínculoselos a un cliente o cree un "
          "cliente nuevo. También avisa de posibles duplicados para fusionar "
          "(la ficha absorbida se archiva, nunca se pierde)."),
        PageBreak(),
    ]


def seccion7():
    return [
        p("7. Presupuestos y módulo económico", est_h1),
        p("La pestaña <b>Presupuestos</b> no es solo la lista de ofertas: "
          "arriba está su <b>módulo económico</b>:"),
        li("<b>Objetivo anual</b> con barra de progreso y proyección a fin "
           "de año (fíjelo con el botón Objetivo)."),
        li("<b>Embudo</b> de presupuestos: enviados, pendientes de firma, "
           "firmados y rechazados, con importes."),
        li("<b>Ventas facturadas</b>: las automáticas (presupuestos firmados) "
           "y las que usted apunta a mano con Añadir venta (históricas, "
           "extraordinarias...)."),
        li("<b>Ranking anual</b> de firmas por cliente."),
        li("<b>Captación: dinero en juego</b>: ofertas sin firmar de "
           "prospectos, por importe y antigüedad."),
        img("08-presupuestos.png"),
        Spacer(1, 8),
        p("En la tabla de presupuestos: estado con colores, próxima "
           "reclamación (vencida en rojo) y botones para marcar Firmado / "
           "Rechazado / Anulado. Recuerde: Firmado se confirma a mano, "
           "siempre."),
        img("09-economico-captacion.png"),
        PageBreak(),
    ]


def seccion8():
    return [
        p("8. Citas y programaciones", est_h1),
        p("La pestaña <b>Citas</b> muestra su agenda con Google Calendar: "
          "agenda del día, próximas citas y su resultado comercial. Desde "
          "cualquier caso, el botón <b>Cita</b> crea el evento en su Calendar "
          "y deja el borrador de aviso al cliente (sin invitaciones "
          "automáticas: el aviso es un borrador que usted envía)."),
        li("Al agendar, el panel avisa si ya tiene algo a esa hora."),
        li("Reprogramar o cancelar también genera el borrador de aviso."),
        li("Después de la visita, marque Efectuada/Cancelada y, si dio "
           "resultado, vincule la venta o el presupuesto."),
        p("La pestaña <b>Programaciones</b> son envíos aplazados: el día "
          "indicado hay aviso por la mañana y, si al final del día no se "
          "envió, queda en rojo (vencido). Puede reprogramar o cancelar."),
        PageBreak(),
    ]


def seccion9():
    return [
        p("9. Reglas de oro (lo que el sistema nunca hace)", est_h1),
        p("Estas cuatro reglas no cambian nunca; son la garantía de que el "
          "sistema trabaja PARA usted y no en su lugar:"),
        li("<b>Nunca envía correos</b>. Todo son borradores en Gmail. Usted "
           "los revisa y los envía a mano."),
        li("<b>Nunca borra nada</b>. Los descartes se archivan con su motivo; "
           "las fusiones archivan la ficha absorbida; hay copias de "
           "seguridad automáticas."),
        li("<b>Nunca marca Firmado por su cuenta</b>. Si un mail confirma una "
           "firma, avisa y espera su confirmación."),
        li("<b>Las acciones del panel tienen prioridad</b>: si usted pide una "
           "respuesta, sustituye al borrador automático del hilo."),
        p("Y una del asesor: si el sistema se equivoca clasificando o "
          "etiquetando, corríjalo usted con un clic (Categoría, Captación, "
          "Envié, Firmado) — con el tiempo el asistente aprende su estilo "
          "con las correcciones que ve en sus borradores.", est_p),
        PageBreak(),
    ]


def seccion10():
    return [
        p("10. Si algo falla", est_h1),
        li("El panel no carga: cierre el navegador y vuelva a abrir el "
           "icono. Si sigue mal, reinicie el PC."),
        li("Un borrador no aparece en Gmail: espere 2-3 minutos (la cola se "
           "procesa en segundo plano) y refresque Gmail."),
        li("Datos raros en el Excel: se regenera solo al final de cada "
           "corrida; también puede pedírselo al asistente (\"regenera el "
           "Excel\")."),
        li("Duda de qué hacer con un caso: pregúnteselo al asistente en la "
           "conversación (icono Asistente) — ve los mismos datos que "
           "el panel."),
        Spacer(1, 10),
        p("Manual generado con capturas del panel de noviembre 2026. Las "
          "imágenes usan datos ficticios.", est_nota),
    ]


def main():
    doc = SimpleDocTemplate(
        str(SALIDA), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.6 * cm, bottomMargin=1.8 * cm,
        title="Panel de Gestión — Manual de usuario",
        author=cfg.get("asesor", {}).get("nombre", "Asesor comercial"))
    historia = (portada() + indice() + seccion1() + seccion2() +
                seccion3() + seccion4() + seccion5() + seccion6() +
                seccion7() + seccion8() + seccion9() + seccion10())
    doc.build(historia, onFirstPage=pie, onLaterPages=pie)
    print(f"[OK] Manual generado: {SALIDA}")


if __name__ == "__main__":
    main()
