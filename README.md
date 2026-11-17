# qcorre

**¿Qué corre en tu compu?** Un panel del desarrollador para la terminal.

[English](README.en.md) · Español

<!-- Cuando exista el GIF: ![qcorre en acción](docs/demo.gif) -->

```
▍qcorre  ¿qué corre en tu compu?                          3 proyectos · 9 procesos · ES
╭─ Proyectos ──────────────────────────╮╭─ tienda-api · feature/pagos ─────────────────╮
│ ▼ tienda-api  4  ⚠                   ││ Estado   Historial     h cambia de vista     │
│    ● postgres      :5432  2h 15m     ││                                              │
│    ● redis-server  :6379  2h 15m     ││ Estás en la rama feature/pagos               │
│    ● uvicorn       :8000  2h 14m     ││                                              │
│    ⚠ celery               3d 4h      ││ Tienes 3 archivos con cambios sin guardar    │
│      ╰ lleva 3 días · su padre ya…   ││ en un commit y 2 archivos nuevos.            │
│ ▼ tienda-web  1                      ││                                              │
│    ● npm run dev → vite  :5173  41m  ││ ╭─ Tu compu ─────╮          ╭─ origin ──────╮│
│ ▼ ⚠ Huérfanos  3                     ││ │ feature/pagos  │ ── 1 ↑ ─►│ feature/pagos ││
│    ⚠ node server.js  :3000  3d 4h    ││ │ 3400d6e        │ ◄─────── │ 487c736       ││
╰──────────────────────────────────────╯╰──────────────────────────────────────────────╯
 ↑↓ mover   tab panel   enter detalle   k matar   K matar todos   r refrescar
 c commit   p push   l pull   f actualizar   b ramas   u deshacer   h historial   ? ayuda
```

## Qué hace

**Procesos por proyecto.** Detecta tus servidores, bases de datos y herramientas
de desarrollo, con sus puertos, y los agrupa según el repo git (o la carpeta de
proyecto) desde donde corren.

- Un servidor y sus procesos hijos se muestran como una sola fila
  (`npm run dev → vite`).
- Marca los **huérfanos**: procesos sin proyecto, que llevan más de un día
  corriendo o cuyo proceso padre ya cerró.
- Mata un proceso o todos los de un proyecto, siempre con una confirmación que
  lista exactamente qué se va a cerrar.

**Git en lenguaje humano**, para el proyecto seleccionado.

- **Estado explicado:** "Tienes 3 archivos con cambios sin guardar en un commit".
- **Mapa tu compu ↔ remoto:** cuántos commits tienes sin subir y sin bajar.
- **Acciones con vista previa:** commit, push, pull, actualizar del remoto,
  ramas y deshacer. Antes de cada una ves qué va a pasar y el comando git
  exacto. Nada se ejecuta sin confirmar.
- **Red de seguridad:** antes de una acción riesgosa se guarda un respaldo
  (en `refs/qcorre/backup/`) al que puedes volver.
- **Historial** como gráfico de ramas con colores.

La interfaz está en español e inglés (tecla `i`).

## Instalación

Necesitas Python 3.10 o superior y `git` instalado. Funciona en Windows, macOS
y Linux.

qcorre todavía no está publicado en PyPI. Mientras tanto, se instala desde el
repositorio:

```bash
pipx install git+https://github.com/BryanGEP/qcorre
# o, sin instalar nada de forma permanente:
uvx --from git+https://github.com/BryanGEP/qcorre qcorre
```

Cuando esté en PyPI bastará con `pipx install qcorre` o `uvx qcorre`.

## Uso

```bash
qcorre                    # abre el panel; el proyecto de la carpeta actual siempre aparece
qcorre ruta/al/proyecto   # igual, fijando otro proyecto
qcorre --demo             # datos simulados: prueba todo sin tocar nada real
qcorre --lang en          # fuerza el idioma (es / en)
qcorre --orphan-hours 8   # marca como huérfano lo que lleve más de 8 horas
```

`qcorre --demo` abre la interfaz completa sobre procesos y repos de mentira que
responden a tus acciones. Es la forma más rápida de conocerlo.

### Atajos

