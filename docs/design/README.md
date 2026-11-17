# Diseño visual de qcorre

Decisión tomada el 2026-11-17 a partir de una auditoría de la interfaz de la
v0.1.0. Este documento guarda el porqué; las capturas y los mockups están en
esta misma carpeta (no forman parte del paquete).

## Auditoría (resumen)

Capturas de la v0.1.0 en [`auditoria/`](auditoria/).

- **Color:** el gris tenue (tiempos, pie, metadatos) tenía 4.0–4.2:1 de
  contraste, por debajo del mínimo AA (4.5:1). El ámbar se usaba para iconos,
  notas y grupos a la vez, así que el aviso dejaba de destacar.
- **Espacio:** a 160×45 más de la mitad de la pantalla quedaba vacía; puertos y
  tiempos alineados a la izquierda no formaban columna.
- **Consistencia:** tres estilos distintos para los encabezados de sección y
  otros tres para las teclas en los diálogos; glifos de ancho ambiguo (`⚠`,
  `⎇`) que en algunas terminales se dibujan como emoji y desalinean.
- **Densidad:** el pie ocupaba 3 de 30 filas mostrando los 17 atajos siempre,
  sin importar dónde estaba el foco.
- **Estados vacíos y de error:** sin llamada a la acción; el error de git
  mostraba el mensaje crudo sin sugerencia.
- **Fondo claro:** sin tema claro; qcorre se ve como un bloque oscuro.

## Direcciones evaluadas

| Mockup | Dirección | Idea |
|---|---|---|
| [`A-sereno.png`](mockups/A-sereno.png) | A · Sereno | Minimalista: sin cajas, un solo acento, color solo en el estado |
| [`B-tablero.png`](mockups/B-tablero.png) | B · Tablero | Denso tipo btop/k9s: tabla con CPU y memoria, paneles numerados |
| [`C-amigable-oscuro.png`](mockups/C-amigable-oscuro.png), [`C-amigable-claro.png`](mockups/C-amigable-claro.png) | C · Amigable | Tarjetas, píldoras y teclas dibujadas; tema oscuro y claro |

## Decisión

**Base: dirección C**, con ajustes tomados de A y B.

- **De C:** paleta oscura y tema claro, mapa de cajas tu compu ↔ remoto, pie con
  teclas dibujadas, chips de resumen en la cabecera y números destacados en las
  frases.
- **De A:** las notas de huérfano y "sin permiso" van en gris tenue, sin fondo
  (el aviso lo dan el color del punto y el chip de la cabecera); "Últimos
  commits" bajo el mapa en la vista Estado, para usar el espacio vacío; pie
  contextual.
- **De B:** salto a paneles con `1` y `2`, y columnas alineadas a la derecha.
  Sin CPU ni memoria por ahora.
- **Corrección sobre el mockup C:** en las filas sin puerto (p. ej. `celery`) no
  debe aparecer el bloque de color de la píldora vacía.

## Plan

1. **`design/mejoras-base`:** contraste del gris tenue, pie contextual de una
   línea, color solo para estado (notas en gris), columnas alineadas a la
   derecha y selección a todo lo ancho, sin glifos ambiguos, un solo estilo de
   encabezados y teclas en los diálogos, panel de git sin redundancias, estados
   vacíos y de error con acción, notas más cortas, y salto a paneles con `1` y
   `2`.
2. **`design/tema-amigable`:** el tema nuevo oscuro y claro (`--theme` y una
   tecla para cambiarlo), el pie con teclas dibujadas, los chips de la cabecera
   y "Últimos commits" bajo el mapa.
