# PLAN MAESTRO — Gestor Comercial (commercial-assistant-agent)

> **Este fichero es la fuente de verdad del proyecto.** Cualquier
> sesión de trabajo debe leerlo antes de tocar código. Cada decisión
> tomada se registra aquí; cada fase se marca con su estado.

---

## 1. Objetivo

Sistema local (PC del asesor) que le ayude a gestionar su cartera de
~1.000 clientes de comunidades (varios edificios por cliente):
lectura y clasificación de mails, seguimiento por cliente,
generación de borradores (NUNCA envío), presupuestos con control de
firmas, Excel regenerado automáticamente y dashboard visual.

**Usuario final:** el asesor, comercial del sector del mantenimiento
de ascensores (dominios de la empresa configurados en
`datos/config.json` → `empresa.dominios`, Google Workspace —
verificado por MX).

**Principios:** todo local · el sistema nunca envía mails · la
memoria vive en ficheros de datos (migrable a BD en el futuro) ·
Excel y dashboard son vistas regeneradas.

---

## 2. Decisiones tomadas (registro)

| # | Fecha | Decisión |
|---|-------|----------|
| D1 | 17-11-2026 | Lenguaje: **Python** (scripts, MCP y mini-servidor del dashboard) |
| D2 | 17-11-2026 | Cuenta de correo: Google Workspace (la cuenta del asesor, ver `datos/config.json` → `asesor.email`). OAuth en modo test |
| D3 | 17-11-2026 | Cliente IA del asesor: compatible con **OpenCode y Gemini CLI** (ambos consumen MCP estándar). El MCP se diseña genérico |
| D4 | 17-11-2026 | WhatsApp: **pospuesto** a fase futura (evaluar API oficial de Meta vs no oficiales) |
| D5 | 17-11-2026 | Arquitectura: memoria en ficheros (`datos/`), Excel y dashboard como **vistas generadas** por sync.py. No usar el Excel como BD |
| D6 | 17-11-2026 | Ejecución: mezcla de terminal (agente) + dashboard en navegador (mini-servidor local) + iconos .bat. Sin app de escritorio propia por ahora |
| D7 | 17-11-2026 | Detección de mails: pull. Corridas automáticas 7:00 y 16:00 (Programador de tareas, OpenCode headless) + "Procesar Ahora" + modo conversación |
| D8 | 17-11-2026 | Dashboard con capacidad de **responder y programar**: el texto bruto que escribe el asesor lo refine el agente y queda como borrador en Gmail. Prioridad de cola: dashboard > mails nuevos |
| D9 | 17-11-2026 | Programación de envíos: aviso informativo la mañana indicada; si a las 16:00 no se envió → alerta roja persistente hasta que el asesor marque enviada/reprogramada/cancelada. El envío real lo hace el asesor (o Gmail "programar envío") |
| D10 | 17-11-2026 | Identidad: cliente con múltiples emails/teléfonos (fichas de contacto). Mapeo en `identidad.json`. El borrador SIEMPRE va al hilo/dirección de origen |
| D11 | 17-11-2026 | Vinculación manual: el asesor vincula direcciones desconocidas a clientes (o crea cliente). Nunca se asigna solo; también **fusión de fichas** duplicadas (avisada, no automática) |
| D12 | 17-11-2026 | Mails corporativos (dominios de la empresa, `empresa.dominios` de config.json): categoría aparte, color distinto (morado 🏢), no cuentan en pipeline ni métricas comerciales |
| D13 | 17-11-2026 | Clasificación entrantes: **Técnico / Facturación / Trabajos pendientes / Comercial** (fijas). Derivación con intro personalizada + bloque fijo de contactos |
| D14 | 17-11-2026 | Presupuestos: ventana firma por defecto **3 meses** antes del vencimiento (aplica a OCA condicionadas; vencimiento autodetectado del título del mail, el asesor puede editar fecha). Reclamación **cada 15 días** con contador. Se detiene al marcar Firmado (confirmación manual del asesor) |
| D15 | 17-11-2026 | Resumen para contestación de presupuestos: historial del caso; el asesor completa los importes de su app |
| D16 | 17-11-2026 | Lista de clientes de entrada: Excel **general** (con clientes propios y ajenos). Flag `propio/ajeno` visible y filtrable; métricas solo computan propios |
| D17 | 17-11-2026 | Módulo económico: importes, estados, ranking anual de firmas de clientes propios, **objetivo anual** del asesor con proyección |
| D18 | 17-11-2026 | Aprendizaje: ajustes manuales del asesor sobre borradores se guardan como lecciones (`datos/memoria/lecciones.md`) para refinar borradores futuros |
| D19 | 17-11-2026 | Memoria: ficheros JSON/MD hoy; migración a BD (SQLite si multi-dispositivo, Postgres si multi-usuario) como fase futura opcional si cambian las necesidades |
| D20 | 17-11-2026 | Formato del Excel real ("adm agosto de 2022.xls", .xls 2002): cabecera desplazada (col3=CP bajo "POBLACION"), emails/teléfonos sucios multi-valor con notas, CÓD = código de cliente en su sistema (se conserva como `codigo_empresa`). Importador con detección de offset contra datos + control de calidad que aborta sin archivar si no extrae nada. Todos los clientes importados como `propio` (export bajo su código comercial 0010); se pueden cambiar a `ajeno` con un clic cuando exista el panel |
| D21 | 17-11-2026 | Proyecto Google Cloud creado SIN organización y con una cuenta Google personal (privacidad frente a la empresa). OAuth: app externa en modo prueba, usuario de prueba la cuenta del asesor (ver `datos/config.json` → `asesor.email`). Nuance honesto: el scope gmail.compose técnicamente permitiría enviar, PERO el servidor MCP no contiene ninguna llamada a endpoints de envío (verificable en el código); la garantía de "nunca enviar" es de diseño de código + revisión. Token en mcp-gmail/token.json (gitignored). Autorización única completada y verificada 17-11-2026 (lectura de reales + ciclo crear/listar/eliminar borrador OK) |
| D22 | 17-11-2026 | Modelo para las corridas del asistente: `opencode-go/glm-5.3-flash` (config de proyecto opencode.json). Historial: la key de OpenCode Console estaba expirada; Google Gemini free se verificó OK (gemini-3.5-flash y lite) pero su cuota diaria gratuita (20 req/día) se agotó con los reintentos de la 1ª corrida — vuelve ~9:00 del 18-11. Las keys de OpenCode Go verificadas OK (glm-5.3-flash y glm-5.3). Alternativas documentadas en docs/MIGRACION_PC.md §3 (opción A GLM / B Gemini pago / C ambas) |
| D23 | 17-11-2026 | Automatización registrada: tareas programadas de Windows `GestorComercial_0700` y `GestorComercial_1600` (Corrida Automatica.bat → scripts/corrida.ps1 -Silencioso, logs en datos/corridas/). Lanzadores: Procesar Ahora.bat (visible), Asistente.bat (TUI conversacional), Panel de Gestion.bat (Fase 2). Cerebro del agente: docs/agente/instrucciones.md + prompt_corrida.txt; AGENTS.md §6 puentea modo conversación con las instrucciones |
| D24 | 17-11-2026 | Tras la 1ª corrida real y pruebas del panel: (1) nuevo estado de seguimiento **borrador_creado** ("🟡 En borrador") entre pendiente_respuesta y respondido — respondido SOLO cuando el asesor confirma envío (el agente lo verifica buscando mensaje SENT en el hilo, PASO 3b, o lo marca con el botón "✅ Ya lo envié"). (2) Esquema canónico de seguimiento fijado en instrucciones.md (descripcion OBLIGATORIA, fecha_ultima_interaccion, thread_id, borrador_id, historial como extra). (3) Procesado automático de la cola: cada acción "responder" del panel lanza procesar_cola.ps1 (prompt_cola.txt) en segundo plano → borrador en Gmail en ~1-2 min, sin esperar corridas. (4) Nueva herramienta MCP **gmail_update_draft**: el borrador del panel SUSTITUYE al automático del mismo hilo (prioridad del panel implementada de verdad). SEG-0001 normalizado al esquema |
| D25 | 17-11-2026 | Módulo económico: módulo compartido `scripts/economico.py` (panel + Excel), embudo por estados con importes y tasa de firma, ranking anual de firmas por cliente propio, sección captación, objetivo anual con barra de progreso, objetivo mensual (total ÷ 12) y proyección a fin de año. Acción `set_objetivo` en el panel (modal 🎯). Hoja "Economico" en el Excel |
| D26 | 17-11-2026 | Ventas manuales (CRUD del asesor) en `datos/ventas.json`: crear/editar/eliminar desde el panel (eliminar ARCHIVA en datos/archivo/ventas/, nunca se pierde) y dictadas al agente (instrucciones §3). Las ventas automáticas (presupuestos firmados) NUNCA se duplican en ventas.json. Métricas: total_anno = firmado_anno (auto) + manual_anno; por_mes desglosado auto/manual; gráfico mensual de barras en el objetivo con tooltip desglosado; potencial (pendiente de firma + captación) mostrado en el objetivo; ranking unificado; hoja Economico con ventas por mes y listado de manuales |

