"""Catálogo de textos en español."""

MESSAGES: dict[str, str | dict[str, str]] = {
    # Cabecera
    "app.tagline": "¿qué corre en tu compu?",
    "status.projects": {"one": "{n} proyecto", "other": "{n} proyectos"},
    "status.processes": {"one": "{n} proceso", "other": "{n} procesos"},
    # Panel de proyectos
    "panel.projects": "Proyectos",
    "projects.scanning": "Buscando procesos…",
    "projects.empty": (
        "No hay procesos de desarrollo corriendo.\n\n"
        "Arranca un servidor o una base de datos\ny aparecerá aquí."
    ),
    "group.orphans": "Huérfanos",
    "tag.no_git": "sin git",
    "tag.idle": "nada corriendo",
    "tag.denied": "sin permiso",
    # Motivos de huérfano
    "orphan.days": {"one": "lleva {n} día", "other": "lleva {n} días"},
    "orphan.hours": {"one": "lleva {n} hora", "other": "lleva {n} horas"},
    "orphan.minutes": {"one": "lleva {n} minuto", "other": "lleva {n} minutos"},
    "orphan.parent_gone": "su padre ya cerró",
    # Panel de git
    "panel.git": "Git",
    "git.empty": "Selecciona un proyecto para ver\nsu estado de git en lenguaje humano.",
    "git.no_repo": "Este proyecto no es un repositorio git.",
    "git.orphans": "Estos procesos no pertenecen a ningún proyecto.",
    "git.loading": "Leyendo el repositorio…",
    "git.error.not_installed": "No encontré git en esta compu.\nInstálalo para ver esta sección.",
    "git.error.timeout": "Git tardó demasiado en responder.",
    "git.error.failed": "Git respondió con un error:",
    # Git: en qué rama estás
    "git.branch.on": "Estás en la rama {branch}",
    "git.branch.unborn": "Estás en la rama {branch}, que todavía no tiene commits",
    "git.branch.detached": (
        "No estás en ninguna rama: estás viendo el commit {oid} directamente"
    ),
    # Git: cambios sin guardar
    "git.changes.clean": "No tienes cambios pendientes: todo está guardado en commits.",
    "git.changes.have": "Tienes {list}.",
    "git.changes.modified": {
        "one": "{n} archivo con cambios sin guardar en un commit",
        "other": "{n} archivos con cambios sin guardar en un commit",
    },
    "git.changes.new": {"one": "{n} archivo nuevo", "other": "{n} archivos nuevos"},
    "git.changes.new_only": {
        "one": "{n} archivo nuevo que aún no está en ningún commit",
        "other": "{n} archivos nuevos que aún no están en ningún commit",
    },
    "git.changes.conflict": {
        "one": "{n} archivo en conflicto",
        "other": "{n} archivos en conflicto",
    },
    "git.changes.staged": {
        "one": "{n} ya está preparado para el próximo commit (git add).",
        "other": "{n} ya están preparados para el próximo commit (git add).",
    },
    "git.conflicts.note": "Resolver conflictos queda fuera de lo que qcorre hace por ahora.",
    "git.files.more": {
        "one": "… y {n} más (tecla a para verlos todos)",
        "other": "… y {n} más (tecla a para verlos todos)",
    },
    "git.files.less": "tecla a para ver menos",
    "list.and": " y ",
    # Git: tu compu y el remoto
    "git.sync.no_remote": "Este repo no tiene remoto: solo existe en tu compu.",
    "git.sync.unborn": "Cuando hagas tu primer commit podrás subirlo al remoto.",
    "git.sync.detached": "Sin una rama no hay nada que subir ni bajar.",
    "git.sync.no_upstream": (
        "La rama {branch} todavía no está en el remoto: solo existe en tu compu."
    ),
    "git.sync.gone": "La rama remota {upstream} ya no existe (quizá la borraron tras un merge).",
    "git.sync.even": "Tu compu y {remote} tienen lo mismo.",
    "git.sync.ahead": "Tienes {what}.",
    "git.sync.behind": {
        "one": "Hay {n} commit en {remote} que no has bajado.",
        "other": "Hay {n} commits en {remote} que no has bajado.",
    },
    "git.sync.diverged": "Tu compu y {remote} se separaron: {push} y {pull}.",
    "git.sync.to_push": {"one": "{n} commit sin subir", "other": "{n} commits sin subir"},
    "git.sync.to_pull": {"one": "{n} commit sin bajar", "other": "{n} commits sin bajar"},
    "git.sync.nothing": "nada por subir ni por bajar",
    "git.fetch.when": "Según el último contacto con el remoto, hace {time}.",
    "git.fetch.never": "Aún no ha habido contacto con el remoto desde esta compu.",
    "map.local": "Tu compu",
    "map.remote": "remoto",
    "map.no_branch": "sin rama",
    "map.no_commits": "sin commits",
    "map.missing": "aún no existe",
    "map.gone": "ya no existe",
    # Diálogo de confirmación
    "confirm.what": "Qué va a pasar",
    "confirm.accept": "confirmar",
    "confirm.cancel": "cancelar",
    # Matar procesos
    "kill.title.process": "Matar proceso",
    "kill.title.project": "Matar todo en {name}",
    "kill.title.orphans": "Matar todos los huérfanos",
    "kill.confirm": "matar",
    "kill.summary": {
        "one": "Se cerrará {n} proceso del sistema",
        "other": "Se cerrarán {n} procesos del sistema",
    },
    "kill.ports": {
        "one": "Quedará libre el puerto {ports}",
        "other": "Quedarán libres los puertos {ports}",
    },
    "kill.method.posix": "Primero se les pide cerrar; lo que siga vivo tras 3 s se fuerza",
    "kill.method.windows": "En Windows el cierre es forzado e inmediato",
    "kill.denied_warning": "Hay procesos sin permiso: puede que no se dejen cerrar",
    "kill.database_warning": {
        "one": "Es una base de datos: cerrarla a la fuerza puede interrumpir operaciones en curso",
        "other": (
            "Incluye bases de datos ({names}): cerrarlas a la fuerza puede "
            "interrumpir operaciones en curso"
        ),
    },
    "kill.done": {"one": "Se cerró {n} proceso", "other": "Se cerraron {n} procesos"},
    "kill.denied": {
        "one": "{n} proceso no se dejó cerrar (sin permiso)",
        "other": "{n} procesos no se dejaron cerrar (sin permiso)",
    },
    "kill.survived": {"one": "{n} proceso sigue vivo", "other": "{n} procesos siguen vivos"},
    "kill.gone": "Ese proceso ya no existe",
    # Detalle de un proceso
    "detail.command": "Comando",
    "detail.cwd": "Carpeta",
    "detail.project": "Proyecto",
    "detail.pid": "PID",
    "detail.parent": "Padre",
    "detail.started": "Inicio",
    "detail.ports": "Puertos",
    "detail.status": "Aviso",
    "detail.members": {"one": "Incluye {n} proceso", "other": "Incluye {n} procesos"},
    "detail.unknown": "desconocido",
    "detail.denied": "sin permiso para leerlo",
    "detail.none": "ninguno",
    "detail.no_project": "sin proyecto",
    "detail.parent_gone": "ya cerró (era el pid {pid})",
    "detail.ago": "hace {time}",
    "info.close": "cerrar",
    # Acciones de git
    "action.commit.title": "Guardar cambios (commit)",
    "action.push.title": "Subir cambios (push)",
    "action.pull.title": "Bajar cambios (pull)",
    "action.fetch.title": "Actualizar del remoto (fetch)",
    "action.no_repo": "Selecciona un proyecto con repositorio git",
    "action.blocked.heading": "Ahora no se puede",
    "action.blocked.conflicts": (
        "Hay archivos en conflicto. Resolverlos queda fuera de lo que qcorre hace por ahora."
    ),
    "action.blocked.no_remote": "Este repo no tiene remoto: no hay a dónde conectarse.",
    "action.blocked.no_commits": (
        "Este repo todavía no tiene commits. Guarda tus cambios en un commit primero."
    ),
    "action.blocked.detached": (
        "No estás en ninguna rama. Cambia a una rama para poder subir o bajar."
    ),
    "action.effect.network": "Se conecta a la red: {where}",
    "action.backup": "Respaldo automático",
    "action.backup.note": "Si algo sale mal, tu rama se puede devolver a este punto.",
    "action.commands": {"one": "Comando exacto", "other": "Comandos exactos"},
    "action.commit.blocked.clean": "No hay cambios que guardar: todo está ya en commits.",
    "action.commit.effect.files": {
        "one": "Se guardará {n} archivo en un commit nuevo",
        "other": "Se guardarán {n} archivos en un commit nuevo (también los nuevos)",
    },
    "action.commit.effect.branch": "El commit queda en la rama {branch}",
    "action.commit.effect.detached": "Ojo: no estás en una rama; el commit quedará suelto",
    "action.commit.effect.local": (
        "Nada se sube: el commit vive solo en tu compu hasta que hagas push"
    ),
    "action.commit.prompt": "Describe qué cambiaste",
    "action.commit.placeholder": "p. ej. corrige el cálculo del total",
    "action.commit.empty": "Escribe un mensaje para poder guardar",
    "action.commit.message": "tu mensaje",
    "action.push.effect.new": "La rama {branch} se creará en {remote}",
    "action.push.effect.linked": (
        "Quedará enlazada: los próximos push y pull ya sabrán a dónde ir"
    ),
    "action.push.effect.commits": {
        "one": "Se subirá {n} commit a {upstream}",
        "other": "Se subirán {n} commits a {upstream}",
    },
    "action.push.blocked.behind": {
        "one": "{remote} tiene {n} commit que no has bajado. Baja primero (tecla l) y luego sube.",
        "other": (
            "{remote} tiene {n} commits que no has bajado. Baja primero (tecla l) y luego sube."
        ),
    },
    "action.push.blocked.nothing": (
        "No hay commits por subir: tu compu y {remote} tienen lo mismo."
    ),
    "action.pull.blocked.no_upstream": (
        "La rama {branch} todavía no está en el remoto: no hay nada que bajar."
    ),
    "action.pull.blocked.gone": (
        "La rama remota {upstream} ya no existe: no hay de dónde bajar."
    ),
    "action.pull.blocked.diverged": (
        "Tu compu y {remote} se separaron: cada uno tiene commits que el otro no. "
        "Combinarlos (merge o rebase) queda fuera de lo que qcorre hace por ahora."
    ),
    "action.pull.effect.commits": {
        "one": "Se bajará {n} commit de {upstream}",
        "other": "Se bajarán {n} commits de {upstream}",
    },
    "action.pull.effect.maybe_nothing": (
        "Según lo último que se sabe no hay nada nuevo; se pregunta al remoto por si acaso"
    ),
    "action.pull.effect.ff_only": (
        "Solo se avanza si no hay que mezclar nada; si no, git se detiene sin cambiar nada"
    ),
    "action.pull.effect.changes": {
        "one": "Tu archivo con cambios sin guardar no se toca",
        "other": "Tus {n} archivos con cambios sin guardar no se tocan",
    },
    "action.fetch.effect.ask": "Se pregunta a {remote} qué commits y ramas nuevas hay",
    "action.fetch.effect.safe": (
        "No cambia tus archivos ni tu rama: solo actualiza lo que se sabe del remoto"
    ),
    "action.confirm.commit": "guardar",
    "action.confirm.push": "subir",
    "action.confirm.pull": "bajar",
    "action.confirm.fetch": "actualizar",
    "action.running": "Trabajando…",
    "action.commit.done": "Cambios guardados en un commit",
    "action.push.done": "Cambios subidos al remoto",
    "action.pull.done": "Cambios bajados del remoto",
    "action.fetch.done": "Remoto actualizado",
    "action.failed.title": "No se pudo completar",
    "action.failed.command": "Comando",
    "action.failed.output": "Git respondió",
    "action.failed.backup": "Tu respaldo quedó guardado en",
    # Por qué falló una acción
    "failure.diverged": (
        "Tu compu y el remoto se separaron: no se puede avanzar sin mezclar. "
        "No se cambió nada."
    ),
    "failure.overwrite": (
        "Tienes cambios sin guardar en archivos que el remoto también cambió. "
        "Guárdalos en un commit y vuelve a intentar. No se cambió nada."
    ),
    "failure.rejected": (
        "El remoto tiene commits que no has bajado, así que rechazó la subida. "
        "Baja primero (tecla l)."
    ),
    "failure.auth": (
        "Git necesita que inicies sesión con el remoto. qcorre no pide "
        "contraseñas: haz un push o un pull desde tu terminal para iniciar "
        "sesión y vuelve a intentarlo aquí."
    ),
    "failure.network": "No se pudo llegar al remoto. Revisa tu conexión a internet.",
    "failure.identity": (
        "Git no sabe quién eres. Configura tu nombre y correo:\n"
        'git config --global user.name "Tu Nombre"\n'
        'git config --global user.email "tu@correo.com"'
    ),
    "failure.nothing_to_commit": "No había cambios que guardar.",
    "failure.locked": (
        "Otro programa está usando el repo en este momento. Espera un momento y reintenta."
    ),
    "failure.unknown": "Git no pudo completar la acción.",
    # Commit: archivos que entran y avisos
    "commit.files": {"one": "Entra {n} archivo", "other": "Entran {n} archivos"},
    "commit.sensitive.title": {
        "one": "Ojo: este archivo parece contener secretos",
        "other": "Ojo: estos archivos parecen contener secretos",
    },
    "commit.sensitive.advice": (
        "Si no deben subirse, cancela (esc) y agrégalos a tu .gitignore antes de guardar."
    ),
    "commit.scroll": "RePág / AvPág recorren la lista",
    # Ramas
    "action.switch.title": "Cambiar a la rama {branch}",
    "action.switch.blocked.current": "Ya estás en la rama {branch}.",
    "action.switch.effect.move": "Pasas de {origin} a {branch}",
    "action.switch.effect.track": "Se crea la rama local {branch}, enlazada a {upstream}",
    "action.switch.effect.files": "Tus archivos pasan a verse como están en esa rama",
    "action.switch.effect.changes": {
        "one": (
            "Tu archivo con cambios sin guardar se viene contigo; si choca con la otra "
            "rama, git se detiene sin cambiar nada"
        ),
        "other": (
            "Tus {n} archivos con cambios sin guardar se vienen contigo; si chocan con "
            "la otra rama, git se detiene sin cambiar nada"
        ),
    },
    "action.branch.title": "Crear una rama nueva",
    "action.branch.prompt": "Nombre de la rama nueva",
    "action.branch.placeholder": "p. ej. feat/buscador",
    "action.branch.invalid.empty": "Escribe un nombre para la rama",
    "action.branch.invalid.chars": (
        "El nombre no puede llevar espacios ni estos símbolos: ~ ^ : ? * [ \\"
    ),
    "action.branch.invalid.format": (
        "Ese nombre no sirve para una rama (revisa puntos, barras y guiones al inicio o al final)"
    ),
    "action.branch.effect.create": (
        "Se crea la rama {branch} a partir de {origin} y te cambias a ella"
    ),
    "action.branch.effect.changes": {
        "one": "Tu archivo con cambios sin guardar se viene contigo",
        "other": "Tus {n} archivos con cambios sin guardar se vienen contigo",
    },
    "action.branch.effect.local": "Solo existe en tu compu hasta que la subas (tecla p)",
    "action.delete.title": "Borrar la rama {branch}",
    "action.delete.blocked.current": (
        "No se puede borrar la rama en la que estás. Cámbiate a otra primero."
    ),
    "action.delete.blocked.remote": (
        "Esa rama solo existe en el remoto: aquí no hay nada que borrar."
    ),
    "action.delete.blocked.not_gone": (
        "Su rama remota todavía existe. qcorre solo ofrece borrar ramas cuya rama "
        "remota ya fue borrada."
    ),
    "action.delete.blocked.unmerged": (
        "La rama {branch} tiene commits que no están en {here}: borrarla perdería ese "
        "trabajo, así que no se ofrece. Si su PR ya se mergeó, cámbiate a la rama "
        "principal, baja los cambios (tecla l) y vuelve a intentarlo."
    ),
    "action.delete.effect.local": (
        "Se borra la rama {branch} de tu compu (su rama remota ya no existe)"
    ),
    "action.delete.effect.merged": "Todos sus commits ya están en {here}: no se pierde trabajo",
    "action.delete.effect.safe": (
        "Se usa «git branch -d», que se niega a borrar si quedara algo sin mergear"
    ),
    # Deshacer
    "action.undo.title": "Deshacer el último commit",
    "action.undo.blocked.no_commits": "Este repo todavía no tiene commits.",
    "action.undo.blocked.first": (
        "Es el primer commit del repo: no hay un commit anterior al cual volver."
    ),
    "action.undo.blocked.pushed": (
        "El último commit ya está subido al remoto. Deshacerlo obligaría a reescribir "
        "el remoto (push forzado), y eso qcorre no lo hace."
    ),
    "action.undo.effect.commit": 'Se deshace el commit "{subject}" ({oid})',
    "action.undo.effect.keep": "Sus cambios no se pierden: quedan como cambios sin guardar",
    "action.undo.effect.local": "Solo cambia tu compu: ese commit no está en el remoto",
    "action.discard.title": "Descartar los cambios sin guardar",
    "action.discard.blocked.nothing": (
        "No hay cambios que descartar en archivos que git ya sigue."
    ),
    "action.discard.effect.files": {
        "one": (
            "Se descartan los cambios de {n} archivo: vuelve a como estaba en el último commit"
        ),
        "other": (
            "Se descartan los cambios de {n} archivos: vuelven a como estaban en el "
            "último commit"
        ),
    },
    "action.discard.effect.added": (
        "Los archivos nuevos que ya habías preparado (git add) se borran del disco; "
        "quedan en el respaldo"
    ),
    "action.discard.effect.untracked": {
        "one": "Tu archivo nuevo que git aún no sigue no se toca",
        "other": "Tus {n} archivos nuevos que git aún no sigue no se tocan",
    },
    "action.discard.effect.backup": (
        "Antes se guarda un respaldo de esos cambios, por si te arrepientes"
    ),
    "action.restore.title": "Volver a un respaldo",
    "action.restore.blocked.branch": (
        "Este respaldo es de la rama {branch}. Cámbiate a esa rama (tecla b) para restaurarlo."
    ),
    "action.restore.effect.move": (
        "La rama {branch} vuelve al commit {oid}, donde estaba antes de {operation} ({when})"
    ),
    "action.restore.effect.changes": (
        "También se recuperan los cambios sin guardar de ese momento"
    ),
    "action.restore.effect.replace": {
        "one": "Tu archivo con cambios sin guardar de ahora se reemplaza",
        "other": "Tus {n} archivos con cambios sin guardar de ahora se reemplazan",
    },
    "action.restore.effect.backup": "Antes se guarda un respaldo de cómo está todo ahora",
    "action.confirm.switch": "cambiar",
    "action.confirm.branch": "crear",
    "action.confirm.delete": "borrar",
    "action.confirm.undo": "deshacer",
    "action.confirm.discard": "descartar",
    "action.confirm.restore": "restaurar",
    "action.switch.done": "Cambiaste de rama",
    "action.branch.done": "Rama creada: ya estás en ella",
    "action.delete.done": "Rama borrada",
    "action.undo.done": "Commit deshecho: sus cambios siguen aquí, sin guardar",
    "action.discard.done": "Cambios descartados (quedó un respaldo)",
    "action.restore.done": "Respaldo restaurado",
    "action.pull.nothing": "Ya estabas al día: no había nada que bajar",
    "failure.unmerged": (
        "Git no la considera mergeada (pasa cuando el PR se mergeó con squash). "
        "No se borró nada."
    ),
    "failure.exists": "Ya existe una rama con ese nombre.",
    "failure.branch_name": "Git no acepta ese nombre de rama.",
    "backup.op.pull": "bajar cambios",
    "backup.op.switch": "cambiar de rama",
    "backup.op.undo": "deshacer un commit",
    "backup.op.discard": "descartar cambios",
    "backup.op.restore": "restaurar un respaldo",
    # Vista de ramas
    "branches.title": "Ramas",
    "branches.local": "En tu compu",
    "branches.remote": "Solo en el remoto",
    "branches.remote.asof": "según el último contacto, hace {time}",
    "branches.remote.never": "aún sin contacto con el remoto",
    "branches.current": "estás aquí",
    "branches.even": "al día",
    "branches.local_only": "solo en tu compu",
    "branches.gone": "su rama remota ya no existe",
    "branches.merged": "ya mergeada",
    "branches.unmerged": "con trabajo sin mergear aquí",
    "branches.remote.hint": "al elegirla se crea la rama local que la sigue",
    "branches.key.switch": "cambiar",
    "branches.key.new": "nueva",
    "branches.key.delete": "borrar",
    "branches.delete.pick": "Elige una rama para borrarla",
    # Vista de deshacer
    "undo.title": "Deshacer",
    "undo.actions": "Qué quieres deshacer",
    "undo.commit": "El último commit",
    "undo.commit.none": "no hay commits",
    "undo.discard": "Los cambios sin guardar",
    "undo.discard.count": {"one": "{n} archivo", "other": "{n} archivos"},
    "undo.discard.none": "no hay cambios",
    "undo.backups": "Volver a un respaldo",
    "undo.backups.none": "Aún no hay respaldos: se crean solos antes de las acciones riesgosas",
    "undo.backup.item": "antes de {operation}",
    "undo.backup.branch": "rama {branch}",
    "undo.backup.changes": "con cambios sin guardar",
    "undo.key.select": "elegir",
    "picker.close": "cerrar",
    # Historial
    "git.tab.status": "Estado",
    "git.tab.history": "Historial",
    "git.tab.switch": "cambia de vista",
    "history.loading": "Leyendo el historial…",
    "history.empty": "Este repo todavía no tiene commits: aún no hay historial que mostrar.",
    "history.no_subject": "(sin mensaje)",
    "history.truncated": {
        "one": "Se muestra el commit más reciente; hay historial más antiguo.",
        "other": "Se muestran los {n} commits más recientes; hay historial más antiguo.",
    },
    # Ayuda
    "help.title": "Ayuda de qcorre",
    "help.section.move": "Moverse",
    "help.section.processes": "Procesos",
    "help.section.git": "Git del proyecto seleccionado",
    "help.section.app": "Aplicación",
    "help.move": "moverse por la lista de proyectos y procesos",
    "help.panel": "cambiar de panel (en el de git, las flechas lo recorren)",
    "help.enter": "ver el detalle de un proceso, o plegar un proyecto",
    "help.refresh": "volver a buscar procesos y releer git ahora",
    "help.kill": "matar el proceso seleccionado (pide confirmación)",
    "help.kill_all": "matar todos los procesos del proyecto",
    "help.commit": "guardar todos los cambios en un commit",
    "help.push": "subir tus commits al remoto",
    "help.pull": "bajar los commits del remoto",
    "help.fetch": "actualizar lo que se sabe del remoto, sin cambiar tus archivos",
    "help.branches": "ver las ramas: cambiar, crear o borrar una ya mergeada",
    "help.undo": "deshacer: el último commit, tus cambios, o volver a un respaldo",
    "help.history": "alternar entre el estado y el historial (gráfico de ramas)",
    "help.files": "ver todos los archivos con cambios, o solo los primeros",
    "help.language": "cambiar el idioma (español / inglés)",
    "help.help": "mostrar esta ayuda",
    "help.quit": "salir",
    "help.note.preview": (
        "Antes de cada acción verás qué va a pasar y el comando exacto. Nada se hace sin confirmar."
    ),
    "help.note.backup": (
        "Antes de las acciones riesgosas se guarda un respaldo en refs/qcorre/backup; "
        "se recupera con la tecla u."
    ),
    "help.note.limits": "qcorre no resuelve conflictos, ni hace merge, rebase o push forzado.",
    "status.demo": "DEMO",
    # Atajos del pie
    "hint.help": "ayuda",
    "hint.history": "historial",
    "hint.branches": "ramas",
    "hint.undo": "deshacer",
    "hint.commit": "commit",
    "hint.push": "push",
    "hint.pull": "pull",
    "hint.fetch": "actualizar",
    "hint.details": "detalle",
    "hint.move": "mover",
    "hint.kill": "matar",
    "hint.kill_all": "matar todos",
    "hint.panel": "panel",
    "hint.refresh": "refrescar",
    "hint.language": "idioma",
    "hint.quit": "salir",
}
