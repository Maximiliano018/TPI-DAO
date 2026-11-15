"""Persistencia: patrones **Repository**, **Data Mapper** y **Unit of Work**.

* ``interfaces/``: los puertos (``Protocol``) que usan los servicios, sin SQL.
* ``impl/``: las implementaciones con SQLAlchemy, que mapean ORM ↔ dominio y aplican el bloqueo
  pesimista (``FOR UPDATE``) y optimista (``version``).
* ``unit_of_work.py``: una transacción por caso de uso.

Ver ``docs/tecnica/05-patrones-de-diseno.md``, secciones 5 a 7.
"""