---

## 3. Fases (estado y entregables)

| Fase | Contenido | Estado |
|------|-----------|--------|
| 0 | Cimientos: git, estructura, PLAN.md, README.md, AGENTS.md, esquemas de datos + mocks | ✅ HECHA (17-11-2026) |
| 1 | Datos + importador Excel + `sync.py` + Excel gestionable | ✅ HECHA (17-11-2026) |
| 2 | Dashboard mini-app local (tablas, filtros, responder, programar, fichas, vinculaciones) | ✅ HECHA (17-11-2026) |
| 3 | MCP Gmail (solo lectura + borradores) + OAuth Google Cloud | ✅ HECHA (17-11-2026) |
| 4 | Agente + automatización (7:00/16:00, Procesar Ahora, colas, alertas, instrucciones del agente) | ✅ HECHA (17-11-2026) — primera corrida real completada: 20 mails procesados (8 empresa, 7 ignorados, 1 caso comercial con borrador en hilo) |
| 5 | Módulo económico (embudo, ranking anual, objetivo con proyección) | ✅ HECHA (17-11-2026) |
| 6 | Citas con Google Calendar (agendar desde seguimientos, borrador de aviso, ciclo de vida con resultado comercial) | ✅ HECHA (18-11-2026) |
| Futuro | WhatsApp · app de presupuestos · migración a BD | ⬜ Opcional |

