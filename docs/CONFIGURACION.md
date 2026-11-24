# 🚀 Guía de configuración — de cero a funcionando

> Esta guía asume **Windows + Python 3.12+** y está pensada para que una persona
> sin experiencia en IA lo tenga funcionando en una tarde, **sin pagar nada**.
> Todo lo que el sistema guarda queda en tu PC. Si prefieres ver el panorama
> general antes de los pasos, empieza por el [README](../README.md).

> 🧭 **La forma más fácil**: haz el *Paso 0*, abre el panel (`Panel de Gestion.bat`)
> y pulsa **🚀 Empezar con mis datos**. Un asistente visual te lleva por los
> pasos 2, 3 y 4 de esta guía (y te dice qué falta del 1) sin abrir la consola.
> Esta guía es la referencia detallada y la vía manual.

## Índice

- [Paso 0: requisitos](#paso-0-requisitos)
- [Paso 1: configura la IA (coste cero)](#paso-1-configura-la-ía-coste-cero)
- [Paso 2: conecta tu correo y tu calendario (OAuth)](#paso-2-conecta-tu-correo-y-tu-calendario-oauth)
- [Paso 3: personaliza tu configuración](#paso-3-personaliza-tu-configuración)
- [Paso 4: importa tu cartera de clientes](#paso-4-importa-tu-cartera-de-clientes)
- [Paso 5: abre el panel de gestión](#paso-5-abre-el-panel-de-gestión)
- [Paso 6: corridas programadas](#paso-6-corridas-programadas)
- [Solución de problemas](#solución-de-problemas)

---

## Paso 0: requisitos

| Necesitas | Para qué |
|---|---|
| **Windows 10/11** | El proyecto está hecho para PowerShell + tareas programadas (funciona en macOS/Linux con ajustes menores) |
| **Python 3.12+** | Todo el backend (`python` en el PATH, no `python3`) |
| **Node.js 18+** | Instalar el cliente agéntico de IA (Gemini CLI u OpenCode) |
| Una **cuenta de Google** | Tu correo (personal `@gmail.com` o corporativo de Workspace) |
| Un **Excel con tus clientes** | El formato exacto lo pide el importador (ver Paso 4) |

### Instala el proyecto (una sola vez)

Abre un terminal (PowerShell o «Símbolo del sistema») **en la carpeta del
proyecto** y ejecuta:

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

La primera línea crea la carpeta **`.venv`**: un Python propio del proyecto
con sus librerías (si vienes de Node, es el `node_modules` del proyecto) y la
segunda las instala (el `npm install`). `.venv` no va al git, así que hay que
crearla en cada equipo donde se instale el proyecto.

> ⚠️ Todos los `.bat` (`Panel de Gestion.bat`, `Importar Clientes.bat`…) usan
> `.venv\Scripts\python.exe`. Si no has hecho este paso, Windows mostrará
> *«No se puede encontrar el archivo .venv\Scripts\python.exe»*.

---

## Paso 1: configura la IA (coste cero)

El sistema necesita un **runtime agéntico**: el "cerebro" que lee las
instrucciones del agente y usa las herramientas MCP. Elige UNA opción:

### 🥇 Opción A — Gemini CLI (recomendada: solo tu cuenta de Google)

Es la vía más sencilla y generosa: **1.000 solicitudes al día**, sin tarjeta.

1. Instala el cliente (necesitas Node.js 18+):

   ```powershell
   npm install -g @google/gemini-cli
   ```

2. Añade al proyecto el fichero `.gemini/settings.json` (copia del
   `.gemini/settings.example.json` incluido en el repo) para que el agente
   vea las herramientas MCP de Gmail/Calendar:

   ```json
   {
     "mcpServers": {
       "gmail-calendar": {
         "command": ".venv\\Scripts\\python.exe",
         "args": ["mcp-gmail\\servidor_mcp.py"],
         "cwd": "."
       }
     }
   }
   ```

3. Ejecuta `gemini` dentro de la carpeta del proyecto. La primera vez te
   pide iniciar sesión con tu cuenta de Google (navegador, sin contraseñas
   en el terminal) y ya puedes conversar con el asistente.

4. Las instrucciones de comportamiento del agente están en
   `docs/agente/instrucciones.md`. Indícale en la primera sesión:
   *"Lee docs/agente/instrucciones.md y datos/config.json: eres el asistente
   comercial de este proyecto"* — o guárdalo como contexto inicial del CLI.

> ℹ️ Si Google renombra o empaqueta este CLI de otra forma en el futuro, la
> pieza que importa es que soporte **servidores MCP**; la configuración es
> idéntica.

### 🥈 Opción B — OpenCode + clave Gemini API gratis

1. Consigue una **clave de API gratuita** en [Google AI Studio](https://aistudio.google.com) (sin tarjeta).
2. Instala OpenCode: `npm install -g opencode-ai`
3. En la carpeta del proyecto ejecuta `opencode`, luego:
   - `/connect` → elige **Google** → pega tu clave.
   - `/models` → elige un modelo Gemini.
4. El repo ya trae `opencode.json` con el servidor MCP de Gmail/Calendar
   registrado, así que no hay que configurar nada más.
5. Usa el modo conversación (`opencode`) o el modo corrida
   (`opencode run` — lo usan los scripts de `scripts/corrida.ps1`).

### 🥉 Opción C — OpenCode + GitHub Copilot Free

Si ya tienes cuenta de GitHub: `opencode` → `/connect` → **GitHub Copilot** →
sigue el flujo de dispositivo → `/models`. Aprovecha la cuota gratuita de
Copilot Free.

### 🖥️ Opción D — Ollama (100 % local, sin internet)

Si prefieres que ni el texto salga de tu PC: instala [Ollama](https://ollama.com),
descarga un modelo con herramientas (`ollama pull qwen3:8b`) y conecta
OpenCode a él (`/connect` → Ollama). Requiere un PC con suficiente memoria.

> **¿Cuánto consume una corrida?** El agente hace ~20-60 "pasos" (lecturas de
> mail, clasificaciones, borradores) por corrida. Con el límite gratuito de
> Gemini CLI (1.000/día) sobran pasadas para 2-3 corridas diarias de una
> cartera de cientos de mails.

---

## Paso 2: conecta tu correo y tu calendario (OAuth)

> 🔐 **No se recibe ninguna contraseña.** El login es OAuth 2.0 estándar:
> escribes tu contraseña **solo en la web de Google, en tu navegador**.
> La aplicación nunca la ve, nunca la pide, nunca la guarda — solo recibe un
> *token* de permiso que queda en tu disco y puedes revocar cuando quieras.
> Vale igual para un correo **personal** (`@gmail.com`) que **corporativo**
> (Google Workspace).

```text
┌──────────┐    1. abrir navegador     ┌─────────────────┐
│ autorizar│ ─────────────────────────▶│  Página de      │
│  .py     │                           │  Google (login) │
│          │ ◀─────────────────────────│  → "Permitir"   │
│          │    2. redirige a tu PC    └─────────────────┘
│          │    (localhost)
│          │    3. guarda SOLO el token local
└──────────┘
```

### Desde el panel (recomendado)

Panel → **⚙️ Configuración** → paso **Conectar Google**. El asistente:

1. Te guía por Google Cloud con enlaces directos a cada pantalla (los mismos
   pasos que el apartado *a* de abajo) y te deja marcar cada uno como hecho.
2. Te pide **arrastrar el `client_secret_….json`** que descargas: comprueba que
   es del tipo correcto y lo guarda como `mcp-gmail/credentials.json`.
3. Con **Conectar con Google** abre la web de Google; al aceptar vuelves al
   panel, que guarda el token en `mcp-gmail/token.json` y comprueba que has
   concedido **todos** los permisos.

Es el mismo OAuth que hace `autorizar.py`, pero sin consola. **Probar la
conexión** detecta si el acceso ha caducado.

### a) Crear la credencial en Google Cloud (una sola vez)

1. Entra en [Google Cloud Console](https://console.cloud.google.com) y crea un **proyecto** nuevo (p. ej. "Gestor Comercial").
2. **APIs y servicios → Biblioteca**: habilita **Gmail API** y **Google Calendar API**.
3. **Google Auth Platform** ([enlace](https://console.cloud.google.com/auth/overview)) → **Comenzar**:
   - Nombre de la app y tu correo de asistencia.
   - Público: **Externo** (o Interno si tu Workspace lo permite).
4. **Público → Publicar app** ([enlace](https://console.cloud.google.com/auth/audience)).
   Si la dejas en modo **Prueba** (*Testing*), Google caduca el acceso **cada
   7 días**. Publicada pero sin verificar funciona igual (Google muestra el aviso
   de «app no verificada» y admite hasta 100 usuarios: de sobra para uso
   personal). Con público **Interno** no hace falta.
5. **Clientes → Crear cliente** ([enlace](https://console.cloud.google.com/auth/clients)) → tipo **App de escritorio**.
6. En la ventana que aparece, **Descargar JSON** (solo se puede en ese momento)
   y guárdalo como `mcp-gmail/credentials.json` (o súbelo desde el asistente).
   El `.gitignore` ya lo excluye: nunca va al git ni a GitHub.

### b) Autorizar la app

```powershell
.venv\Scripts\python.exe mcp-gmail\autorizar.py
```

Se abre tu navegador → inicia sesión con el buzón a gestionar → revisa los
permisos → **Permitir**. El token se guarda en `mcp-gmail/token.json`
(local, excluido del git).

Los permisos que se piden son **mínimos y verificables**:

| Scope | Qué permite | Qué NO permite |
|---|---|---|
| `gmail.readonly` | Leer correos e hilos | Modificar o borrar nada |
| `gmail.compose` | Crear **borradores** | **Enviar** correos |
| `calendar.events` | Crear/listar/mover citas | Borrar tu calendario |

> ⚠️ **Aviso honesto sobre caducidad**: si la app sigue en modo *Prueba*
> (*Testing*), Google caduca el token cada **7 días** y hay que volver a
> conectar. Se evita publicándola (paso 4 del apartado *a*); después, vuelve
> a conectar una vez para obtener un token sin caducidad semanal.
> Si aparece la pantalla *"Google no ha verificado esta app"*, es normal para
> tu propia app: clic en *Configuración avanzada* → *Ir a <tu app> (no
> seguro)* → revisa los permisos → Permitir.

### c) Cuentas corporativas (Google Workspace)

Si tu empresa restringe el acceso de apps externas, el **administrador de
Workspace** debe permitir la app (o añadir tu client ID como app confiable).
Si no hay restricciones, el flujo es idéntico al personal.

### d) Revocar el acceso

Tu cuenta de Google → **Seguridad → Aplicaciones con acceso** → quitar la app,
y borra `mcp-gmail/token.json`. Sin rastros.

---

## Paso 3: personaliza tu configuración

**Desde el panel**: ⚙️ Configuración → **Tus datos** (formulario; el email se
rellena solo con la cuenta de Google conectada). **A mano**: copia
`datos/config.example.json` → `datos/config.json` y rellena:

- `asesor`: **tu** nombre, cargo y email (aparecen en el panel y en las firmas de los borradores).
- `empresa`: nombre, **dominios** de correo de tu empresa (para clasificar mails internos) y los **contactos** de cada departamento (averías, administración, facturación...) que el agente incluirá en las derivaciones.
- `reglas_*`: cadencia de captación y ventana de firma de presupuestos (los valores por defecto son razonables).
- `objetivo_anual`: tu objetivo de presupuestos firmados del año.

`datos/config.json` está excluido del git: tus datos nunca se publican.

---

## Paso 4: importa tu cartera de clientes

**Desde el panel**: ⚙️ Configuración → **Tus clientes** → *Descargar plantilla
Excel*, pega tus clientes (columnas `CÓD`, `NOMBRE`, `DOMICILIO`, `POBLACIÓN`,
`E-MAIL`, `TELÉFONO`) y arrástrala al recuadro. Verás cuántos se importaron,
cuántos tienen email/teléfono y los posibles duplicados.

**A mano**:

1. Deja tu Excel en la carpeta `entrada/`.
2. Doble clic en **`Importar Clientes.bat`** (o `python scripts/importar_clientes.py`).
3. El fichero se procesa y se mueve a `entrada/procesados/` con fecha.
4. La memoria de clientes vive en `datos/maestro_clientes.json` y la vista
   Excel de gestión se genera con `Sincronizar Excel.bat` (salida
   regenerable; nunca se edita a mano).

El importador espera un formato concreto de columnas (ver
`scripts/importar_clientes.py` y `tests/test_importador.py`). Si tu Excel es
diferente, adapta la lectura de columnas ahí — es la única pieza que
depende de tu formato.

---

## Paso 5: abre el panel de gestión

Doble clic en **`Panel de Gestion.bat`** → se abre `http://127.0.0.1:8765`.

> 🧪 **¿Quieres probar antes de importar nada real?** La primera vez que
> abres el panel, elige **Probar con datos de ejemplo**: carga una cartera
> **ficticia** (clientes, seguimientos, presupuestos, citas...) para explorarlo
> sin riesgo (también con `python scripts/demo_data.py`). Una franja amarilla
> te recuerda que es la demo; **Empezar con mis datos** la archiva en
> `datos/archivo/demo_<fecha>/` (no se borra) y abre el asistente.

- **Pendientes**: mails nuevos clasificados, urgentes arriba.
- **Borradores**: lo que el agente preparó para que revises y envíes.
- **Clientes / Presupuestos / Citas / Económico**: fichas y métricas.
- Las acciones del panel (recategorizar, marcar enviado, descartar, marcar
  captación...) **mandan sobre lo que el agente deduzca del correo**.

---

## Paso 6: corridas programadas

`Corrida Automatica.bat` ejecuta una corrida silenciosa del agente
(`scripts/corrida.ps1`). Para automatizarla:

1. **Programador de tareas de Windows** → Crear tarea básica.
2. Desencadenador: a diario a la hora que elijas (p. ej. 7:00 y 16:00).
3. Acción: iniciar `Corrida Automatica.bat` en la carpeta del proyecto.
4. La corrida procesa el buzón, actualiza `datos/` y deja borradores en Gmail.

También puedes ejecutarla a mano con **`Procesar Ahora.bat`** (ve el progreso).

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| *«No se puede encontrar el archivo .venv\Scripts\python.exe»* al abrir un `.bat` | Falta la carpeta `.venv` (no va al git) | Haz el Paso 0 → *Instala el proyecto* |
| `No hay token de acceso` | No has conectado Google aún | Panel → ⚙️ Configuración → Conectar Google (o `mcp-gmail/autorizar.py`) |
| El agente deja de leer mails a los 7 días | App en modo *Prueba* (Testing) en Google Cloud | Publica la app (Paso 2a, punto 4) y vuelve a conectar |
| El asistente dice *«Faltan permisos»* | Desmarcaste alguna casilla en la pantalla de Google | Vuelve a conectar y marca todas las casillas |
| *"Google no ha verificado esta app"* | Tu app no está verificada (normal) | Configuración avanzada → Ir a tu app → Permitir |
| `No model is available` | Runtime sin proveedor conectado | Repite el Paso 1 (`/connect` o login de Gemini CLI) |
| El panel no abre / `8765` ocupado | Quedó un proceso viejo | `netstat -ano \| findstr :8765` → mata el PID escuchando |
| El Excel no importa | Columnas con otro formato | Revisa `importar_clientes.py` y compara con tu fichero |
| El MCP no responde tras editar `servidor_mcp.py` | El servicio guarda la conexión vieja | Reinicia el runtime agéntico (en OpenCode: `opencode service restart`) |
