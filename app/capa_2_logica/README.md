# Capa 2 — Lógica de Negocio (Servicios)

Este módulo concentra las reglas de negocio del juego y expone casos de uso a través del servicio `ServicioJuego`. La capa no conoce detalles de FastAPI; se comunica con la capa 1 mediante repositorios concretos de SQLAlchemy inyectados por la fábrica (duck typing/Protocol para mantener bajo acoplamiento).

## Componentes

- `servicio_juego.py`: Implementa los casos de uso del dominio.
- `errores.py`: Excepciones de dominio para mapear a códigos HTTP en la capa API.
- `fabrica.py`: Composition root para construir el servicio con repositorios concretos (SQLAlchemy async) y proveerlo como dependencia de FastAPI.
- `resultados.py`: Dataclasses de resultados para comandos.
- `convertidores.py`: Helpers para transformar objetos ORM a diccionarios (usados en consultas para no exponer la ORM hacia capa 3).

## Casos de uso (contratos)

Entradas y salidas principales. Todos los métodos son `async`. Usamos un criterio CQS:

- Comandos (modifican estado) devuelven dataclasses de resultados (en `resultados.py`).
- Consultas (solo lectura) devuelven diccionarios (neutros, sin acoplamiento a ORM).

- `crear_partida(jugador_creador: str, fecha_nac: datetime, minimo: int, maximo: int) -> CrearPartidaResultado`
  - Inicializa la partida en "En espera", crea el jugador creador y actualiza `id_jugador_creador`.
- `listar_en_espera() -> list[dict]`
  - Devuelve partidas en estado "En espera" como dicts.
- `obtener_por_id(partida_id: int) -> dict | None`
- `iniciar_partida(partida_id: int) -> IniciarPartidaResultado`
  - Valida mínimo de jugadores y que no esté ya en juego.
- `repartir_cartas(partida_id: int, num_cartas: int) -> RepartirCartasResultado`
  - Construye mazo (1..61), reparte `num_cartas` por jugador y persiste.
- `asignar_turnos(partida_id: int, fecha_referencia: date = 1980-09-15) -> list[dict] | list[Jugador]`
  - Nota: si se requiere exponer a capa 3, preferir dicts; si se usa internamente en capa 2, puede trabajar con ORM.
  - Ordena jugadores por proximidad de fecha y actualiza `orden_turno`.
- `listar_jugadores(partida_id: int) -> list[dict]`
- `unirse_a_partida(partida_id: int, nombre: str, fecha_nacimiento: datetime, id_avatar: int | None) -> UnirsePartidaResultado`
  - Valida máximo de jugadores y crea el jugador.
- `terminar_turno(partida_id: int, id_enviada: int) -> TurnoResultado`
  - Valida que sea el turno del jugador y avanza el turno. Retorna el nuevo turno.
- `reponer_del_mazo(partida_id: int, jugador_id: int, max_cartas_en_mano: int = 6) -> ReponerResultado`
  - Mueve cartas del mazo a la mano hasta completar `max_cartas_en_mano`.
  - Incluye flags: `max_alcanzado`, `sin_cartas`, `fin_de_mazo` y `cartas`.
  - Si el mazo está vacío o queda en cero, marca la partida como `Finalizada` y puede `confirmar` (commit) inmediato vía repo.
- `descartar_carta(partida_id: int, jugador_id: int) -> DescartarResultado`
  - Mueve una carta de mano a descarte y retorna `carta_id` (o `None` si no hay cartas para descartar).

- `iniciar_y_preparar_partida(partida_id: int, cartas_por_mano: int) -> IniciarYPrepararResultado`
  - Orquesta: iniciar, repartir cartas y asignar turnos. Devuelve `partida`, `repartidas`, `mazo`, `jugadores`.

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

  - Mapear excepciones de dominio a HTTP.
  - Notificar por WebSockets (administrador de conexiones) a jugadores o salas (mensajes texto y JSON).

## Notas de diseño

- La capa 2 no importa FastAPI ni detalles de WebSockets.
- Las entidades que retorna son modelos ORM o estructuras simples (dict/list) fáciles de mapear a DTOs.
- Para DTOs, se unificó en `capa_3_api/dtos/partidas.py`.