**Workflow:** cada fase en rama `fase-N-nombre`, merge a `main` al
validar, estado actualizado en este fichero.

### Entradas pendientes del asesor
- [x] Excel de clientes (carpeta `entrada/`) — RECIBIDO e importado 17-11-2026 (84 clientes)
- [ ] Objetivo anual (monto) y reparto mensual opcional — Fase 5
- [x] Creación del proyecto Google Cloud + OAuth — HECHA 17-11-2026 (proyecto sin organización, cuenta Google personal; app externa en prueba con la cuenta del asesor como usuario de prueba; token autorizado y verificado)
- [x] Confirmar lista de contactos corporativos — DETECTADOS del Gmail real: dominios de la empresa (contactos en `empresa.contactos_corporativos` de `datos/config.json`); ampliar si el asesor indica más áreas/jefes
- [ ] Revisar 3 posibles duplicados detectados (informe_importacion.json) — Fase 2 (panel)
- [ ] Confirmar clientes propios/ajenos de la lista importada — Fase 2 (panel)

---

## 4. Esquemas de datos (`datos/`)

> Los ficheros reales NO van al git (ver `.gitignore`). Los mocks
> de demostración se eliminaron el 17-11-2026 tras importar la
> cartera real (84 clientes); las versiones demo quedan archivadas
> en `datos/archivo/` como referencia de esquema.

### 4.1 `maestro_clientes.json`
```jsonc
{
  "version": 1,
  "clientes": [{
    "id": "CLI-0001",
    "nombre": "Comunidad Cortes Valencianas 132",
    "direccion": "...", "poblacion": "...",
    "edificios": [{"nombre": "Bloque A", "escaleras": 2}],
    "tipo": "cliente",            // cliente | prospecto
    "propiedad": "propio",        // propio | ajeno
    "fichas_contacto": [
      {"tipo": "email", "valor": "...", "nombre": "...", "verificado": true},
      {"tipo": "telefono", "valor": "600123456", "nombre": "...", "verificado": false}
    ],
    "fecha_alta": "2024-03-10",
    "fecha_primera_contactacion": "2024-03-10",
    "fecha_ultima_interaccion": "2026-11-14",
    "estado_seguimiento": "al_dia",   // al_dia | pendiente_respuesta
    "notas": ""
  }]
}
```

