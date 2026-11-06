# database

Todo lo relacionado con PostgreSQL 16 que no es código de la aplicación.

| Carpeta | Contenido |
|---------|-----------|
| `init/` | Scripts SQL que Docker ejecuta al crear la base por primera vez (extensiones, roles). |
| `seeds/` | Datos de demostración (sedes, usuarios, libros, ejemplares). Se completa con la implementación del esquema. |

El esquema (tablas, restricciones e índices) lo versiona **Alembic** en `backend/alembic/`, según [docs/tecnica/04-modelo-de-datos.md](../docs/tecnica/04-modelo-de-datos.md).

## Levantar la base

```bash
cp .env.example .env        # y definir POSTGRES_PASSWORD
docker compose up -d db
docker compose ps           # esperar estado "healthy"
```

Conexión: `localhost:5432` (o `POSTGRES_PORT`), base `tpi_dao`, usuario `tpi_dao`.

```bash
docker compose exec db psql -U tpi_dao -d tpi_dao   # consola SQL
docker compose down                                  # apagar conservando los datos
docker compose down -v                               # apagar y borrar los datos
```
