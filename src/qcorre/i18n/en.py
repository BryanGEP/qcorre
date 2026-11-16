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
    "tag.idle": "nothing running",
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
    "git.loading": "Reading the repository…",
    "git.error.not_installed": "Couldn't find git on this machine.\nInstall it to see this section.",
    "git.error.timeout": "Git took too long to respond.",
    "git.error.failed": "Git answered with an error:",
    # Git: en qué rama estás
    "git.branch.on": "You are on branch {branch}",
    "git.branch.unborn": "You are on branch {branch}, which has no commits yet",
    "git.branch.detached": (
        "You are not on any branch: you are looking at commit {oid} directly"
    ),
    # Git: cambios sin guardar
    "git.changes.clean": "No pending changes: everything is saved in commits.",
    "git.changes.have": "You have {list}.",
    "git.changes.modified": {
        "one": "{n} file with changes not saved in a commit",
        "other": "{n} files with changes not saved in a commit",
    },
    "git.changes.new": {"one": "{n} new file", "other": "{n} new files"},
    "git.changes.new_only": {
        "one": "{n} new file that isn't in any commit yet",
        "other": "{n} new files that aren't in any commit yet",
    },
    "git.changes.conflict": {
        "one": "{n} file in conflict",
        "other": "{n} files in conflict",
    },
    "git.changes.staged": {
        "one": "{n} is already staged for the next commit (git add).",
        "other": "{n} are already staged for the next commit (git add).",
    },
    "git.conflicts.note": "Resolving conflicts is outside what qcorre does for now.",
    "git.files.more": {"one": "… and {n} more", "other": "… and {n} more"},
    "list.and": " and ",
    # Git: tu compu y el remoto
    "git.sync.no_remote": "This repo has no remote: it only exists on your machine.",
    "git.sync.unborn": "Once you make your first commit you can push it to the remote.",
    "git.sync.detached": "Without a branch there is nothing to push or pull.",
    "git.sync.no_upstream": (
        "Branch {branch} isn't on the remote yet: it only exists on your machine."
    ),
    "git.sync.gone": "Remote branch {upstream} no longer exists (maybe deleted after a merge).",
    "git.sync.even": "Your machine and {remote} have the same commits.",
    "git.sync.ahead": "You have {what}.",
    "git.sync.behind": {
        "one": "There is {n} commit on {remote} you haven't pulled.",
        "other": "There are {n} commits on {remote} you haven't pulled.",
    },
    "git.sync.diverged": "Your machine and {remote} have diverged: {push} and {pull}.",
    "git.sync.to_push": {"one": "{n} commit to push", "other": "{n} commits to push"},
    "git.sync.to_pull": {"one": "{n} commit to pull", "other": "{n} commits to pull"},
    "git.sync.nothing": "nothing to push or pull",
    "git.fetch.when": "As of the last check with the remote, {time} ago.",
    "git.fetch.never": "The remote hasn't been checked from this machine yet.",
    "map.local": "Your machine",
    "map.remote": "remote",
    "map.no_branch": "no branch",
    "map.no_commits": "no commits",
    "map.missing": "doesn't exist yet",
    "map.gone": "no longer exists",
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
    "kill.database_warning": {
        "one": "This is a database: force-closing it can interrupt operations in progress",
        "other": (
            "Includes databases ({names}): force-closing them can interrupt "
            "operations in progress"
        ),
    },
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
