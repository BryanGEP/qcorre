# Cambios

Todos los cambios notables de qcorre se anotan aquí. El formato sigue
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y las versiones,
[SemVer](https://semver.org/lang/es/).

## [Sin publicar]

### Añadido

- Tema nuevo, oscuro y claro: se elige con `--theme dark|light` (o la variable
  `QCORRE_THEME`) y se cambia en caliente con `t`. Todos los textos cumplen el
  contraste AA en los dos.
- Cabecera con chips de resumen: proyectos, procesos, huérfanos (solo si hay) e
  idioma.
- Pie con las teclas dibujadas.
- "Últimos commits" bajo el mapa, en la vista Estado del panel de git.
- Los números de las frases de git van destacados con el color de lo que cuentan.

### Cambiado

- Mejor contraste: el gris de los textos secundarios cumple el mínimo AA (4.5:1).
- El pie ocupa una sola línea y muestra solo los atajos que sirven en ese
  momento, según el panel activo y lo seleccionado.
- `1` y `2` saltan al panel de proyectos y al de git.
- Panel de proyectos: puertos, tiempos y conteos alineados a la derecha, la
  selección ocupa toda la fila y las notas de huérfano van en gris (el aviso lo
  da el color del punto). Notas más cortas.
- Sin glifos que algunas terminales dibujan como emoji (`⚠`).
- Los diálogos usan un solo estilo para los encabezados y las teclas.
- El panel de git ya no repite la rama, que está en su borde.
- Los estados vacíos y los errores de git sugieren qué hacer.
- El panel de git se repinta cuando cambia su ancho real, así que el mapa y
  las listas ya no se parten al aparecer la barra de desplazamiento.

## [0.1.0] - 2026-11-17

Primera versión publicada en PyPI: `pipx install qcorre` o `uvx qcorre`.

### Procesos

- Panel de proyectos: procesos de desarrollo con sus puertos y tiempo corriendo,
  agrupados por el repo git o la carpeta de proyecto desde donde corren.
- Un servidor y sus procesos hijos se muestran como una sola fila, incluidos los
  lanzadores (`npm run dev → vite`).
- Huérfanos marcados con su razón: sin proyecto, mucho tiempo corriendo o con el
  proceso padre ya cerrado. El umbral se ajusta con `--orphan-hours`.
- Procesos que el sistema no deja leer se muestran como "sin permiso".
- Matar un proceso o todos los de un proyecto, con confirmación que lista cada
  proceso afectado. Aviso especial al matar una base de datos.
- Detalle de un proceso: comando completo, carpeta, PID, padre y hora de inicio.

### Git

- Estado del repo en lenguaje humano y mapa tu compu ↔ remoto.
- Acciones con vista previa y comando exacto: commit, push, pull y actualizar
  del remoto.
- El commit lista los archivos que entran y avisa de los que parecen contener
  secretos.
- Ramas: locales, solo remotas y con la rama remota borrada; cambiar, crear y
  borrar ramas ya mergeadas.
- Deshacer el último commit, descartar cambios y volver a un respaldo.
- Respaldos automáticos en `refs/qcorre/backup/` antes de las acciones riesgosas.
- Historial como gráfico de ramas con colores.

### General

- Interfaz en español e inglés, con detección del idioma del sistema.
- Modo `--demo` con procesos y repos simulados.
- Pantalla de ayuda (`?`).
- El pie de atajos se reparte en más renglones cuando la terminal es angosta.
- README en inglés (principal) y español, con GIF de demostración y capturas.

[0.1.0]: https://github.com/BryanGEP/qcorre/releases/tag/v0.1.0
