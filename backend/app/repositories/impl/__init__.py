"""Repositorios sobre SQLAlchemy: patrones **Repository** y **Data Mapper**.

Cada repositorio implementa su interfaz de ``interfaces/`` y convierte entre el modelo del ORM
(``app/db/models``) y la entidad de dominio (funciones ``_<entidad>_a_dominio``); nunca expone
objetos del ORM a los servicios.

Concurrencia (ver ``docs/tecnica/05-patrones-de-diseno.md``, sección 7):

* **Bloqueo pesimista:** ``obtener_para_modificar`` lee con ``SELECT … FOR UPDATE``; la sede que
  se usa como origen, destino o retiro se bloquea con ``FOR SHARE`` (``obtener_para_operar``) y
  el ejemplar de la autogestión con ``FOR UPDATE SKIP LOCKED``.
* **Bloqueo optimista:** sede, libro y ejemplar comparan la columna ``version`` al modificarse.
"""
