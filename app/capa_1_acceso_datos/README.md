# Capa 1 — Acceso a Datos (Repositorios)

Implementaciones concretas de repositorios usando SQLAlchemy async. No hay interfaces/contratos abstractos; la capa 2 (servicio) usa duck typing sobre los métodos públicos de estos repos.

## Repositorios disponibles

- `partida_sqlalchemy.py`: CRUD y consultas de Partida.
- `jugador_sqlalchemy.py`: CRUD y listados de Jugador.
- `carta_sqlalchemy.py`: operaciones de Carta (crear_muchas, contar, obtener, guardar).

## Sesión y transacciones

- Las implementaciones usan una `AsyncSession` inyectada (ver fábrica en capa 2).
- Se usa `flush()` y `refresh()` para obtener IDs y reflejar cambios.
- El `commit` por request lo maneja `get_async_db` (capa 0). Casos especiales pueden forzar `commit`/`rollback` desde el servicio vía métodos del repo (por ej. `confirmar`).

## Uso desde la capa 2 (Servicios)

La fábrica (`capa_2_logica/fabrica.py`) compone el servicio inyectando repositorios con la sesión async actual.

