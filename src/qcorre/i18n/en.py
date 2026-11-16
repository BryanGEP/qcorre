"""Catálogo de textos en inglés."""

MESSAGES: dict[str, str | dict[str, str]] = {
    # Cabecera
    "app.tagline": "what's running on your machine?",
    "status.projects": {"one": "{n} project", "other": "{n} projects"},
    "status.processes": {"one": "{n} process", "other": "{n} processes"},
    # Panel de proyectos
    "panel.projects": "Projects",
    "projects.scanning": "Looking for processes…",
    "projects.empty": (
        "No dev processes are running.\n\n"
        "Start a server or a database\nand it will show up here."
    ),
    "group.orphans": "Orphans",
    "tag.no_git": "no git",
    "tag.denied": "no access",
    # Motivos de huérfano
    "orphan.days": {"one": "running for {n} day", "other": "running for {n} days"},
    "orphan.hours": {"one": "running for {n} hour", "other": "running for {n} hours"},
    "orphan.minutes": {"one": "running for {n} minute", "other": "running for {n} minutes"},
    "orphan.parent_gone": "its parent has exited",
    # Panel de git
    "panel.git": "Git",
    "git.empty": "Select a project to see its\ngit status in plain language.",
    "git.no_repo": "This project is not a git repository.",
    "git.orphans": "These processes don't belong to any project.",
    # Atajos del pie
    "hint.move": "move",
    "hint.panel": "panel",
    "hint.refresh": "refresh",
    "hint.language": "language",
    "hint.quit": "quit",
}
