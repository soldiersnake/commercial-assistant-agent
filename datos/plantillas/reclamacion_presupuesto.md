# Plantilla — Reclamación de presupuesto a firmar

**Cuándo usarla:** presupuestos con fecha de vencimiento (títulos
tipo "… OCA Condicionada Vencimiento dd-mm-aa"). A partir de la
fecha de reclamación (por defecto 3 meses antes del vencimiento) y
si sigue sin firmar, se genera un borrador con esta plantilla **cada
15 días**, con contador. Se detiene cuando el asesor marca el
presupuesto como **Firmado**.

**Variables:** `{nombre_contacto}` · `{titulo_presupuesto}` ·
`{fecha_vencimiento}` · `{n_reclamacion}` · `{dias_restantes}` ·
`{asesor_nombre}` · `{asesor_cargo}` · `{empresa}` (valores de
`datos/config.json`).

---

## Texto

Estimado/a {nombre_contacto}:

Me pongo en contacto en relación al presupuesto de
**{titulo_presupuesto}**, que figura con fecha de vencimiento del
**{fecha_vencimiento}**.

Para poder acometer los trabajos dentro del plazo indicado, es
necesario que la firma del presupuesto se formalice con una
antelación de aproximadamente tres meses (quedan
**{dias_restantes} días** hasta la fecha de vencimiento).

Le agradecería que me indicara el estado del documento y, si así lo
desea, quedo a su disposición para pasar por la comunidad, resolver
cualquier duda y recoger la firma.

Un saludo,

{asesor_nombre}
{asesor_cargo} — {empresa}

---

## Notas para el agente

- Reclamación 1ª: texto estándar. Reclamación 2ª y siguientes:
  hacer referencia amable a la anterior ("hace dos semanas me
  permití consultarle…") y ofrecer la visita/llamada.
- **Importante:** antes de generar el borrador, comprobar que el
  asesor no haya marcado el presupuesto como Firmado.
- Si el asesor ajusta el texto a mano, aprender de su versión (ver
  `datos/memoria/lecciones.md`).
