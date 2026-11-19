# Plantilla — Derivación a departamentos no comerciales

**Cuándo usarla:** mail entrante de cliente cuyo motivo NO es
comercial (Técnico / Facturación / Trabajos pendientes). El agente
escribe la introducción personalizada y añade este bloque fijo.

**Variables:** `{nombre_contacto}` · `{intro}` (resumen del caso) ·
`{fecha_consulta}` · `{tema}` (motivo derivado) · `{asesor_nombre}` ·
`{asesor_cargo}` · `{empresa}` (valores de `datos/config.json`).

> NOTA: el bloque de contactos se rellena desde
> `datos/config.json` (`empresa.contactos_corporativos`); los
> `{email_contacto_X}` / `{telefono_contacto_1}` son los datos de
> cada área tal como están en la configuración.

---

## Texto

Estimado/a {nombre_contacto}:

{intro}

Para agilizar su consulta y los tiempos, le indico el personal de
contacto de los diferentes departamentos administrativos de cada
área, para que pueda realizar las consultas necesarias:

- **Teléfono 24 h de Averías, ascensor parado, reclamaciones:**
  {telefono_contacto_1}. En el caso de no conseguir contactar este
  número, puede enviar un correo a {nombre_contacto_1}:
  **{email_contacto_1}**

- **Para consulta del estado de los trabajos ejecutados, pendientes,
  etc.,** puede escribir a Administración Comercial:
  **{email_contacto_2}**

- **Temas de Facturación,** puede escribir a: **{email_contacto_3}**

- **Y sobre consultas de OCAS,** a: **{email_contacto_4}**

Para todo el resto, me tiene a mí. Y como, si ninguno de mis
compañeros le responde dándoles un tiempo estimado, me llama o me
envía un correo, como siempre estaré a su disposición.

Un saludo,

{asesor_nombre}
{asesor_cargo} — {empresa}
