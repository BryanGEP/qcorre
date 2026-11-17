# Cambios

Todos los cambios notables de qcorre se anotan aquí. El formato sigue
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y las versiones,
[SemVer](https://semver.org/lang/es/).

## [0.1.0] - sin publicar

Primera versión.

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
