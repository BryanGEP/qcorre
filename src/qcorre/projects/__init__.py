"""Lógica pura para decidir a qué proyecto pertenece cada proceso.

No depende de psutil ni de la interfaz: recibe ``ProcessInfo`` y devuelve un
``Snapshot`` con los procesos agrupados.
"""
