# Capa 3 — API (Routers y DTOs)

Punto de entrada HTTP/WebSockets. Contiene los routers de FastAPI y los DTOs (esquemas) de entrada/salida.

## Componentes

- `dtos/partidas.py`: DTOs de dominio (Jugador, JugadorCrear, Partida, PartidaCrear). Son la fuente de verdad.
- `routers/partidas.py`: Endpoints REST relacionados a partidas, jugadores y turnos.
- `routers/mazo.py`: Endpoints para reponer cartas, descartar y consultar mano.
- `mapeadores.py`: funciones que mapean dicts de la capa 2 a DTOs de capa 3. La API no importa modelos ORM.
- `websockets/ApiWS.py`: Administrador de conexiones para enviar mensajes a jugadores/salas (texto y JSON).

## Inyección de dependencias

Los routers reciben un `ServicioJuego` mediante `Depends(obtener_servicio_juego)`, que conecta con los repos (capa 1) y la sesión async (capa 0).

## Mapeo de errores

Las excepciones de dominio de la capa 2 se traducen a HTTP:

- `PartidaNoEncontrada` → 404
- `MinimoJugadoresNoAlcanzado` → 400
- `PartidaYaEnJuego` → 400
- Otras validaciones (jugador inválido, fuera de turno, etc.) → 400/404 según caso

## Notificaciones por WebSocket

- Se notifica a canales individuales (por id de jugador) y/o a la sala de una partida.
- Eventos típicos:
  - `nueva_partida` (difusión global)
  - `partida_iniciada` (difusión a sala)
  - `jugadores_actualizados` y `jugador_unido` (privados + sala)
  - `fin_de_mazo` (privado en texto plano y JSON; también a sala)

## Endpoints clave

- `POST /partidas` → crea partida + jugador creador.
- `GET /partidas` → lista partidas en espera.
- `GET /partidas/{id}` → obtiene una partida.
- `GET /partidas/{id}/jugadores` → lista jugadores de la partida.
- `PUT /partidas/{id}/unirse` → se une un jugador a la partida.
- `PATCH /partidas/{id}/iniciar` → valida y pasa a "En Juego", reparte cartas, asigna turnos, y notifica.
- `PATCH /partidas/{id}/terminar_turno` → avanza el turno si corresponde y notifica a los jugadores.
- `PUT /partida/{id}/reponer` → repone cartas hasta 6; si el mazo queda vacío o está vacío, se notifica `fin_de_mazo` y la partida queda `Finalizada`.
- `PATCH /partida/{id}/descartar` → descarta una carta de la mano del jugador.

## Contratos de DTOs

Los DTOs se definen en `dtos/partidas.py` y se usan directamente desde los routers. 

## Notas de diseño

- Los routers contienen orquestación mínima: delegan la lógica al servicio y se ocupan del mapeo HTTP y WS.
- Se preservan los contratos de respuesta que consumen el frontend y que validan los tests.
- Capa 3 consume dicts de consultas desde capa 2 y dataclasses simples en comandos; se mapean a DTOs/payloads sin exponer ORM.

## Patrón de endpoints “bonitos”

- try/except en capa 3 para traducir errores de dominio a HTTP (404/400) y disparar notificaciones WS mínimas.
- La lógica y orquestación quedan en el servicio (capa 2). Ejemplo: para iniciar una partida se usa
  `ServicioJuego.iniciar_y_preparar_partida(partida_id, cartas_por_mano)` que internamente:
  1) valida e inicia, 2) reparte cartas, 3) asigna turnos. El router solo devuelve
  `{mensaje, estado}` y notifica `partida_iniciada`.
