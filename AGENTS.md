# AGENTS.md — Reglas de desarrollo del proyecto Gestor Comercial (commercial-assistant-agent)

Gestor comercial de asesoría para un asesor comercial del sector del
mantenimiento de ascensores. Este fichero guía a cualquier
agente/developper que trabaje en este repositorio.

## 1. Fuente de verdad del proyecto

- **`docs/PLAN.md` es el plan maestro.** Léelo ANTES de tocar nada.
  Contiene: fases con estado, decisiones tomadas, reglas de negocio
  y esquemas de datos. Cualquier decisión nueva se registra ahí.
- Al cerrar una fase: actualizar su estado en PLAN.md y hacer merge
  a `main` (las fases se trabajan en su rama `fase-N-nombre`).

## 2. Estructura del proyecto

```
AGENTS.md            ← este fichero (reglas de desarrollo)
README.md            ← documentación para el usuario final (el asesor)
docs/PLAN.md         ← plan maestro (fases, decisiones, esquemas)
docs/agente/         ← instrucciones del asistente (Fase 4)
entrada/             ← el asesor suelta aquí su Excel de clientes
  procesados/        ← ficheros ya importados (con fecha)
datos/               ← LA MEMORIA (fuente de verdad de los datos)
  maestro_clientes.json / identidad.json / seguimientos.json
  presupuestos.json / programaciones.json / config.json
  meses/AAAA-MM.md   ← registro cronológico por mes
  memoria/lecciones.md ← aprendizaje del agente (estilo del asesor)
  plantillas/*.md    ← escritos estándar editables
scripts/             ← Python: sync, importador, utilidades
dashboard/           ← mini-app local (HTML + servidor pequeño)
mcp-gmail/           ← MCP: SOLO lectura + borradores (nunca enviar)
tests/               ← pruebas
```

> **Nota:** `datos/config.json` no va al git. Se crea copiando
> `datos/config.example.json` y rellenando nombre de la empresa,
> asesor, contactos y dominios.

## 3. Reglas de oro (inviolables)

1. **NUNCA se envía un mail por el sistema.** El MCP de Gmail solo
   tendrá scopes `gmail.readonly` + `gmail.compose` (borradores).
   El asesor envía siempre a mano desde Gmail.
2. **Las vistas no se editan a mano.** Excel y dashboard son salidas
   generadas por `sync.py` desde `datos/`. Nada escribe directamente
   en el Excel.
3. **La memoria vive en `datos/`.** Toda escritura de datos pasa por
   los módulos centralizados de `scripts/` (un único punto de
   acceso, para que una futura migración a BD sea barata).
4. **Datos personales NO van al git.** `.gitignore` excluye
   `datos/` (memoria), `excel/` y `entrada/` (ficheros reales).
   La cartera real se importó el 17-11-2026; los mocks de
   demostración fueron eliminados ese mismo día.
5. **Nunca borrar datos sin archivar.** Los borrados son movidas a
   archivo o marcado con estado; no desaparecen.
6. **Credenciales OAuth nunca en el repositorio** (ver .gitignore).

## 4. Reglas de negocio clave (resumen; detalle en PLAN.md)

- Clasificación de entrantes: Empresa ( interna) / Técnico /
  Facturación / Trabajos pendientes / Comercial. Solo 4 categorías
  de cliente + la corporativa.
- Derivación a otros departamentos: intro personalizada + bloque
  fijo de contactos (plantilla `datos/plantillas/`).
- Presupuestos: ventana de firma por defecto 3 meses antes del
  vencimiento (los OCA condicionadas); reclamación cada 15 días con
  contador; se detiene al marcar Firmado (confirmación manual).
- El borrador de respuesta SIEMPRE va al hilo/dirección de origen.
- Acciones del dashboard tienen prioridad sobre mails nuevos.
- Programación: aviso informativo la mañana indicada; si a las 16:00
  no se envió → alerta roja persistente.
- Cliente con varios mails/teléfonos → fichas múltiples + mapeo en
  `identidad.json`. Vinculación de direcciones desconocidas solo a
  mano por el asesor o con su confirmación.

## 5. Entorno

- Windows + PowerShell. Python 3.12+ (`python`, no `python3`).
- Dependencias se instalan en `.venv` (documentar en scripts).
- Ejecutar tests de `tests/` antes de cada commit de fase.
- Idioma del producto: español (código y comentarios en español).
- **Al cambiar el código de un MCP (`mcp-gmail/servidor_mcp.py`),
  ejecutar `opencode service restart`** — el servicio en segundo
  plano mantiene la conexión MCP viva con el código anterior y no
  recarga el fichero del servidor por sí solo.
- **Ojo con los procesos zombis del panel**: el python de
  WindowsApps lanza hijos `python3.13.exe`, así que matar
  `python.exe` por nombre NO los mata. Para reiniciar el panel:
  `netstat -ano | findstr :8765` → matar POR PID todos los
  LISTENING (en Windows varios procesos pueden compartir puerto
  con SO_REUSEADDR y las conexiones van salteando entre instancias
  viejas y nuevas — síntoma: unas rutas sí y otras no).

## 6. Modo asistente comercial (IMPORTANTE para sesiones de OpenCode)

Este proyecto tiene, además del código, un **asistente comercial
operativo** que usa el MCP `gmail` (solo lectura + borradores).

- Si el usuario pide tareas del día a día (procesar mails, generar
  borradores, revisar pendientes, preguntar por clientes o
  presupuestos), **lee y sigue `docs/agente/instrucciones.md`**.
- Preguntas conversacionales sueltas → sección 3 de ese fichero.
- Proceso diario completo (corridas 7:00/16:00/"Procesar Ahora") →
  sección 2 de ese fichero, usando `docs/agente/prompt_corrida.txt`.
- Recordatorio: NUNCA enviar correos. Solo borradores vía MCP.
