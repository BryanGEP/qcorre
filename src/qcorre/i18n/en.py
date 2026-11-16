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
    # Diálogo de confirmación
    "confirm.what": "What will happen",
    "confirm.accept": "confirm",
    "confirm.cancel": "cancel",
    # Matar procesos
    "kill.title.process": "Kill process",
    "kill.title.project": "Kill everything in {name}",
    "kill.title.orphans": "Kill all orphans",
    "kill.confirm": "kill",
    "kill.summary": {
        "one": "{n} system process will be closed",
        "other": "{n} system processes will be closed",
    },
    "kill.ports": {
        "one": "Port {ports} will be freed",
        "other": "Ports {ports} will be freed",
    },
    "kill.method.posix": "They are asked to exit first; anything alive after 3 s is forced",
    "kill.method.windows": "On Windows processes are force-closed immediately",
    "kill.denied_warning": "Some processes deny access: they may refuse to close",
    "kill.done": {"one": "Closed {n} process", "other": "Closed {n} processes"},
    "kill.denied": {
        "one": "{n} process refused to close (no access)",
        "other": "{n} processes refused to close (no access)",
    },
    "kill.survived": {
        "one": "{n} process is still alive",
        "other": "{n} processes are still alive",
    },
    "kill.gone": "That process no longer exists",
    # Detalle de un proceso
    "detail.command": "Command",
    "detail.cwd": "Folder",
    "detail.project": "Project",
    "detail.pid": "PID",
    "detail.parent": "Parent",
    "detail.started": "Started",
    "detail.ports": "Ports",
    "detail.status": "Warning",
    "detail.members": {"one": "Includes {n} process", "other": "Includes {n} processes"},
    "detail.unknown": "unknown",
    "detail.denied": "no access to read it",
    "detail.none": "none",
    "detail.no_project": "no project",
    "detail.parent_gone": "already exited (was pid {pid})",
    "detail.ago": "{time} ago",
    "info.close": "close",
    # Atajos del pie
    "hint.details": "details",
    "hint.move": "move",
    "hint.kill": "kill",
    "hint.kill_all": "kill all",
    "hint.panel": "panel",
    "hint.refresh": "refresh",
    "hint.language": "language",
    "hint.quit": "quit",
}
