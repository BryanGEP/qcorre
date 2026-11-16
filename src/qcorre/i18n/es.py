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
    "git.fetch.when": "Según la última consulta al remoto, hace {time}.",
    "git.fetch.never": "Aún no se ha consultado el remoto desde esta compu.",
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
    # Atajos del pie
    "hint.details": "detalle",
    "hint.move": "mover",
    "hint.kill": "matar",
    "hint.kill_all": "matar todos",
    "hint.panel": "panel",
    "hint.refresh": "refrescar",
    "hint.language": "idioma",
    "hint.quit": "salir",
}