### 4.2 `identidad.json` — mapeo email/tel → cliente
```jsonc
{
  "version": 1,
  "mapeo": {"administracion@cv132.com": "CLI-0001", "600123456": "CLI-0001"},
  "sin_vincular": [
    {"valor": "comunidad.bosque@yahoo.es", "detectado": "2026-11-16",
     "origen": "mail entrante", "pista": "Firma: Comunidad Bosque de Ayora"}
  ]
}
```
Normalización: emails en minúsculas, teléfonos como dígitos.

### 4.3 `seguimientos.json`
```jsonc
{
  "version": 1,
  "seguimientos": [{
    "id": "SEG-0007", "cliente_id": "CLI-0002",
    "fecha_apertura": "2026-11-03",
    "descripcion": "Avería en ascensor escalera B, porteador no cierra",
    "nuevo": true, "continua_de": null,
    "categoria": "tecnico",   // tecnico | facturacion | trabajos_pendientes | comercial | empresa
    "prioridad": "alta",      // alta | media | baja (avería/atascado/urgente → alta)
    "canal": "email", "edificio": "Bloque B",
    "estado": "pendiente_respuesta",  // pendiente_respuesta | respondido | cerrado
    "presupuesto": {"pedido": true, "presupuesto_id": "PRE-0002"},
    "fecha_ultima_interaccion": "2026-11-14",
    "proximo_paso": "Si no contesta, llamar el jueves",
    "correo_origen": "laruiz@gmail.com"
  }]
}
```

### 4.4 `presupuestos.json`
```jsonc
{
  "version": 1,
  "presupuestos": [{
    "id": "PRE-0001", "cliente_id": "CLI-0001",
    "referencia": "CV132-OCA-27",
    "titulo": "Cortes Valencianas 132 Quart OCA Condicionada Vencimiento 13-04-27",
    "importe": 18450.0,
    "fecha_envio": "2026-10-20",
    "fecha_vencimiento": "2027-04-13",
    "fecha_reclamacion": "2027-01-13",   // default: vencimiento − 3 meses (editable)
    "estado": "pendiente_firma",  // enviado | pendiente_firma | firmado | rechazado | anulado
    "fecha_firma": null,
    "reclamaciones": [{"n": 1, "fecha": "2027-01-13", "estado": "programada"}],
    "notas": ""
  }]
}
```

### 4.5 `programaciones.json`
```jsonc
{
  "version": 1,
  "programaciones": [{
    "id": "PROG-0001", "cliente_id": "CLI-0002", "seguimiento_id": "SEG-0007",
    "asunto": "Presupuesto cabina Bloque 2",
    "fecha_programada": "2026-11-18", "hora_programada": "09:00",
    "estado": "pendiente",       // pendiente | avisado | vencido | completado | cancelado
    "borrador_creado": true,
    "avisos": [{"fecha": "2026-11-18", "tipo": "manana", "hecho": false},
               {"fecha": "2026-11-18", "tipo": "tarde_verificacion", "hecho": false}]
  }]
}
```

### 4.6 `config.json` — empresa, reglas, objetivo
```jsonc
{
  "empresa": {
    "nombre": "Mi Empresa S.L.",
    "dominios": ["miempresa.com"],
    "contactos_corporativos": [
      {"nombre": "Nombre Apellido", "email": "averias@miempresa.com",
       "area": "Averías 24h / Reclamaciones", "telefono": "000 00 00 00"},
      {"nombre": "Nombre Apellido", "email": "administracion@miempresa.com",
       "area": "Administración Comercial — estado de trabajos"},
      {"nombre": "Nombre Apellido", "email": "facturacion@miempresa.com",
       "area": "Facturación"},
      {"nombre": "Nombre Apellido", "email": "tecnico@miempresa.com", "area": "OCAS"}
    ]
  },
  "asesor": {"nombre": "Nombre y Apellidos del asesor", "cargo": "Asesor comercial"},
  "reglas_presupuestos": {
    "ventana_firma_default_dias": 90,
    "intervalo_reclamacion_dias": 15,
    "max_reclamaciones": null
  },
  "objetivo_anual": {"anno": 2026, "monto": null, "reparto_mensual": null},
  "regex_vencimiento": "Vencimiento\\s*([0-9]{2}-[0-9]{2}-[0-9]{2,4})"
}
```

