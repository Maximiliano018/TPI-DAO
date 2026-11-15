"""Modelo de dominio: entidades, objetos de valor y reglas de negocio, sin persistencia ni HTTP.

Patrones que viven acá (detalle en ``docs/tecnica/05-patrones-de-diseno.md``):

* **State** (``states/``): ciclo de vida de remito, préstamo, ejemplar y reserva.
* **Strategy** (``policies/``): plazo de préstamo, multa por atraso y por daño o extravío, y la
  verificación de baja de sede (con **Composite**).
* **Factory** (``factories/``) y constructores con nombre (``Pago.manual``, ``Sede.crear``…).
* **Value Object** (``valores.py``, ``horario.py``, ``UsuarioRef``): datos inmutables que se
  validan al construirse.
"""
