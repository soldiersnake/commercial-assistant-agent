# Plantilla — Recordatorio de captación (pasos 2 y 3 del plan)

> USO: el agente redacta a partir de esta plantilla el BORRADOR del
> paso pendiente del plan de captación, en el hilo de origen, con el
> contexto del caso. NUNCA se envía: queda como borrador para el
> asesor. El estilo final lo manda `datos/memoria/lecciones.md`.

---

## PASO 2 — Recordatorio (a los 7 días)

Asunto: el mismo del hilo.

Cuerpo:

    Buenos días, {nombre_contacto}:

    Le escribo de nuevo en relación con su mensaje sobre {tema_del_caso}
    ({edificio_o_poblacion}). Como le comenté, de parte de {empresa}
    le podemos preparar la propuesta para {objeto_oferta}.

    ¿Sigue interesado? Si me confirma los datos que falten
    ({peticiones_pendientes}, por ejemplo el número de ascensores o la
    marca), le preparo la oferta esta misma semana.

    Un saludo cordial.

    {asesor_nombre}
    {asesor_cargo} — {empresa}

Tono: cortés y breve, SIN agobio. Si ya pasó más de un recordatorio,
admite llamada: "si prefiere, le llamo un momento".

## PASO 3 — Cierre / último toque (a los 15 días)

Asunto: el mismo del hilo.

Cuerpo:

    Buenos días, {nombre_contacto}:

    Hace unas semanas le escribí a propósito de {tema_del_caso}. No
    quiero insistirle más: si el momento no es bueno, con decírmelo
    lo dejamos aquí sin problema; y si más adelante quiere retomarlo,
    aquí estaré.

    Quedo a su disposición.

    {asesor_nombre}
    {asesor_cargo} — {empresa}

Tono: cierre amable, sin presión, puerta abierta.

---

## Notas para el agente

- Rellena los {placeholders} desde el seguimiento (descripcion,
  edificio, proximo_paso, presupuesto pedido) y la ficha del cliente.
  {asesor_nombre}, {asesor_cargo} y {empresa} salen de
  `datos/config.json` (asesor y empresa).
- Si el caso ya tiene presupuesto/oferta en marcha (presupuesto.pedido),
  adapta: recordatorio de la OFERTA concreta, no de "preparar la oferta".
- Si el cliente es un EDIFICIO AJENO (gestionado por la competencia),
  menciona suavemente la comparativa/2ª opinión, sin despreciar al
  gestor actual.
- La respuesta SIEMPRE en el hilo de origen, dirigida a
  `correo_origen`.
- Tras crear el borrador: paso → `borrador_creado` (+ `borrador_id`),
  estado del seguimiento → `borrador_creado`, fila en historial y
  registro mensual.