### 4.7 `meses/AAAA-MM.md` — registro cronológico
Una tabla por mes: `fecha | hora | cliente/ID | categoría | canal |
acción | estado | nota`. La lee el agente para tener contexto.

### 4.8 `memoria/lecciones.md`
Aprendizaje del agente: ajustes que el asesor hace a mano sobre
borradores (estilo, frases, criterios). Se consulta antes de
redactar.

### 4.9 `plantillas/`
Escritos estándar editables: `derivacion_no_comercial.md` (su texto
de derivación con bloques de contactos), `consulta_estado_oferta.md`,
`reclamacion_presupuesto.md`, `solicitud_documentacion.md`.

---

## 5. Flujo del sistema (referencia)

```
07:00 / 16:00 (OpenCode headless) · "Procesar Ahora" · modo conversación
  1. Cola de acciones del dashboard (PRIORIDAD)
  2. Mails nuevos de Gmail (MCP: solo lectura + borradores)
  3. Clasificar: Empresa → 🏢 aparte · sino categoría T/F/TP/C
  4. Emparejar remitente → identidad.json (duda → ❓ sin vincular)
  5. Actualizar seguimientos + ficha + registro mensual
  6. Generar borradores (hilo de origen) — refinar con lecciones.md
  7. Programaciones: aviso mañana / verificación tarde (alerta roja)
  8. Presupuestos: fechas de reclamación → borrador c/ contador
  9. sync.py → Excel + dashboard
```

---

## 7. ESTADO ACTUAL Y REANUDACIÓN (léelo si abres sesión nueva)

**Última actualización: 18/11/2026.** El sistema está COMPLETO y en
producción en el PC actual. Fases 0-6 hechas y
probadas con datos reales.

### Qué está vivo
- Cartera real: 84 clientes (Excel del asesor importado; 3 duplicados
  por fusionar cuando el asesor decida).
- Corridas automáticas 7:00/16:00 con StartWhenAvailable (si el PC
  estaba apagado, corren al encender). Modelo: `opencode-go/glm-5.3-flash`
  (key de OpenCode Go propia; Gemini free se agotó el 17/11 —
  disponible de nuevo con cuota diaria).
- Panel (127.0.0.1:8765): seguimientos con estados (incluido
  `borrador_creado`), fichas multi-contacto, presupuestos con
  reclamaciones, económico (objetivo/embudo/ranking/captación),
  ventas CRUD, citas con Calendar (agenda del día con aviso de
  solapamiento, agenda real 14 días, resultado comercial),
  vinculaciones, botonera superior (⚡ Procesar ahora / 📥 Importar).
- Cola del panel: órdenes ACC-*.json procesadas en automático
  (responder, cita_aviso) con borradores que SUSTITUYEN a los
  automáticos via `gmail_update_draft`.
- Primeras corridas reales validadas: clasificación correcta,
  1ª derivación a Facturación, detección de envíos (PASO 3b con
  regla mecánica corregida el 18/11 — ver D28).

### Pendientes (ordenado)
1. **El asesor**: fijar objetivo anual (🎯), cargar ventas históricas,
   revisar duplicados (Vinculaciones), marcar propios/ajenos,
   registrar su primera cita real.
2. **Semana de uso real** → lista de retoques finos (tono de
   borradores, clasificaciones).
3. **Migración al PC del asesor**: guía completa en
   `docs/MIGRACION_PC.md` (incluye API key OpenCode paso a paso).
4. **`git push`** del repositorio cuando quiera (solo código, nada de datos).
5. Futuro: WhatsApp · app de presupuestos · migración a BD.

### Lanadores y ficheros ejecutables (referencia)
| Fichero | Qué es | Quién lo usa |
|---|---|---|
| `Panel de Gestion.bat` | Abre la app (servidor + navegador) | el asesor (doble clic) |
| `Asistente.bat` | Conversación con el agente (TUI) | el asesor |
| `Procesar Ahora.bat` | Corrida manual visible | Respaldo (hay botón ⚡) |
| `Importar Clientes.bat` | Importar Excel de entrada/ | Respaldo (hay botón 📥) |
| `Corrida Automatica.bat` | Corrida silenciosa | Solo las tareas de Windows |
| `Sincronizar Excel.bat` | Regenera Excel | Respaldo (sync corre solo) |

