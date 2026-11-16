"""Lógica de git, usando el git del sistema.

- ``runner``: único punto que ejecuta ``git`` (y sabe mostrar el comando exacto).
- ``parse``: convierte la salida de git en modelos. Funciones puras.
- ``status``: lee el estado completo de un repo.
- ``explain``: traduce ese estado a frases en lenguaje humano.
"""
