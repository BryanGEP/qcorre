"""Modo demo: un mundo simulado para enseñar qcorre sin tocar nada real.

``qcorre --demo`` abre la interfaz completa sobre procesos y repositorios de
mentira. Sirve para grabar el GIF del proyecto y para curiosear sin riesgo:
aquí matar un proceso o descartar cambios no afecta a tu compu.

El mundo responde a las acciones: los procesos que matas desaparecen, un
commit aparece en el historial, un push pone al día el mapa con el remoto...
Para lograrlo, ``DemoWorld`` implementa las mismas piezas que la app usa de
verdad (escáner, cierre de procesos y lecturas/acciones de git), pero en
memoria. No importa ni ``psutil`` ni ejecuta ``git``.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from qcorre import i18n
from qcorre.collectors.killer import KillResult, Victim
from qcorre.git import actions
from qcorre.git.actions import ActionPlan, ActionResult
from qcorre.git.backup import BACKUP_PREFIX, Backup
from qcorre.git.branches import Branch, BranchList
from qcorre.git.history import Commit, History, Ref, RefKind
from qcorre.git.parse import FileChange, RepoStatus
from qcorre.git.runner import GitError, GitResult
from qcorre.models import (
    DevProcess,
    OrphanReason,
    ProcessInfo,
    ProcessKind,
    Project,
    ProjectRoot,
    Snapshot,
)

MINUTE = 60.0
HOUR = 60 * MINUTE
DAY = 24 * HOUR

REMOTE = "origin"


def _pick(es: str, en: str) -> str:
    """Texto de los datos de ejemplo en el idioma activo."""
    return es if i18n.get_language() == "es" else en


# ── Repositorio simulado ────────────────────────────────────────


@dataclass
class _DemoBranch:
    name: str
    tip: str  # commit al que apunta en tu compu
    remote_tip: str | None = None  # commit al que apunta en el remoto (None = no está)
    gone: bool = False  # estuvo en el remoto, pero ya la borraron


@dataclass
class _DemoRepo:
    """Un repo en memoria: commits, ramas, cambios sin guardar y respaldos."""

    name: str
    current: str
    url: str
    commits: dict[str, Commit] = field(default_factory=dict)
    order: dict[str, int] = field(default_factory=dict)  # antigüedad de cada commit
    branches: dict[str, _DemoBranch] = field(default_factory=dict)
    remote_only: dict[str, str] = field(default_factory=dict)  # rama -> commit
    tags: dict[str, str] = field(default_factory=dict)  # etiqueta -> commit
    files: tuple[FileChange, ...] = ()
    last_sync: float = 0.0
    backups: list[Backup] = field(default_factory=list)
    saved_files: dict[str, tuple[FileChange, ...]] = field(default_factory=dict)
    committed: dict[str, tuple[FileChange, ...]] = field(default_factory=dict)
    # Commit que "alguien más" subió y que aparece al actualizar del remoto.
    incoming: tuple[str, Commit] | None = None

    # ── Construcción ────────────────────────────────────────────

    def add_commit(
        self, subject: str, parents: tuple[str, ...], author: str, when: float
    ) -> str:
        number = len(self.commits) + 1
        oid = hashlib.sha1(f"{self.name}-{number}-{subject}".encode()).hexdigest()
        self.commits[oid] = Commit(
            oid=oid, parents=parents, author=author, time=when, subject=subject
        )
        self.order[oid] = number
        return oid

    # ── Consultas ───────────────────────────────────────────────

    def ancestors(self, oid: str | None) -> set[str]:
        """El commit y todos los anteriores a él."""
        seen: set[str] = set()
        pending = [oid] if oid else []
        while pending:
            current = pending.pop()
            if current in seen or current not in self.commits:
                continue
            seen.add(current)
            pending.extend(self.commits[current].parents)
        return seen

    def ahead_behind(self, branch: _DemoBranch) -> tuple[int | None, int | None]:
        if branch.remote_tip is None:
            return None, None
        mine, theirs = self.ancestors(branch.tip), self.ancestors(branch.remote_tip)
        return len(mine - theirs), len(theirs - mine)

    def status(self) -> RepoStatus:
        branch = self.branches[self.current]
        ahead, behind = self.ahead_behind(branch)
        tip = self.commits[branch.tip]
        on_remote = branch.remote_tip is not None or branch.gone
        return RepoStatus(
            branch=branch.name,
            oid=branch.tip,
            upstream=f"{REMOTE}/{branch.name}" if on_remote else None,
            ahead=ahead,
            behind=behind,
            files=self.files,
            remotes=(REMOTE,),
            upstream_oid=branch.remote_tip[:7] if branch.remote_tip else None,
            remote_url=self.url,
            head_subject=tip.subject,
            has_parent=bool(tip.parents),
            last_sync=self.last_sync,
        )

    def branch_list(self) -> BranchList:
        reachable = self.ancestors(self.branches[self.current].tip)
        local = []
        for branch in self.branches.values():
            ahead, behind = self.ahead_behind(branch)
            on_remote = branch.remote_tip is not None or branch.gone
            local.append(
                Branch(
                    name=branch.name,
                    oid=branch.tip[:7],
                    current=branch.name == self.current,
                    upstream=f"{REMOTE}/{branch.name}" if on_remote else None,
                    ahead=ahead,
                    behind=behind,
                    gone=branch.gone,
                    merged=branch.tip in reachable,
                )
            )
        local.sort(key=lambda b: (not b.current, b.name.casefold()))
        remote_only = [
            Branch(name=name, oid=oid[:7], remote=REMOTE)
            for name, oid in sorted(self.remote_only.items())
        ]
        return BranchList(tuple(local), tuple(remote_only), self.last_sync)

    def history(self) -> History:
        refs: dict[str, list[Ref]] = {}
        tips: list[str] = []
        for branch in self.branches.values():
            kind = RefKind.HEAD if branch.name == self.current else RefKind.LOCAL
            refs.setdefault(branch.tip, []).append(Ref(kind, branch.name))
            tips.append(branch.tip)
            if branch.remote_tip:
                remote_ref = Ref(RefKind.REMOTE, f"{REMOTE}/{branch.name}")
                refs.setdefault(branch.remote_tip, []).append(remote_ref)
                tips.append(branch.remote_tip)
        for name, oid in self.remote_only.items():
            refs.setdefault(oid, []).append(Ref(RefKind.REMOTE, f"{REMOTE}/{name}"))
            tips.append(oid)
        for name, oid in self.tags.items():
            refs.setdefault(oid, []).append(Ref(RefKind.TAG, name))

        reachable: set[str] = set()
        for tip in tips:
            reachable |= self.ancestors(tip)
        # Los commits se numeran al crearse, así que "del más nuevo al más
        # viejo" deja siempre a los hijos antes que sus padres.
        ordered = sorted(reachable, key=lambda oid: self.order[oid], reverse=True)
        kinds = list(RefKind)
        commits = []
        for oid in ordered:
            commit = self.commits[oid]
            own = sorted(refs.get(oid, []), key=lambda r: (kinds.index(r.kind), r.name))
            commits.append(
                Commit(
                    oid=commit.oid,
                    parents=commit.parents,
                    refs=tuple(own),
                    author=commit.author,
                    time=commit.time,
                    subject=commit.subject,
                )
            )
        return History(tuple(commits))

    # ── Acciones ────────────────────────────────────────────────

    def apply(self, plan: ActionPlan, now: float) -> None:
        """Aplica el efecto de un plan sobre el repo simulado."""
        branch = self.branches[self.current]
        first = plan.commands[0]

        if plan.action == actions.COMMIT:
            message = plan.commands[1][2]
            oid = self.add_commit(message, (branch.tip,), _pick("Tú", "You"), now)
            self.committed[oid] = self.files
            branch.tip = oid
            self.files = ()
        elif plan.action == actions.PUSH:
            branch.remote_tip = branch.tip
            branch.gone = False
            self.last_sync = now
        elif plan.action == actions.PULL:
            if branch.remote_tip:
                branch.tip = branch.remote_tip
            self.last_sync = now
        elif plan.action == actions.FETCH:
            self.last_sync = now
            if self.incoming is not None:
                target, commit = self.incoming
                self.commits[commit.oid] = commit
                self.order[commit.oid] = len(self.order) + 1
                self.branches[target].remote_tip = commit.oid
                self.incoming = None
        elif plan.action == actions.SWITCH:
            if "--track" in first:
                name = first[2]
                tip = self.remote_only.pop(name)
                self.branches[name] = _DemoBranch(name, tip, remote_tip=tip)
            else:
                name = first[1]
            self.current = name
        elif plan.action == actions.NEW_BRANCH:
            name = first[2]
            self.branches[name] = _DemoBranch(name, branch.tip)
            self.current = name
        elif plan.action == actions.DELETE_BRANCH:
            self.branches.pop(first[2], None)
        elif plan.action == actions.UNDO_COMMIT:
            undone = self.commits[branch.tip]
            restored = self.committed.get(undone.oid) or (
                FileChange(_pick("archivo.py", "file.py"), index="M"),
            )
            # Los cambios del commit vuelven como "ya preparados" (reset --soft).
            staged = tuple(
                FileChange(f.path, index="A" if f.untracked else (f.index if f.index != "." else "M"))
                for f in restored
            )
            branch.tip = undone.parents[0]
            self.files = staged + self.files
        elif plan.action == actions.DISCARD:
            self.files = tuple(f for f in self.files if f.untracked)
        elif plan.action == actions.RESTORE:
            backup = next(b for b in self.backups if b.ref == first[2])
            branch.tip = backup.oid
            self.files = self.saved_files.get(backup.name, ())

    def make_backup(self, plan: ActionPlan, now: float) -> Backup | None:
        if not plan.backup_ref:
            return None
        branch = self.branches[self.current]
        name = plan.backup_ref[len(BACKUP_PREFIX) :]
        tracked = tuple(f for f in self.files if not f.untracked)
        backup = Backup(
            name=name,
            ref=f"{plan.backup_ref}/rama/{branch.name}",
            oid=branch.tip,
            operation=name.split("-", 2)[-1],
            created=now,
            branch=branch.name,
            changes_ref=f"{plan.backup_ref}/cambios" if tracked else None,
        )
        self.backups.insert(0, backup)
        self.saved_files[name] = self.files
        return backup


# ── El mundo completo ───────────────────────────────────────────


class DemoWorld:
    """Procesos y repos simulados, con las mismas piezas que usa la app real.

    ``delay`` es la pausa (en segundos) que simula el trabajo de git y del
    sistema, para que la demo se sienta real; los tests la ponen en cero.
    """

    def __init__(self, *, delay: float = 0.35, home: Path | None = None) -> None:
        self.delay = delay
        self.started = time.time()
        self.root = (home or Path.home()) / "code"
        self._next_pid = 4200
        self.projects: dict[str, tuple[ProjectRoot, list[DevProcess]]] = {}
        self.orphans: list[DevProcess] = []
        self.repos: dict[Path, _DemoRepo] = {}
        self._build_processes()
        self._build_repos()

    def as_kwargs(self) -> dict[str, Any]:
        """Argumentos para ``QcorreApp``: todas sus piezas, en versión simulada."""
        return {
            "scanner": self.scan,
            "killer": self,
            "git_reader": self.read_status,
            "git_executor": self.execute,
            "branch_reader": self.read_branches,
            "backup_reader": self.read_backups,
            "history_reader": self.read_history,
            "demo": True,
        }

    # ── Procesos ────────────────────────────────────────────────

    def scan(self) -> Snapshot:
        projects = [
            Project(root, tuple(sorted(processes, key=_order)))
            for root, processes in self.projects.values()
        ]
        projects.sort(key=lambda p: p.name.casefold())
        return Snapshot(tuple(projects), tuple(sorted(self.orphans, key=_order)))

    def preview(self, process: DevProcess) -> list[Victim]:
        return [Victim(m.pid, m.name, m.create_time) for m in process.members]

    def kill(self, victims: list[Victim]) -> KillResult:
        time.sleep(self.delay)
        pids = {victim.pid for victim in victims}
        denied: list[Victim] = []
        closed = 0

        def survives(process: DevProcess) -> bool:
            nonlocal closed
            if process.pid not in pids:
                return True
            if process.access_denied:
                # Igual que en la vida real: sin permiso, el sistema no deja cerrarlo.
                denied.extend(v for v in victims if v.pid in process.pids)
                return True
            closed += len(process.pids)
            return False

        for _, processes in self.projects.values():
            processes[:] = [p for p in processes if survives(p)]
        self.orphans[:] = [p for p in self.orphans if survives(p)]
        return KillResult(closed=closed, denied=tuple(denied))

    # ── Git ─────────────────────────────────────────────────────

    def _repo(self, path: Path) -> _DemoRepo:
        try:
            return self.repos[Path(path)]
        except KeyError:
            raise GitError("failed", f"fatal: not a git repository: {path}") from None

    def read_status(self, path: Path) -> RepoStatus:
        return self._repo(path).status()

    def read_branches(self, path: Path) -> BranchList:
        return self._repo(path).branch_list()

    def read_backups(self, path: Path) -> list[Backup]:
        return list(self._repo(path).backups)

    def read_history(self, path: Path) -> History:
        return self._repo(path).history()

    def execute(self, path: Path, plan: ActionPlan) -> ActionResult:
        """Simula la ejecución de un plan y devuelve un resultado como el real."""
        repo = self._repo(path)
        if plan.blocked or not plan.commands:
            return ActionResult(plan, error=GitError("failed", plan.blocked or ""))
        time.sleep(self.delay * (2 if plan.network else 1))
        now = time.time()
        tip_before = repo.branches[repo.current].tip
        backup = repo.make_backup(plan, now)
        repo.apply(plan, now)
        steps = tuple(GitResult(args, 0, "", "") for args in plan.commands)

        # Misma regla que en la ejecución real: si no cambió nada y no había
        # cambios que respaldar, el respaldo sobra.
        unchanged = False
        tip_after = repo.branches[repo.current].tip
        if backup is not None and backup.changes_ref is None and tip_after == tip_before:
            repo.backups.remove(backup)
            backup, unchanged = None, True
        return ActionResult(plan, steps, backup, unchanged=unchanged)

    # ── Datos de ejemplo ────────────────────────────────────────

    def _process(
        self,
        name: str,
        label: str,
        *ports: int,
        age: float,
        cwd: Path | None,
        cmdline: tuple[str, ...],
        kind: ProcessKind = ProcessKind.SERVER,
        reasons: tuple[OrphanReason, ...] = (),
        denied: bool = False,
        parent: str | None = "zsh",
        extra: tuple[tuple[str, tuple[str, ...]], ...] = (),
    ) -> DevProcess:
        """Un proceso simulado; ``extra`` son sus procesos hijos (nombre, comando)."""
        pid = self._next_pid
        self._next_pid += 7
        born = self.started - age
        leader = ProcessInfo(
            pid=pid,
            name=name,
            cmdline=() if denied else cmdline,
            cwd=None if denied or cwd is None else str(cwd),
            ports=tuple(ports),
            create_time=born,
            ppid=None if denied else (1 if parent is None else 900),
            access_denied=denied,
        )
        members = [leader]
        for child_name, child_cmdline in extra:
            child_pid = self._next_pid
            self._next_pid += 3
            members.append(
                ProcessInfo(
                    pid=child_pid,
                    name=child_name,
                    cmdline=child_cmdline,
                    cwd=leader.cwd,
                    create_time=born + 1,
                    ppid=pid,
                )
            )
        return DevProcess(
            info=leader,
            kind=kind,
            label=label,
            ports=tuple(ports),
            pids=tuple(m.pid for m in members),
            orphan_reasons=reasons,
            members=tuple(members),
            parent_name=parent,
        )

    def _build_processes(self) -> None:
        # Los nombres están pensados para que el proyecto principal quede arriba.
        api, web = self.root / "tienda-api", self.root / "tienda-web"
        blog = self.root / "web-personal"
        python = str(api / ".venv" / "bin" / "python")
        self.projects["tienda-api"] = (
            ProjectRoot(api, has_git=True),
            [
                self._process(
                    "python", "uvicorn", 8000, age=2 * HOUR + 14 * MINUTE, cwd=api,
                    cmdline=(python, "-m", "uvicorn", "app.main:app", "--reload"),
                    extra=(("python", (python, "-c", "from multiprocessing.spawn import spawn_main")),),
                ),
                self._process(
                    "postgres", "postgres", 5432, age=2 * HOUR + 15 * MINUTE, cwd=api / "data",
                    cmdline=("postgres", "-D", str(api / "data"), "-p", "5432"),
                    kind=ProcessKind.DATABASE,
                ),
                self._process(
                    "redis-server", "redis-server", 6379, age=2 * HOUR + 15 * MINUTE, cwd=api,
                    cmdline=("redis-server", "*:6379"), kind=ProcessKind.DATABASE,
                ),
                self._process(
                    "python", "celery", age=3 * DAY + 4 * HOUR, cwd=api,
                    cmdline=(python, "-m", "celery", "-A", "app.tasks", "worker"),
                    kind=ProcessKind.TOOL, parent=None,
                    reasons=(OrphanReason.LONG_RUNNING, OrphanReason.PARENT_GONE),
                ),
            ],
        )  # fmt: skip
        vite = str(web / "node_modules" / "vite" / "bin" / "vite.js")
        self.projects["tienda-web"] = (
            ProjectRoot(web, has_git=True),
            [
                self._process(
                    "node", "npm run dev → vite", 5173, age=41 * MINUTE, cwd=web,
                    cmdline=("node", "/usr/local/lib/node_modules/npm/bin/npm-cli.js", "run", "dev"),
                    extra=(("sh", ("sh", "-c", "vite")), ("node", ("node", vite))),
                ),
            ],
        )  # fmt: skip
        self.projects["web-personal"] = (
            ProjectRoot(blog, has_git=False),
            [
                self._process(
                    "hugo", "hugo", 1313, age=5 * HOUR + 2 * MINUTE, cwd=blog,
                    cmdline=("hugo", "server", "-D"),
                ),
            ],
        )  # fmt: skip
        self.orphans = [
            self._process(
                "node", "node server.js", 3000, age=3 * DAY + 4 * HOUR, cwd=Path.home() / "Downloads",
                cmdline=("node", "server.js"), parent=None,
                reasons=(OrphanReason.NO_PROJECT, OrphanReason.LONG_RUNNING, OrphanReason.PARENT_GONE),
            ),
            self._process(
                "python", "http.server", 8888, age=1 * DAY + 2 * HOUR, cwd=Path.home(),
                cmdline=("python3", "-m", "http.server", "8888"),
                reasons=(OrphanReason.NO_PROJECT, OrphanReason.LONG_RUNNING),
            ),
            self._process(
                "mysqld", "mysqld", 3306, age=6 * DAY, cwd=None, cmdline=(),
                kind=ProcessKind.DATABASE, denied=True, reasons=(OrphanReason.NO_PROJECT,),
            ),
        ]  # fmt: skip

    def _build_repos(self) -> None:
        now = self.started
        ana, luis = "Ana", "Luis"

        # tienda-api: una rama de trabajo con cambios, PRs mergeados y ramas viejas.
        api = _DemoRepo(
            "tienda-api", "feature/pagos", "https://github.com/ana/tienda-api.git",
            last_sync=now - 2 * HOUR,
        )  # fmt: skip
        a = api.add_commit(_pick("esqueleto del proyecto", "project skeleton"), (), ana, now - 9 * DAY)
        b = api.add_commit(_pick("modelo de productos", "product model"), (a,), ana, now - 8 * DAY)
        e1 = api.add_commit(_pick("prueba: caché en memoria", "spike: in-memory cache"), (b,), ana, now - 7 * DAY)
        c1 = api.add_commit(_pick("endpoint del carrito", "cart endpoint"), (b,), luis, now - 6 * DAY)
        c2 = api.add_commit(_pick("tests del carrito", "cart tests"), (c1,), luis, now - 5 * DAY)
        b2 = api.add_commit(_pick("paginación de productos", "product pagination"), (b,), ana, now - 5 * DAY)
        m1 = api.add_commit("Merge pull request #12 from ana/feat/carrito", (b2, c2), ana, now - 4 * DAY)
        l1 = api.add_commit(_pick("corrige expiración de sesión", "fix session expiry"), (m1,), ana, now - 3 * DAY)
        m2 = api.add_commit("Merge pull request #13 from ana/fix/login", (m1, l1), luis, now - 2 * DAY)
        s1 = api.add_commit(_pick("buscador: índice de productos", "search: product index"), (m2,), luis, now - 1 * DAY)
        p1 = api.add_commit(_pick("modelo de pagos", "payment model"), (m2,), ana, now - 20 * HOUR)
        p2 = api.add_commit(_pick("valida montos negativos", "validate negative amounts"), (p1,), ana, now - 3 * HOUR)
        api.branches = {
            "feature/pagos": _DemoBranch("feature/pagos", p2, remote_tip=p1),
            "main": _DemoBranch("main", m2, remote_tip=m2),
            "feat/carrito": _DemoBranch("feat/carrito", c2, gone=True),
            "experimento": _DemoBranch("experimento", e1),
        }
        api.remote_only = {"feat/buscador": s1}
        api.tags = {"v0.4.0": m1}
        api.files = (
            FileChange("app/pagos.py", worktree="M"),
            FileChange("app/models.py", index="M"),
            FileChange("tests/test_pagos.py", worktree="M"),
            FileChange("app/webhooks.py", untracked=True),
            FileChange(".env", untracked=True),
        )
        incoming_oid = hashlib.sha1(b"tienda-api-incoming").hexdigest()
        api.incoming = (
            "main",
            Commit(
                oid=incoming_oid,
                parents=(m2,),
                author=luis,
                time=now - 25 * MINUTE,
                subject=_pick("actualiza dependencias", "update dependencies"),
            ),
        )
        self.repos[self.root / "tienda-api"] = api

        # tienda-web: un repo tranquilo, al día con el remoto.
        web = _DemoRepo(
            "tienda-web", "main", "https://github.com/ana/tienda-web.git",
            last_sync=now - 35 * MINUTE,
        )  # fmt: skip
        tip = ""
        subjects = [
            (_pick("proyecto con vite", "vite project"), 12 * DAY),
            (_pick("página de inicio", "home page"), 10 * DAY),
            (_pick("listado de productos", "product list"), 6 * DAY),
            (_pick("carrito en el encabezado", "cart in the header"), 2 * DAY),
            (_pick("modo oscuro", "dark mode"), 4 * HOUR),
        ]
        for index, (subject, age) in enumerate(subjects):
            tip = web.add_commit(subject, (tip,) if tip else (), ana, now - age)
            if index == 2:
                web.tags = {"v0.3.0": tip}
        web.branches = {"main": _DemoBranch("main", tip, remote_tip=tip)}
        self.repos[self.root / "tienda-web"] = web


def _order(process: DevProcess) -> tuple:
    """Mismo orden que el agrupador real: con puertos primero, por puerto."""
    return (not process.ports, process.ports, process.label.casefold(), process.pid)
