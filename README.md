# qcorre

**¿Qué corre en tu compu?** Un panel del desarrollador para la terminal.

- **Procesos por proyecto:** detecta tus servidores y bases de datos, sus
  puertos, y los agrupa según el repo git al que pertenecen. Marca los
  huérfanos y te deja matarlos (con confirmación).
- **Git en lenguaje humano:** estado explicado, mapa tu compu ↔ remoto, vista
  previa con el comando exacto antes de cada acción y respaldo automático
  antes de las operaciones riesgosas.

> En desarrollo: todavía no hay una versión publicada.

## Desarrollo

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"

qcorre            # abre la interfaz; el proyecto de la carpeta actual siempre se muestra
qcorre ../otro    # igual, pero fijando otro proyecto
qcorre --lang en  # fuerza el idioma (es / en)
pytest            # corre los tests
```

## Licencia

MIT
