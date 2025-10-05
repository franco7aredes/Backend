# Capa 2 — Lógica de Negocio (Servicios)

Este módulo concentra las reglas de negocio del juego y expone casos de uso a través del servicio `ServicioJuego`. La capa no conoce detalles de FastAPI ni de SQLAlchemy; se comunica mediante interfaces de repositorio (capa 1) e inyección de dependencias a través de la fábrica.

## Componentes

- `servicio_juego.py`: Implementa los casos de uso del dominio.
- `errores.py`: Excepciones de dominio para mapear a códigos HTTP en la capa API.
- `fabrica.py`: Composition root para construir el servicio con repositorios concretos (SQLAlchemy async) y proveerlo como dependencia de FastAPI.

## Casos de uso (contratos)

Entradas y salidas principales. Todos los métodos son `async` y retornan modelos ORM o estructuras simples.

- `crear_partida(jugador_creador: str, fecha_nac: datetime, minimo: int, maximo: int) -> (Partida, Jugador)`
  - Inicializa la partida en "En espera", crea el jugador creador y actualiza `id_jugador_creador`.
- `listar_en_espera() -> list[Partida]`
  - Devuelve partidas en estado "En espera".
- `obtener_por_id(partida_id: int) -> Partida | None`
- `iniciar_partida(partida_id: int) -> Partida`
  - Valida mínimo de jugadores y que no esté ya en juego.
- `repartir_cartas(partida_id: int, num_cartas: int) -> dict`
  - Construye mazo (1..61), reparte `num_cartas` por jugador y persiste.
  - Devuelve `{ repartidas: dict[jugador_id, list[Carta]], mazo: list[Carta] }`.
- `asignar_turnos(partida_id: int, fecha_referencia: date = 1980-09-15) -> list[Jugador]`
  - Ordena jugadores por proximidad de fecha y actualiza `orden_turno`.
- `listar_jugadores(partida_id: int) -> list[Jugador]`
- `unirse_a_partida(partida_id: int, nombre: str, fecha_nacimiento: datetime, id_avatar: int | None) -> (Partida, Jugador)`
  - Valida máximo de jugadores y crea el jugador.
- `terminar_turno(partida_id: int, id_enviada: int) -> int`
  - Valida que sea el turno del jugador y avanza el turno. Retorna `turno_actual`.
- `reponer_del_mazo(partida_id: int, jugador_id: int, max_cartas_en_mano: int = 6) -> dict`
  - Mueve cartas del mazo a la mano hasta completar `max_cartas_en_mano`.
  - Flags en la respuesta: `max_alcanzado`, `sin_cartas`, `fin_de_mazo` y `cartas`.
  - Si el mazo está vacío o queda en cero, marca la partida como `Finalizada` y hace `commit` inmediato.
- `descartar_carta(partida_id: int, jugador_id: int) -> int | None`
  - Mueve una carta de mano a descarte y retorna su id (o `None` si no hay cartas).

## Excepciones de dominio

- `PartidaNoEncontrada`
- `PartidaYaEnJuego`
- `MinimoJugadoresNoAlcanzado`

La capa API (routers) debe capturarlas y traducirlas a HTTP 404/400 según corresponda.

## Transaccionalidad

- La sesión async (`AsyncSession`) se maneja en la capa 0 (dependencia `get_async_db`).
- Los repos (capa 1) comparten la misma sesión.
- Este servicio generalmente realiza `flush`/`refresh` a través de los repos, y delega el `commit` a la dependencia por request.
- Casos especiales como `reponer_del_mazo` cuando se necesita persistir `Finalizada` antes de retornar un 404: se hace `commit` inmediato para garantizar consistencia observada por los tests y el frontend.

## Integración con la API (capa 3)

- La fábrica (`fabrica.obtener_servicio_juego`) inyecta repos SQLAlchemy async al `ServicioJuego`.
- Los routers usan el servicio para orquestar la lógica y se encargan de:
  - Mapear excepciones de dominio a HTTP.
  - Notificar por WebSockets (`manager`) a jugadores o salas (mensajes texto y JSON).
  - Mantener contratos de respuesta esperados por el frontend y tests.

## Notas de diseño

- La capa 2 no importa FastAPI ni detalles de WebSockets.
- Las entidades que retorna son modelos ORM o estructuras simples (dict/list) fáciles de mapear a DTOs.
- Para DTOs, se unificó en `capa_3_api/dtos/partidas.py`, y `app/schemas/partidas.py` re-exporta esos modelos para mantener compatibilidad.
