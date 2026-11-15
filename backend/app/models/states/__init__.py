"""Patrón **State**: un estado por clase para remito, préstamo, ejemplar y reserva.

Cada estado implementa solo las operaciones que admite y devuelve el estado siguiente; la clase
base rechaza el resto con ``TransicionInvalida``. La entidad (el contexto) delega en su estado y
registra el movimiento en su historial. Ver ``docs/tecnica/05-patrones-de-diseno.md``, sección 1.
"""