### Cómo continuar el desarrollo (sesión nueva)
1. OpenCode abriendo ESTA carpeta → leerá `AGENTS.md` solo.
2. `AGENTS.md` apunta a este PLAN.md y a `docs/agente/instrucciones.md`.
3. Leer la sección 2 (decisiones D1-D28) y la tabla de fases para
   saber qué está hecho; los pendientes están aquí arriba.
4. Recordatorios técnicos: reiniciar panel matando por PID los
   LISTENING del 8765 (python3.13.exe zombis, ver AGENTS.md §5);
   tras cambiar el MCP, `opencode service restart`.

### Notas técnicas históricas por fase (ya implementadas)
- **F1:** parser del Excel real del asesor (depende del formato) ·
  detección duplicados · flag propio/ajeno por defecto.
- **F2:** mini-servidor stdlib (`http.server`) en 127.0.0.1:8765 ·
  `GET /api/estado` (instantánea con derivados: días sin responder,
  próx. reclamación, programaciones vencidas) · `POST /api/accion`
  (vincular, desvincular, crear cliente, cambiar propiedad/tipo,
  marcar firmado, cambiar estado presupuesto, responder→
  `datos/acciones/ACC-*.json` + programación con avisos,
  reprogramar, estado programación, fusionar con archivado) ·
  SPA vanilla JS en `dashboard/index.html` con filtros, fichas,
  modales y resaltados por urgencia. Registro mensual se actualiza
  con cada acción relevante. Lanzador `Panel de Gestion.bat`.
- **F3:** proyecto Google Cloud · scopes `gmail.readonly` +
  `gmail.compose` · MCP en Python (SDK oficial) · config para
  OpenCode y Gemini CLI.
- **F4:** OpenCode headless (`opencode run`) en el Programador de
  tareas · iconos .bat · plantilla de derivación.
- **F5:** regex vencimiento · máquina de estados presupuestos ·
  objetivo anual + proyección. ✅ HECHA (17-11-2026): módulo
  compartido `scripts/economico.py` (panel + Excel), embudo por
  estados con importes y tasa de firma, ranking anual de firmas por
  cliente propio, sección captación (prospectos con oferta sin
  firmar por importe/antigüedad), objetivo anual con barra de
  progreso, objetivo mensual (total ÷ 12) y proyección a fin de
  año. Acción `set_objetivo` en el panel (modal 🎯). Hoja
  nueva "Economico" en el Excel. + Fase 5b: CRUD de ventas manuales
  (D26): gráfico mensual facturado, potencial, ranking unificado.
  Pendiente del asesor: fijar su objetivo anual real desde el panel
  y cargar sus ventas históricas del año (CRUD o dictándolas al
  agente). |
