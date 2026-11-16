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
    "git.fetch.when": "As of the last contact with the remote, {time} ago.",
    "git.fetch.never": "There has been no contact with the remote from this machine yet.",
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
    # Acciones de git
    "action.commit.title": "Save changes (commit)",
    "action.push.title": "Upload changes (push)",
    "action.pull.title": "Download changes (pull)",
    "action.fetch.title": "Update from remote (fetch)",
    "action.no_repo": "Select a project with a git repository",
    "action.blocked.heading": "Not possible right now",
    "action.blocked.conflicts": (
        "Some files are in conflict. Resolving them is outside what qcorre does for now."
    ),
    "action.blocked.no_remote": "This repo has no remote: there is nowhere to connect to.",
    "action.blocked.no_commits": (
        "This repo has no commits yet. Save your changes in a commit first."
    ),
    "action.blocked.detached": (
        "You are not on any branch. Switch to a branch to push or pull."
    ),
    "action.effect.network": "Connects to the network: {where}",
    "action.backup": "Automatic backup",
    "action.backup.note": "If something goes wrong, your branch can be moved back to this point.",
    "action.commands": {"one": "Exact command", "other": "Exact commands"},
    "action.commit.blocked.clean": "Nothing to save: everything is already in commits.",
    "action.commit.effect.files": {
        "one": "{n} file will be saved in a new commit",
        "other": "{n} files will be saved in a new commit (new files included)",
    },
    "action.commit.effect.branch": "The commit goes on branch {branch}",
    "action.commit.effect.detached": "Careful: you are not on a branch; the commit will be loose",
    "action.commit.effect.local": (
        "Nothing is uploaded: the commit lives only on your machine until you push"
    ),
    "action.commit.prompt": "Describe what you changed",
    "action.commit.placeholder": "e.g. fix the total calculation",
    "action.commit.empty": "Type a message to be able to save",
    "action.commit.message": "your message",
    "action.push.effect.new": "Branch {branch} will be created on {remote}",
    "action.push.effect.linked": (
        "It will be linked: future pushes and pulls will know where to go"
    ),
    "action.push.effect.commits": {
        "one": "{n} commit will be uploaded to {upstream}",
        "other": "{n} commits will be uploaded to {upstream}",
    },
    "action.push.blocked.behind": {
        "one": "{remote} has {n} commit you haven't pulled. Pull first (key l), then push.",
        "other": "{remote} has {n} commits you haven't pulled. Pull first (key l), then push.",
    },
    "action.push.blocked.nothing": (
        "No commits to push: your machine and {remote} have the same commits."
    ),
    "action.pull.blocked.no_upstream": (
        "Branch {branch} isn't on the remote yet: there is nothing to pull."
    ),
    "action.pull.blocked.gone": (
        "Remote branch {upstream} no longer exists: there is nowhere to pull from."
    ),
    "action.pull.blocked.diverged": (
        "Your machine and {remote} have diverged: each has commits the other lacks. "
        "Combining them (merge or rebase) is outside what qcorre does for now."
    ),
    "action.pull.effect.commits": {
        "one": "{n} commit will be downloaded from {upstream}",
        "other": "{n} commits will be downloaded from {upstream}",
    },
    "action.pull.effect.maybe_nothing": (
        "As far as is known there is nothing new; the remote is asked just in case"
    ),
    "action.pull.effect.ff_only": (
        "It only moves forward if nothing needs merging; otherwise git stops without changes"
    ),
    "action.pull.effect.changes": {
        "one": "Your file with unsaved changes is left untouched",
        "other": "Your {n} files with unsaved changes are left untouched",
    },
    "action.fetch.effect.ask": "Asks {remote} which new commits and branches exist",
    "action.fetch.effect.safe": (
        "Doesn't change your files or your branch: it only updates what is known about the remote"
    ),
    "action.confirm.commit": "save",
    "action.confirm.push": "push",
    "action.confirm.pull": "pull",
    "action.confirm.fetch": "update",
    "action.running": "Working…",
    "action.commit.done": "Changes saved in a commit",
    "action.push.done": "Changes uploaded to the remote",
    "action.pull.done": "Changes downloaded from the remote",
    "action.fetch.done": "Remote updated",
    "action.failed.title": "Couldn't complete",
    "action.failed.command": "Command",
    "action.failed.output": "Git answered",
    "action.failed.backup": "Your backup was saved at",
    # Por qué falló una acción
    "failure.diverged": (
        "Your machine and the remote have diverged: can't move forward without merging. "
        "Nothing was changed."
    ),
    "failure.overwrite": (
        "You have unsaved changes in files the remote also changed. "
        "Save them in a commit and try again. Nothing was changed."
    ),
    "failure.rejected": (
        "The remote has commits you haven't pulled, so it rejected the push. "
        "Pull first (key l)."
    ),
    "failure.auth": (
        "The remote didn't accept your credentials (or none are saved). "
        "Try a push from your terminal to sign in."
    ),
    "failure.network": "Couldn't reach the remote. Check your internet connection.",
    "failure.identity": (
        "Git doesn't know who you are. Set your name and email:\n"
        'git config --global user.name "Your Name"\n'
        'git config --global user.email "you@example.com"'
    ),
    "failure.nothing_to_commit": "There were no changes to save.",
    "failure.locked": (
        "Another program is using the repo right now. Wait a moment and retry."
    ),
    "failure.unknown": "Git couldn't complete the action.",
    # Atajos del pie
    "hint.commit": "commit",
    "hint.push": "push",
    "hint.pull": "pull",
    "hint.fetch": "update",
    "hint.details": "details",
    "hint.move": "move",
    "hint.kill": "kill",
    "hint.kill_all": "kill all",
    "hint.panel": "panel",
    "hint.refresh": "refresh",
    "hint.language": "language",
    "hint.quit": "quit",
}
