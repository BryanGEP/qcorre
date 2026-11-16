"""Recolección de datos del sistema con psutil.

Es la única capa que toca psutil. Entrega ``ProcessInfo`` planos para que la
lógica de ``qcorre.projects`` se pueda testear sin procesos reales.
"""
