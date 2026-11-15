"""Patrón **Repository**: interfaces de acceso a datos que conoce la capa de servicios.

Cada interfaz es un ``Protocol`` con las operaciones que el dominio necesita (``obtener``,
``obtener_para_modificar``, ``agregar``, ``guardar``, consultas propias). Las implementan los
repositorios de SQLAlchemy (``impl/``) y los repositorios en memoria de las pruebas
(``tests/fakes/``). Ver ``docs/tecnica/05-patrones-de-diseno.md``, sección 5.
"""