| Tecla | Qué hace |
|---|---|
| `↑` `↓` | Moverse por proyectos y procesos |
| `tab` | Cambiar de panel |
| `enter` | Detalle del proceso (comando completo, carpeta, PID, padre) |
| `k` / `K` | Matar el proceso / todos los del proyecto |
| `r` | Refrescar ahora (también se refresca solo cada 3 s) |
| `c` | Guardar los cambios en un commit |
| `p` / `l` | Subir (push) / bajar (pull) |
| `f` | Actualizar del remoto (fetch) |
| `b` | Ramas: cambiar, crear (`n`) o borrar una ya mergeada (`d`) |
| `u` | Deshacer: el último commit, tus cambios, o volver a un respaldo |
| `h` | Alternar entre el estado y el historial |
| `a` | Ver todos los archivos con cambios |
| `i` | Cambiar de idioma |
| `?` | Ayuda |
| `q` | Salir |

## Cómo decide a qué proyecto pertenece un proceso

Por orden: la carpeta de trabajo del proceso, las rutas de su línea de comandos,
la ruta de su ejecutable y, si nada de eso sirve, el proyecto de su proceso
padre. Desde esa carpeta sube buscando un `.git`; si no hay repo, vale la
carpeta más cercana con un archivo de proyecto (`package.json`,
`pyproject.toml`, `Cargo.toml`, `go.mod`…).

Los procesos que el sistema no deja leer (muy común en Windows con procesos de
servicio) se muestran igual, marcados como **sin permiso**.

## Qué hace y qué no hace con tu repo

qcorre usa el `git` de tu sistema, así que cualquier cosa que haga es algo que
podrías teclear tú. Está pensado para no dar sustos:

- El **pull** solo avanza si no hay que mezclar nada (`--ff-only`).
- **Nunca** hace push forzado ni `git branch -D`.
- **Deshacer un commit** conserva sus cambios, y solo se ofrece si ese commit
  aún no está en el remoto.
- El **commit** guarda todos los cambios (`git add -A`), te lista los archivos
  que entran y te avisa si alguno parece contener secretos (`.env`, `*.pem`,
  `id_rsa`…).
- Nunca te pide contraseñas: si el remoto necesita que inicies sesión, te lo
  dice y lo haces desde tu terminal.
- Mientras solo miras, no toca nada: ni la red ni el índice del repo.

Los respaldos son referencias normales de git. Puedes verlos con
`git for-each-ref refs/qcorre/backup` y borrarlos con `git update-ref -d <ref>`.

### Limitaciones

- No resuelve conflictos, ni hace merge o rebase. Si tu rama y el remoto se
  separaron, te lo explica y te deja resolverlo a tu manera.
- El respaldo de los cambios sin guardar no incluye archivos nuevos que git
  todavía no sigue.
- Los contenedores Docker aparecen como procesos de Docker, sin proyecto.
- Una rama mergeada con *squash* en GitHub no cuenta como mergeada para git, así
  que no se ofrece borrarla.

## Desarrollo

```bash
git clone https://github.com/BryanGEP/qcorre
cd qcorre
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"

pytest             # tests (lógica, git contra repos temporales e interfaz)
ruff check .       # estilo
qcorre --demo      # la interfaz con datos simulados
```

El código está separado en capas para poder testear la lógica sin la interfaz:

| Carpeta | Responsabilidad |
|---|---|
| `src/qcorre/collectors/` | Leer procesos y puertos del sistema (psutil) y cerrarlos |
| `src/qcorre/projects/` | Decidir el proyecto de cada proceso y agruparlos (lógica pura) |
| `src/qcorre/git/` | Leer el repo, preparar y ejecutar acciones, respaldos, historial |
| `src/qcorre/ui/` | La interfaz (Textual). Solo presentación |
| `src/qcorre/i18n/` | Textos en español e inglés |
| `src/qcorre/demo.py` | El mundo simulado de `--demo` |

Para grabar el GIF de presentación, abre `qcorre --demo` en una terminal de
unas 120×34 columnas: los datos simulados responden a las acciones (matar un
proceso, commit, push, ramas, historial), así que el recorrido se puede repetir
las veces que haga falta sin tocar nada real.

Los cambios se describen en [CHANGELOG.md](CHANGELOG.md).

## Licencia

[MIT](LICENSE)
