"""qcorre: panel del desarrollador en la terminal.

El paquete está dividido en capas para poder testear la lógica sin la interfaz:

- ``collectors`` / ``projects``: recolección de procesos y agrupación por proyecto.
- ``git``: lógica de git mediante el git del sistema.
- ``ui``: interfaz con Textual (solo presentación).
"""

__version__ = "0.1.0"
