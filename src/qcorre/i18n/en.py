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
        "Start a server or a database\nand it will show up here.\n\n"
        "Want to see what it looks like? Try\nqcorre --demo"
    ),
    "group.orphans": "Orphans",
    "tag.no_git": "no git",
    "tag.idle": "nothing running",
    "tag.denied": "no access",
    # Motivos de huérfano
    "orphan.days": {"one": "up {n} day", "other": "up {n} days"},
    "orphan.hours": {"one": "up {n} hour", "other": "up {n} hours"},
    "orphan.minutes": {"one": "up {n} minute", "other": "up {n} minutes"},
    "orphan.parent_gone": "parent exited",
    # Panel de git
    "panel.git": "Git",
    "git.empty": (
        "The selected project's git shows up here.\n\n"
        "qcorre always lists the project of the folder\nyou open it from."
    ),
    "git.no_repo": "This project is not a git repository.",
    "git.orphans": "These processes don't belong to any project.",
    "git.loading": "Reading the repository…",
    "git.error.not_installed": "Couldn't find git on this machine.\nInstall it to see this section.",
    "git.error.timeout": "Git took too long to respond.",
    "git.error.failed": "Git answered with an error:",
    "git.error.hint.retry": "Press r to try again.",
    "git.error.hint.install": "Get it from https://git-scm.com and reopen qcorre.",
    "git.error.hint.not_repo": (
        "This folder is no longer a git repository (was .git moved or deleted?).\n"
        "Press r to try again."
    ),
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
    "git.files.more": {
        "one": "… and {n} more (key a to see them all)",
        "other": "… and {n} more (key a to see them all)",
    },
    "git.files.less": "key a to see fewer",
    "list.and": " and ",
    "git.files.secret": "secret?",
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
        "Git needs you to sign in to the remote. qcorre doesn't ask for "
        "passwords: run a push or a pull from your terminal to sign in, "
        "then try again here."
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
    # Commit: archivos que entran y avisos
    "commit.files": {"one": "{n} file goes in", "other": "{n} files go in"},
    "commit.sensitive.title": {
        "one": "Careful: this file looks like it contains secrets",
        "other": "Careful: these files look like they contain secrets",
    },
    "commit.sensitive.advice": (
        "If they shouldn't be uploaded, cancel (esc) and add them to your .gitignore first."
    ),
    "commit.scroll": "PgUp / PgDn scroll the list",
    # Ramas
    "action.switch.title": "Switch to branch {branch}",
    "action.switch.blocked.current": "You are already on branch {branch}.",
    "action.switch.effect.move": "You go from {origin} to {branch}",
    "action.switch.effect.track": "Local branch {branch} is created, linked to {upstream}",
    "action.switch.effect.files": "Your files change to how they are on that branch",
    "action.switch.effect.changes": {
        "one": (
            "Your file with unsaved changes comes with you; if it clashes with the "
            "other branch, git stops without changing anything"
        ),
        "other": (
            "Your {n} files with unsaved changes come with you; if they clash with "
            "the other branch, git stops without changing anything"
        ),
    },
    "action.branch.title": "Create a new branch",
    "action.branch.prompt": "Name of the new branch",
    "action.branch.placeholder": "e.g. feat/search",
    "action.branch.invalid.empty": "Type a name for the branch",
    "action.branch.invalid.chars": (
        "The name can't contain spaces or these symbols: ~ ^ : ? * [ \\"
    ),
    "action.branch.invalid.format": (
        "That name doesn't work for a branch (check leading or trailing dots, slashes and dashes)"
    ),
    "action.branch.effect.create": (
        "Branch {branch} is created from {origin} and you switch to it"
    ),
    "action.branch.effect.changes": {
        "one": "Your file with unsaved changes comes with you",
        "other": "Your {n} files with unsaved changes come with you",
    },
    "action.branch.effect.local": "It only exists on your machine until you push it (key p)",
    "action.delete.title": "Delete branch {branch}",
    "action.delete.blocked.current": (
        "You can't delete the branch you are on. Switch to another one first."
    ),
    "action.delete.blocked.remote": (
        "That branch only exists on the remote: there is nothing to delete here."
    ),
    "action.delete.blocked.not_gone": (
        "Its remote branch still exists. qcorre only offers to delete branches whose "
        "remote branch has been deleted."
    ),
    "action.delete.blocked.unmerged": (
        "Branch {branch} has commits that aren't in {here}: deleting it would lose "
        "that work, so it isn't offered. If its PR was merged, switch to the main "
        "branch, pull (key l) and try again."
    ),
    "action.delete.effect.local": (
        "Branch {branch} is deleted from your machine (its remote branch no longer exists)"
    ),
    "action.delete.effect.merged": "All its commits are already in {here}: no work is lost",
    "action.delete.effect.safe": (
        "It uses «git branch -d», which refuses to delete if anything were left unmerged"
    ),
    # Deshacer
    "action.undo.title": "Undo the last commit",
    "action.undo.blocked.no_commits": "This repo has no commits yet.",
    "action.undo.blocked.first": (
        "It's the first commit of the repo: there is no earlier commit to go back to."
    ),
    "action.undo.blocked.pushed": (
        "The last commit is already on the remote. Undoing it would require rewriting "
        "the remote (force push), which qcorre doesn't do."
    ),
    "action.undo.effect.commit": 'Commit "{subject}" ({oid}) is undone',
    "action.undo.effect.keep": "Its changes aren't lost: they become unsaved changes",
    "action.undo.effect.local": "Only your machine changes: that commit isn't on the remote",
    "action.discard.title": "Discard unsaved changes",
    "action.discard.blocked.nothing": (
        "There are no changes to discard in files git already tracks."
    ),
    "action.discard.effect.files": {
        "one": "Changes in {n} file are discarded: it goes back to the last commit",
        "other": "Changes in {n} files are discarded: they go back to the last commit",
    },
    "action.discard.effect.added": (
        "New files you had already staged (git add) are deleted from disk; "
        "they stay in the backup"
    ),
    "action.discard.effect.untracked": {
        "one": "Your new file that git doesn't track yet is left untouched",
        "other": "Your {n} new files that git doesn't track yet are left untouched",
    },
    "action.discard.effect.backup": (
        "A backup of those changes is saved first, in case you change your mind"
    ),
    "action.restore.title": "Go back to a backup",
    "action.restore.blocked.branch": (
        "This backup belongs to branch {branch}. Switch to that branch (key b) to restore it."
    ),
    "action.restore.effect.move": (
        "Branch {branch} goes back to commit {oid}, where it was before {operation} ({when})"
    ),
    "action.restore.effect.changes": (
        "The unsaved changes from that moment are recovered too"
    ),
    "action.restore.effect.replace": {
        "one": "Your current file with unsaved changes is replaced",
        "other": "Your {n} current files with unsaved changes are replaced",
    },
    "action.restore.effect.backup": "A backup of how everything is now is saved first",
    "action.confirm.switch": "switch",
    "action.confirm.branch": "create",
    "action.confirm.delete": "delete",
    "action.confirm.undo": "undo",
    "action.confirm.discard": "discard",
    "action.confirm.restore": "restore",
    "action.switch.done": "Switched branch",
    "action.branch.done": "Branch created: you are on it now",
    "action.delete.done": "Branch deleted",
    "action.undo.done": "Commit undone: its changes are still here, unsaved",
    "action.discard.done": "Changes discarded (a backup was kept)",
    "action.restore.done": "Backup restored",
    "action.pull.nothing": "You were already up to date: nothing to pull",
    "failure.unmerged": (
        "Git doesn't consider it merged (happens when the PR was squash-merged). "
        "Nothing was deleted."
    ),
    "failure.exists": "A branch with that name already exists.",
    "failure.branch_name": "Git doesn't accept that branch name.",
    "backup.op.pull": "pulling",
    "backup.op.switch": "switching branch",
    "backup.op.undo": "undoing a commit",
    "backup.op.discard": "discarding changes",
    "backup.op.restore": "restoring a backup",
    # Vista de ramas
    "branches.title": "Branches",
    "branches.local": "On your machine",
    "branches.remote": "Only on the remote",
    "branches.remote.asof": "as of the last contact, {time} ago",
    "branches.remote.never": "no contact with the remote yet",
    "branches.current": "you are here",
    "branches.even": "up to date",
    "branches.local_only": "only on your machine",
    "branches.gone": "its remote branch no longer exists",
    "branches.merged": "already merged",
    "branches.unmerged": "with work not merged here",
    "branches.remote.hint": "choosing it creates the local branch that follows it",
    "branches.key.switch": "switch",
    "branches.key.new": "new",
    "branches.key.delete": "delete",
    "branches.delete.pick": "Pick a branch to delete it",
    # Vista de deshacer
    "undo.title": "Undo",
    "undo.actions": "What do you want to undo",
    "undo.commit": "The last commit",
    "undo.commit.none": "no commits",
    "undo.discard": "Unsaved changes",
    "undo.discard.count": {"one": "{n} file", "other": "{n} files"},
    "undo.discard.none": "no changes",
    "undo.backups": "Go back to a backup",
    "undo.backups.none": "No backups yet: they are created automatically before risky actions",
    "undo.backup.item": "before {operation}",
    "undo.backup.branch": "branch {branch}",
    "undo.backup.changes": "with unsaved changes",
    "undo.key.select": "choose",
    "picker.close": "close",
    # Historial
    "git.tab.status": "Status",
    "git.tab.history": "History",
    "git.tab.switch": "switches view",
    "history.loading": "Reading the history…",
    "history.empty": "This repo has no commits yet: there is no history to show.",
    "history.no_subject": "(no message)",
    "history.truncated": {
        "one": "Showing the most recent commit; there is older history.",
        "other": "Showing the {n} most recent commits; there is older history.",
    },
    # Ayuda
    "help.title": "qcorre help",
    "help.section.move": "Moving around",
    "help.section.processes": "Processes",
    "help.section.git": "Git for the selected project",
    "help.section.app": "Application",
    "help.move": "move through the list of projects and processes",
    "help.panel": "switch panel (in the git panel, the arrows scroll it)",
    "help.jump": "jump straight to the projects panel (1) or the git panel (2)",
    "help.enter": "see a process's details, or collapse a project",
    "help.refresh": "look for processes and re-read git right now",
    "help.kill": "kill the selected process (asks for confirmation)",
    "help.kill_all": "kill every process of the project",
    "help.commit": "save all changes in a commit",
    "help.push": "upload your commits to the remote",
    "help.pull": "download the remote's commits",
    "help.fetch": "update what is known about the remote, without changing your files",
    "help.branches": "see the branches: switch, create, or delete a merged one",
    "help.undo": "undo: the last commit, your changes, or go back to a backup",
    "help.history": "toggle between the status and the history (branch graph)",
    "help.files": "see every changed file, or just the first ones",
    "help.language": "switch language (Spanish / English)",
    "help.help": "show this help",
    "help.quit": "quit",
    "help.note.preview": (
        "Before each action you see what will happen and the exact command. Nothing runs without confirming."
    ),
    "help.note.backup": (
        "Before risky actions a backup is saved under refs/qcorre/backup; "
        "recover it with the u key."
    ),
    "help.note.limits": "qcorre doesn't resolve conflicts, merge, rebase or force-push.",
    "status.demo": "DEMO",
    # Atajos del pie
    "hint.help": "help",
    "hint.history": "history",
    "hint.branches": "branches",
    "hint.undo": "undo",
    "hint.commit": "commit",
    "hint.push": "push",
    "hint.pull": "pull",
    "hint.fetch": "update",
    "hint.details": "details",
    "hint.move": "move",
    "hint.kill": "kill",
    "hint.kill_all": "kill all",
    "hint.scroll": "scroll",
    "hint.status": "status",
    "hint.collapse": "fold",
    "hint.to_git": "go to git",
    "hint.to_projects": "go to projects",
    "hint.refresh": "refresh",
    "hint.quit": "quit",
}
