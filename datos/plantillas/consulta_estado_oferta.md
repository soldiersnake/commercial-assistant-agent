# Plantilla — Consulta de estado de oferta

**Cuándo usarla:** seguimiento de presupuestos enviados y sin
respuesta. Se programa con fecha de reclamación (por defecto a 1
mes del envío, o según la fecha que indique el asesor). El contador
de reclamaciones permite variar el tono.

**Variables:** `{nombre_contacto}` · `{titulo_oferta}` ·
`{fecha_envio}` · `{n_reclamacion}` · `{tono}` (1ª cortés / 2ª
insistente / 3ª+ firme pero amable) · `{asesor_nombre}` ·
`{asesor_cargo}` · `{empresa}` (valores de `datos/config.json`).

---

## Texto (1ª reclamación)

Estimado/a {nombre_contacto}:

Le escribo en relación a la oferta de **{titulo_oferta}** que le
enviamos con fecha {fecha_envio}, por si necesita alguna aclaración
o ampliación de la misma.

Asimismo, me gustaría conocer si la comunidad tiene previsto tratar
la oferta en alguna reunión próxima, para así poder adaptarnos a
sus fechas.

Quedo a su disposición para cualquier consulta.

Un saludo,

{asesor_nombre}
{asesor_cargo} — {empresa}

---

## Notas para el agente

- En reclamaciones 2ª o posteriores: reconocer amablemente que ya se
  consultó anteriormente y ofrecer alternativa (llamada, visita).
- Si el asesor ajustó este texto a mano en algún borrador, incorporar
  su versión a esta plantilla (ver `datos/memoria/lecciones.md`).
