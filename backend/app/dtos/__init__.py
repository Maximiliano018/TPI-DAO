"""Patrón **DTO** (Data Transfer Object): el contrato de la API, separado del dominio.

* ``request/``: valida con Pydantic la forma de cada solicitud.
* ``response/``: arma la respuesta desde la entidad eligiendo el **esquema según el rol** de quien
  consulta (por ejemplo, ``MultaPersonalResponse | MultaPropiaResponse``), así nada sale por la API
  sin decidirlo. Ver ``docs/tecnica/05-patrones-de-diseno.md``, sección 11.
"""
