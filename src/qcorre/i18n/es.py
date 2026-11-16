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
    # Atajos del pie
    "hint.move": "mover",
    "hint.panel": "panel",
    "hint.refresh": "refrescar",
    "hint.language": "idioma",
    "hint.quit": "salir",
}
