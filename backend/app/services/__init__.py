"""Capa de servicios de aplicación: patrón **Service Layer** (una fachada por módulo).

Cada servicio ofrece un método por caso de uso: controla el permiso, abre la transacción (Unit of
Work), obtiene y bloquea las entidades, delega las reglas en el dominio y guarda. Los controllers
solo traducen HTTP ↔ DTO. ``ColaDeReservas`` y ``reevaluar_socio`` son servicios de dominio que
comparten varios casos de uso. Las dependencias se reciben por constructor (**inyección de
dependencias**, ver ``app/controllers/dependencies.py``).
Ver ``docs/tecnica/05-patrones-de-diseno.md``, secciones 8 y 9.
"""