| D27 | 18-11-2026 | **Citas con Google Calendar** (Fase 6): scope `calendar.events` añadido y re-autorizado; módulo compartido `scripts/gcal.py` (MCP + panel); 4 herramientas MCP (`calendar_create_event`, `list_events`, `update_event`, `delete_event`); panel: botón "📅 Agendar" en seguimientos + pestaña Citas (gráfico de estados, modificaciones, efectuada con/sin resultado comercial vinculado a venta/presupuesto); cada acción con cliente genera orden `cita_aviso` → borrador de aviso/reprogramación/cancelación en el hilo (texto guía del panel o contexto del hilo; NUNCA invitaciones automáticas de Calendar); citas sin cliente = solo calendario; `datos/citas.json` con event_id y resultado; hoja "Citas" en Excel; PASO 3c del agente: citas pasadas sin marcar. Ciclo verificado en vivo (crear/listar/reprogramar/eliminar). La 1ª corrida autónoma del 18/11 (7:00) validó el sistema diario: 2 casos reales, 1ª derivación real a Facturación (ARJ), PASO 3b detectó el envío del asesor (SEG-0001 → respondido) |
| D28 | 18-11-2026 | **Corrección de falso positivo del PASO 3b**: el agente marcó SEG-0001 como respondido cuando el mensaje del 17/11 en el hilo seguía siendo BORRADOR (etiqueta DRAFT) — se dejó engañar por los SENT antiguos del hilo (correos reales del asesor de octubre). Datos corregidos (SEG-0001 → borrador_creado con borrador_id r8263720554540604470, entrada falsa del historial marcada como CORREGIDO sin borrarse) y regla del PASO 3b reescrita como comprobación MECÁNICA: el último DRAFT del hilo debe seguir DRAFT salvo que exista un SENT POSTERIOR EN FECHA al borrador; los SENT viejos no cuentan. Lección: las verificaciones de estado del agente deben ser comparaciones de fechas/etiquetas deterministas, nunca interpretaciones |
| D29 | 18-11-2026 | **Empaquetado .exe postergado** (consulta interna): pros (apariencia de app, sin Python visible) vs contras (SmartScreen/antivirus sin certificado, recompilar en cada retoque durante la fase de ajuste fino, depuracion a ciegas, ~150-200 MB, OpenCode y carpetas de datos seguirian existiendo). Decision: NO ahora; el empaquetado se resuelve con iconos de escritorio (Panel + Asistente) y el proyecto en carpeta aparte que el asesor nunca abre. Opcional futuro: compilar solo el panel como exe tras 1-2 meses estables. **Runtime agentico necesario**: la API key sola no basta - OpenCode es el bucle del agente (herramientas, reintentos, MCP); en la migracion se instala OpenCode en el PC del asesor y se pega la key de soporte con opencode auth login (alternativa: cuenta propia del asesor o Gemini pago - docs/MIGRACION_PC.md sec.3). Alternativa futura documentada: agente propio en Python con API directa (proyecto aparte, mayor esfuerzo/riesgo). **Manual de un minuto del asesor** anadido al principio del README |
| D30 | 18-11-2026 | **Nuevo estado de seguimiento `descartado` + botón "🚫 Descartar"** (migrado del portátil del asesor, prueba real con SEG-0004): para cerrar casos que NO requieren respuesta (hilo ya resuelto, mail informativo, duplicado) sin falsos "respondidos" ni seguimientos eternos. Botón en el panel con nota de motivo OBLIGATORIA; el caso queda archivado con estado, motivo, historial y fila en el registro mensual (NADA se borra, regla de oro nº 5). Solo el asesor descarta desde el panel (el agente NUNCA marca este estado); un descartado NO se reabre: mail nuevo del tema = seguimiento NUEVO. Contabilizado como cerrado en métricas del panel (`seguimientos_abiertos`) y Excel (hoja resumen + etiqueta en hoja Seguimientos, motivo en la Descripción). Migra también 2 mejoras de panel: (1) el mail de origen (`correo_origen`) visible bajo el nombre del cliente en Seguimientos; (2) modal de hilo con la conversación ordenada MÁS NUEVA primero por defecto (por fecha real, borradores intercalados), botón ⇅ para invertir el orden y botón "✕ Cerrar" FIJO (sticky) arriba a la derecha en todos los modales |
| D31 | 18-11-2026 | **Captación estructurada (rama comercial: 👤 cliente vs 🎯 captación + plan de 3 propuestas)**: todo seguimiento comercial lleva `captacion` (true/false) y, si es captación, `plan_captacion` (3 pasos: Propuesta inicial / Recordatorio +7d / Cierre +15d; cadencia en `config.json → reglas_captacion`; aplica a prospectos y edificios AJENOS). Detección automática en PASO 2e (remitente no vinculado/prospecto sin historial → captación con nota justificativa; ante duda, captación — el asesor corrige). SOLO una contactación de categoría COMERCIAL puede ser captación (validado en servidor y en panel). El borrador de respuesta al mail entrante ES el paso 1; los pasos vencidos generan BORRADOR automático en el hilo (plantilla `captacion_recordatorio.md`) con aviso de disponibilidad y alerta si no se envía (PASO 3d, verificación mecánica como PASO 3b). Panel: botones 🎯/👤 (toggle), ⇄ Recategorizar (corrección de clasificación; recategorizar a comercial NO activa captación), ✅ Paso enviado, 📅 reprogramar paso; badges + línea de paso con alerta de vencido; métricas captaciones activas/pasos vencidos. Excel: columnas Captación/Paso + líneas en resumen. El plan se cierra con descartado/cerrado/firmado (se archiva, no se borra). El agente NUNCA marca captación fuera de comercial ni crea el plan (lo crea el panel) |
| D32 | 18-11-2026 | **Retoques de interfaz del panel tras probar el flujo real** (feedback del asesor): (1) botonera de acciones de Seguimientos compacta — columna fija ~240px con los botones secundarios en 2 filas (✅ Envié, ✅ Paso N, 📅 Paso, 📅 Cita, 🚫 Descartar, 🎯 Captación/👤 Cliente, ⇄ Categoría), con **👁️ Hilo** y **✍️ Responder** sacados a la columna CASO (debajo del texto del caso, separados ~70px), porque son las acciones principales; (2) botón **🚫 Descartar con fondo ROJO** (clase `danger`) para distinguirlo; (3) el botón **🎯 Captación/👤 Cliente SOLO aparece en casos de categoría comercial** — un caso mal categorizado se corrige primero con ⇄ Categoría → Comercial y entonces aparece (el servidor además rechaza toggle/recategorización que violen la regla); (4) el README (manual del asesor) actualizado con la columna Seguimientos completa y los chips de captación. Todo en `dashboard/index.html`, sin cambios de servidor salvo los de D31 |
| D33 | 18-11-2026 | **MCP playwright añadido** a `opencode.json` (formato OpenCode V2: `mcp.servers` + `type: "local"` + `command` array, NO el formato `mcpServers` de Claude/Cursor): `["cmd", "/c", "npx", "-y", "@playwright/mcp@latest"]` — el `cmd /c` es necesario en Windows (npx es un shim .cmd que falla al spawn directo) y `-y` evita que la 1ª descarga bloquee el handshake. Requisito nuevo para el PC del asesor: **Node.js** (nota añadida a MIGRACION_PC.md sec.2). Verificado: `opencode mcp list` → connected (la 1ª vez sale "pending" mientras descarga el paquete) y prueba real navegando al panel (127.0.0.1:8765) con captura y snapshot — único error de consola el favicon 404, preexistente e inofensivo. Los tools quedan en Code Mode como `tools.playwright.*` (útil para revisar el panel como el asesor lo ve). Ojo: NO sustituye al Excel ni escribe datos — solo navegación/prueba visual |
| D34 | 18-11-2026 | **Manual de usuario ilustrado en PDF** (`docs/manual_usuario.pdf`, 16 páginas): flujo completo con capturas reales del panel tomadas con el MCP playwright (13 imágenes en `docs/manual/img/`). Las capturas se **ANONIMIZAN antes de guardar** — se inyecta JS que sustituye nombres/mails/teléfonos/direcciones/edificios de la cartera real (399 sustituciones) por ficticios coherentes ("CLIENTE DEMO 053", "demo053@mail.com"…), con límites de palabra para evitar falsos positivos (ej. "ADMINISTRA" dentro de "Administración Comercial"); así el PDF puede ir a git y compartirse. El mapa real→ficticio vive SOLO en temp (nunca al repo, las claves son datos personales). Generador reutilizable `scripts/manual_usuario_pdf.py` (reportlab, ya en .venv): regenerar tras cada cambio de interfaz con `.venv\Scripts\python.exe scripts\manual_usuario_pdf.py`. Para la demo del plan de captación se activó 🎯 en SEG-0001, se capturó y se revirtió a 👤 Cliente (quedan 2 entradas en su historial, trazables). Verificado visualmente página a página (portada, secciones, imágenes) |
| D35 | 18-11-2026 | **Desmarcado de la empresa (petición del asesor: la herramienta es personal, sin vínculo formal con la empresa para evitar reclamaciones)**: eliminadas TODAS las referencias a la empresa del manual de usuario (portada, pie de página, metadatos author del PDF) y del README (título → "Gestor Comercial — Panel de seguimiento de asesor comercial"); re-captura del hilo con el dominio de la empresa también anonimizado en el mapa (→ `demo-mail.com`), incluido el mail del asesor. La UI del panel no mostraba la marca (cabecera: "Panel de Gestión — Asesor"). SIGUEN teniéndola (INTENCIONADO, uso operativo real): `datos/config.json` (nombre de empresa y contactos corporativos para las derivaciones de mails), la firma de los borradores en `docs/agente/instrucciones.md` (es la firma profesional de los mails del asesor) y las notas internas de desarrollo (PLAN/AGENTS). Si algún día se quiere eliminar también de ahí, decisión aparte |
