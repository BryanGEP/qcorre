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
    "git.files.more": {"one": "… y {n} más", "other": "… y {n} más"},
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
        "El remoto no aceptó tus credenciales (o no hay ninguna guardada). "
        "Prueba un push desde tu terminal para iniciar sesión."
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
    # Atajos del pie
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
