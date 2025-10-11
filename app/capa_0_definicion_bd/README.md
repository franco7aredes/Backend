# Capa 0 — Definición de Base de Datos (Infra)

Infraestructura de SQLAlchemy asíncrona compartida por todo el backend.

## Componentes

- `base_datos_sqlalchemy.py`
  - `Base`: clase base declarativa para todos los modelos ORM.
  - `async_engine`: motor async creado con la URL de `settings.DATABASE_URL_ASYNC`.
  - `AsyncSessionLocal`: fábrica de sesiones `AsyncSession`.
  - `get_async_db()`: dependencia para FastAPI que libera una sesión por request y maneja `commit/rollback`.

## Ciclo de vida de la sesión

- `get_async_db` hace `commit` si el request se procesa con éxito, y `rollback` si ocurre una excepción.
- Las capas superiores (repos y servicios) realizan `flush`/`refresh` cuando lo necesitan; el `commit` por defecto lo maneja esta capa.

## Modelos ORM

Los modelos viven en `app/db/models/*` y deben heredar de la `Base` compartida para que el esquema sea consistente.

## Notas

- Esta capa no importa FastAPI ni routers.
- La URL de base de datos y otras opciones se encuentran en `app/settings.py`.
- En `app/db/models/cartas_modelos` al declarar el Tipo, disgregamos la lógica de mantener el Backend en español, escribiendo esto en inglés, para mantenernos consistentes luego con el Frontend y las propias imágenes de las cartas; de semejante manera, esto sucede con los nombres de las mismas.