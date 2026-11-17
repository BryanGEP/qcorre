"""Graba el GIF de demostración y las capturas del README.

Uso (desde la raíz del repo)::

    pip install -e ".[dev]" pillow
    python scripts/record_demo.py            # inglés: docs/demo.gif y docs/screenshots/*.png
    python scripts/record_demo.py --lang es  # español: docs/demo.es.gif y *.es.png

Cómo funciona: abre ``qcorre --demo`` sin terminal real (con el Pilot de
Textual), recorre un guion fijo y en cada paso exporta la pantalla como SVG.
Después un navegador Chromium (Edge o Chrome) en modo headless convierte cada
SVG en PNG, y Pillow une los PNG en un GIF.

No toca nada real: usa el mundo simulado de ``qcorre.demo``. Necesita Pillow,
un navegador Chromium instalado y, la primera vez, internet (el navegador baja
la tipografía Fira Code con la que Textual dibuja las capturas).
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from qcorre import i18n
from qcorre.demo import DemoWorld
from qcorre.ui.app import QcorreApp
from qcorre.ui.projects_panel import ProjectsPanel

# Tamaño de la terminal simulada (columnas, filas).
SIZE = (108, 30)

# Colores del GIF. Con menos, pesa menos; con muy pocos, el texto pierde suavizado.
COLORS = 160

# Fondo de la página: el mismo gris del marco de la ventana, para que las
# esquinas redondeadas no dejen píxeles de otro color.
FRAME_BACKGROUND = "#292929"

BROWSERS = (
    "msedge",
    "chromium",
    "chromium-browser",
    "google-chrome",
    "chrome",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
)

# Mensaje del commit que se "teclea" en la demo, por idioma.
COMMIT_MESSAGE = {"en": "add payment webhooks", "es": "agrega webhooks de pagos"}


@dataclass
class Frame:
    svg: str
    seconds: float


class Recorder:
    """Lleva la app por el guion y va guardando fotogramas."""

    def __init__(self, app: QcorreApp, pilot) -> None:
        self.app = app
        self.pilot = pilot
        self.frames: list[Frame] = []
        self.stills: dict[str, str] = {}

    async def settle(self) -> None:
        """Espera a que terminen los trabajos en segundo plano y se pinte todo."""
        calm = 0
        for _ in range(60):
            await self.app.workers.wait_for_complete()
            await self.pilot.pause(0.03)
            calm = 0 if any(w.is_running for w in self.app.workers) else calm + 1
            if calm >= 2:
                return

    async def snap(self, seconds: float, still: str | None = None) -> None:
        """Guarda la pantalla actual, que se mostrará durante ``seconds``."""
        await self.pilot.pause(0.05)
        svg = self.app.export_screenshot(title="qcorre")
        self.frames.append(Frame(svg, seconds))
        if still:
            self.stills[still] = svg

    async def press(self, *keys: str, seconds: float = 0.0, still: str | None = None) -> None:
        """Pulsa teclas; con ``seconds`` guarda además un fotograma."""
        await self.pilot.press(*keys)
        if len(self.app.screen_stack) == 1:
            await self.settle()  # con un diálogo abierto hay un trabajo esperando
        else:
            await self.pilot.pause(0.1)
        if seconds:
            await self.snap(seconds, still)

    async def move_to(self, fragment: str, seconds: float = 0.3) -> None:
        """Baja con el cursor, fila a fila, hasta la que contiene ``fragment``."""
        tree = self.app.query_one(ProjectsPanel).tree
        for _ in range(tree.last_line + 1):
            node = tree.cursor_node
            if node is not None and fragment in str(node.label):
                return
            await self.press("down", seconds=seconds)
        raise RuntimeError(f"no hay ninguna fila con {fragment!r}")

    async def type(self, text: str, chunk: int = 4, seconds: float = 0.22) -> None:
        """Teclea ``text`` de a pocos caracteres, con un fotograma por trozo."""
        for start in range(0, len(text), chunk):
            await self.pilot.press(*text[start : start + chunk])
            await self.snap(seconds)

    def clear_toasts(self) -> None:
        self.app.clear_notifications()


async def storyboard(rec: Recorder, lang: str) -> None:
    """El recorrido de la demo: unos 28 segundos por las funciones principales."""
    # 1. El panel: procesos agrupados por proyecto, con puertos y huérfanos.
    await rec.snap(2.0, still="processes")

    # 2. Detalle de un proceso.
    await rec.move_to("uvicorn")
    await rec.press("enter", seconds=2.4)
    await rec.press("escape", seconds=0.5)

    # 3. Matar el proceso huérfano, con confirmación.
    await rec.move_to("celery")
    await rec.snap(0.7)
    await rec.press("k", seconds=2.2)
    await rec.press("enter", seconds=1.3)
    rec.clear_toasts()

    # 4. Git: el estado en lenguaje humano y el mapa con el remoto.
    await rec.press("tab", seconds=2.2, still="git-status")
    await rec.press("shift+tab")

    # 5. Commit: lista de archivos y aviso del .env.
    await rec.press("c", seconds=2.0)
    await rec.type(COMMIT_MESSAGE[lang])
    await rec.snap(1.5, still="commit")
    await rec.press("enter", seconds=1.5)
    rec.clear_toasts()

    # 6. Push: vista previa con el comando exacto, y el mapa queda al día.
    await rec.press("p", seconds=1.9)
    await rec.press("enter", seconds=1.5)
    rec.clear_toasts()

    # 7. Ramas.
    await rec.press("b", seconds=2.6)
    await rec.press("escape")

    # 8. Historial como gráfico de ramas.
    await rec.press("h", seconds=3.5, still="history")


async def record(lang: str) -> Recorder:
    i18n.set_language(lang)
    # Una carpeta personal de ejemplo, con el aspecto del sistema donde se graba.
    home = Path("C:/Users/ana") if sys.platform == "win32" else Path("/home/ana")
    world = DemoWorld(delay=0, home=home)
    app = QcorreApp(**world.as_kwargs(), refresh_seconds=None)
    async with app.run_test(size=SIZE, notifications=True) as pilot:
        rec = Recorder(app, pilot)
        await rec.settle()
        await storyboard(rec, lang)
    return rec


# ── De SVG a PNG ────────────────────────────────────────────────


def find_browser() -> str:
    for candidate in BROWSERS:
        found = shutil.which(candidate) or (candidate if Path(candidate).is_file() else None)
        if found:
            return found
    raise SystemExit("No encontré Edge ni Chrome: hace falta un navegador Chromium.")


def svg_size(svg: str) -> tuple[int, int]:
    match = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    if not match:
        raise ValueError("el SVG no tiene viewBox")
    return round(float(match.group(1))), round(float(match.group(2)))


def render_png(browser: str, svg: str, target: Path, workdir: Path, slot: int) -> None:
    """Convierte un SVG en PNG con el navegador en modo headless."""
    width, height = svg_size(svg)
    sized = svg.replace("<svg ", f'<svg width="{width}" height="{height}" ', 1)
    page = workdir / f"{target.stem}.html"
    page.write_text(
        "<!doctype html><meta charset='utf-8'>"
        f"<body style='margin:0;overflow:hidden;background:{FRAME_BACKGROUND}'>{sized}</body>",
        encoding="utf-8",
    )
    subprocess.run(
        [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
            "--virtual-time-budget=4000",  # da tiempo a que cargue la tipografía
            f"--user-data-dir={workdir / f'perfil-{slot}'}",
            f"--window-size={width},{height}",
            f"--screenshot={target}",
            page.as_uri(),
        ],
        capture_output=True,
        timeout=120,
        check=False,
    )
    if not target.is_file():
        raise RuntimeError(f"el navegador no generó {target.name}")


def render_all(svgs: dict[str, str], workdir: Path) -> dict[str, Path]:
    """Convierte todos los SVG distintos (por huella) en PNG, en paralelo."""
    browser = find_browser()
    targets = {digest: workdir / f"{digest}.png" for digest in svgs}
    workers = 4

    def job(item: tuple[int, tuple[str, str]]) -> None:
        index, (digest, svg) = item
        render_png(browser, svg, targets[digest], workdir, slot=index % workers)

    # Los SVG se reparten en tantas filas como hilos, y cada fila usa su propio
    # perfil del navegador: así nunca hay dos procesos sobre el mismo perfil.
    items = list(enumerate(svgs.items()))
    lanes = [items[offset::workers] for offset in range(workers)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(lambda lane: [job(item) for item in lane], lanes))
    return targets


def digest_of(svg: str) -> str:
    return hashlib.sha1(svg.encode("utf-8")).hexdigest()[:16]


# ── De PNG a GIF ────────────────────────────────────────────────


def build_gif(frames: list[tuple[Path, float]], output: Path) -> None:
    from PIL import Image

    images = [Image.open(path).convert("RGB") for path, _ in frames]
    # Una paleta común para todos los fotogramas: sin ella los colores
    # "bailan" de un fotograma a otro y el archivo pesa más.
    # La paleta se calcula sobre los colores *distintos* que aparecen, cada uno
    # una sola vez: si se pesaran por superficie, el fondo oscuro lo dominaría
    # todo y los colores de estado (verde, rojo, rosa) se perderían.
    distinct: set[tuple[int, int, int]] = set()
    for image in images:
        distinct.update(color for _, color in image.getcolors(maxcolors=2**24))
    swatch = Image.new("RGB", (len(distinct), 1))
    swatch.putdata(sorted(distinct))
    palette = swatch.quantize(colors=COLORS, method=Image.Quantize.MEDIANCUT)

    indexed = [image.quantize(palette=palette, dither=Image.Dither.NONE) for image in images]
    output.parent.mkdir(parents=True, exist_ok=True)
    indexed[0].save(
        output,
        save_all=True,
        append_images=indexed[1:],
        duration=[round(seconds * 1000) for _, seconds in frames],
        loop=0,
        optimize=True,
        disposal=1,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lang", choices=i18n.LANGUAGES, default="en")
    parser.add_argument("--out", type=Path, default=Path("docs"))
    args = parser.parse_args()
    suffix = "" if args.lang == "en" else f".{args.lang}"

    rec = asyncio.run(record(args.lang))
    svgs = {digest_of(frame.svg): frame.svg for frame in rec.frames}
    svgs.update({digest_of(svg): svg for svg in rec.stills.values()})

    with tempfile.TemporaryDirectory(prefix="qcorre-demo-") as tmp:
        pngs = render_all(svgs, Path(tmp))

        # Fotogramas iguales y seguidos se funden en uno que dura la suma.
        merged: list[tuple[Path, float]] = []
        for frame in rec.frames:
            path = pngs[digest_of(frame.svg)]
            if merged and merged[-1][0] == path:
                merged[-1] = (path, merged[-1][1] + frame.seconds)
            else:
                merged.append((path, frame.seconds))

        gif = args.out / f"demo{suffix}.gif"
        build_gif(merged, gif)
        shots = args.out / "screenshots"
        shots.mkdir(parents=True, exist_ok=True)
        for name, svg in rec.stills.items():
            shutil.copyfile(pngs[digest_of(svg)], shots / f"{name}{suffix}.png")

    total = sum(seconds for _, seconds in merged)
    size_mb = gif.stat().st_size / 1_000_000
    print(f"{gif}: {len(merged)} fotogramas, {total:.1f} s, {size_mb:.2f} MB")
    for name in rec.stills:
        path = shots / f"{name}{suffix}.png"
        print(f"{path}: {path.stat().st_size / 1000:.0f} kB")


if __name__ == "__main__":
    main()
