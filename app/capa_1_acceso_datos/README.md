# Capa 1 — Acceso a Datos (Repositorios)

Abstracciones y adaptadores de persistencia. Define contratos (interfaces) y sus implementaciones en SQLAlchemy async.

## Estructura

- `repositorios/*_contrato.py`: contratos que exponen operaciones del agregado (Partida, Jugador, Carta).
- `repositorios/*_sqlalchemy.py`: implementaciones concretas con `AsyncSession`.

## Contratos

- `IRepositorioPartida`
  - `crear(partida)` -> Partida
  - `obtener(partida_id)` -> Partida | None
  - `listar_en_espera()` -> list[Partida]
  - `guardar(partida)` -> None
- `IRepositorioJugador`
  - `listar_por_partida(partida_id)` -> list[Jugador]
  - `crear(jugador)` -> Jugador
  - `obtener(jugador_id)` -> Jugador | None
- `IRepositorioCarta`
  - `crear_muchas(cartas)` -> None
  - `contar_en_mano(partida_id, jugador_id)` -> int
  - `obtener_mazo_disponible(partida_id, limite)` -> list[Carta]

## Sesión y transacciones

- Las implementaciones usan una `AsyncSession` inyectada (ver fábrica en capa 2).
- Se usa `flush()` y `refresh()` para obtener IDs y reflejar cambios.
- El `commit` por request lo maneja `get_async_db` (capa 0). Casos especiales pueden forzar `commit` inmediato desde el servicio.

## Uso desde la capa 2 (Servicios)

La fábrica (`capa_2_logica/fabrica.py`) compone el servicio inyectando repositorios con la sesión async actual.

