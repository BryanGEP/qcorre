"""Tests del parseo de ``git status --porcelain=v2 --branch -z`` (sin ejecutar git)."""

from qcorre.git.parse import ChangeKind, FileChange, RepoStatus, parse_status
from qcorre.git.runner import format_command

OID = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
ZERO = "0" * 40


def porcelain(*records: str) -> str:
    """Une registros como lo hace git con ``-z``: cada uno termina en NUL."""
    return "".join(record + "\0" for record in records)


def ordinary(xy: str, path: str) -> str:
    return f"1 {xy} N... 100644 100644 100644 {ZERO} {ZERO} {path}"


HEADERS = (
    f"# branch.oid {OID}",
    "# branch.head feature/pagos",
    "# branch.upstream origin/feature/pagos",
    "# branch.ab +2 -1",
)


def test_cabeceras_de_rama_y_remoto():
    status = parse_status(porcelain(*HEADERS))
    assert status.branch == "feature/pagos"
    assert status.oid == OID
    assert status.short_oid == "a1b2c3d"
    assert status.upstream == "origin/feature/pagos"
    assert (status.ahead, status.behind) == (2, 1)
    assert status.is_clean
    assert not status.detached and status.has_commits and not status.upstream_gone


def test_repo_sin_commits():
    status = parse_status(porcelain("# branch.oid (initial)", "# branch.head main"))
    assert status.branch == "main"
    assert status.oid is None
    assert not status.has_commits
    assert status.upstream is None and status.ahead is None


def test_head_suelto():
    status = parse_status(porcelain(f"# branch.oid {OID}", "# branch.head (detached)"))
    assert status.detached
    assert status.branch is None
    assert status.short_oid == "a1b2c3d"


def test_rama_remota_borrada():
    # Hay upstream configurado pero git no da conteos: la rama remota no existe.
    status = parse_status(porcelain(*HEADERS[:3]))
    assert status.upstream == "origin/feature/pagos"
    assert status.upstream_gone


def test_tipos_de_cambio():
    status = parse_status(
        porcelain(
            *HEADERS,
            ordinary(".M", "editado.py"),
            ordinary("M.", "preparado.py"),
            ordinary("MM", "ambos.py"),
            ordinary("A.", "nuevo-preparado.py"),
            ordinary(".D", "borrado.py"),
            ordinary("D.", "borrado-preparado.py"),
            "? sin-seguir.txt",
            "! ignorado.log",
        )
    )
    kinds = {f.path: f.kind for f in status.files}
    assert kinds == {
        "editado.py": ChangeKind.MODIFIED,
        "preparado.py": ChangeKind.MODIFIED,
        "ambos.py": ChangeKind.MODIFIED,
        "nuevo-preparado.py": ChangeKind.NEW,
        "borrado.py": ChangeKind.DELETED,
        "borrado-preparado.py": ChangeKind.DELETED,
        "sin-seguir.txt": ChangeKind.NEW,
    }
    assert len(status.changed) == 5
    assert len(status.new) == 2
    assert {f.path for f in status.staged} == {
        "preparado.py",
        "ambos.py",
        "nuevo-preparado.py",
        "borrado-preparado.py",
    }
    assert not status.is_clean


def test_renombrado_ocupa_dos_registros():
    status = parse_status(
        porcelain(
            *HEADERS,
            f"2 R. N... 100644 100644 100644 {ZERO} {ZERO} R100 nuevo nombre.py",
            "viejo nombre.py",
            ordinary(".M", "despues.py"),
        )
    )
    renamed, after = status.files
    assert renamed.kind is ChangeKind.RENAMED
    assert renamed.path == "nuevo nombre.py"
    assert renamed.orig_path == "viejo nombre.py"
    assert after.path == "despues.py"  # el registro siguiente no se desalinea


def test_conflictos():
    status = parse_status(
        porcelain(
            *HEADERS,
            f"u UU N... 100644 100644 100644 100644 {ZERO} {ZERO} {ZERO} en conflicto.py",
        )
    )
    (conflict,) = status.conflicts
    assert conflict.path == "en conflicto.py"
    assert conflict.kind is ChangeKind.CONFLICT
    assert not conflict.staged
    assert status.changed == ()


def test_rutas_con_espacios_y_acentos():
    status = parse_status(porcelain(*HEADERS, ordinary(".M", "docs/guía de uso.md"), "? año 2026/"))
    assert [f.path for f in status.files] == ["docs/guía de uso.md", "año 2026/"]


def test_salida_vacia_o_rara_no_truena():
    assert parse_status("") == RepoStatus()
    status = parse_status(porcelain("# branch.ab cosa-rara", "1 incompleto", "x desconocido"))
    assert status.files == ()
    assert status.ahead is None


def test_nombre_del_remoto_y_de_la_rama():
    status = RepoStatus(branch="x", upstream="origin/feature/pagos", ahead=0, behind=0)
    assert status.remote_name == "origin"
    assert status.remote_branch == "feature/pagos"
    # Un remoto puede llevar "/" en el nombre: gana el remoto conocido más largo.
    weird = RepoStatus(
        branch="x", upstream="equipo/fork/main", ahead=0, behind=0, remotes=("equipo", "equipo/fork")
    )
    assert weird.remote_name == "equipo/fork"
    assert weird.remote_branch == "main"
    assert RepoStatus(branch="x").remote_name is None


def test_file_change_por_defecto():
    change = FileChange("a.py")
    assert change.kind is ChangeKind.MODIFIED
    assert not change.staged


def test_format_command_muestra_el_comando_como_se_teclea():
    assert format_command(["status", "--porcelain=v2"]) == "git status --porcelain=v2"
    assert format_command(["commit", "-m", "mi mensaje"]) == 'git commit -m "mi mensaje"'
    assert format_command(["commit", "-m", 'dice "hola"']) == 'git commit -m "dice \\"hola\\""'
    assert format_command(["add", ""]) == 'git add ""'
