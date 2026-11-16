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
