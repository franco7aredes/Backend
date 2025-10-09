# Backend — Arquitectura por capas (async)

Este backend está implementado en FastAPI usando SQLAlchemy async y una arquitectura por capas inspirada en “código bonito”.

## Capas

- Capa 0: Definición de BD y sesión async (`app/capa_0_definicion_bd`)
	- `base_datos_sqlalchemy.py`: `AsyncEngine` y `AsyncSession` (aiosqlite).
	- `models/`: modelos SQLAlchemy (Partida, Jugador, Carta).
- Capa 1: Acceso a datos (`app/capa_1_acceso_datos`)
	- Repositorios SQLAlchemy para partida, jugador y carta.
- Capa 2: Lógica de negocio (`app/capa_2_logica`)
		- `servicio_juego.py`: casos de uso y orquestación (por ejemplo `iniciar_y_preparar_partida`).
			- Comandos devuelven dataclasses de resultado (ver `resultados.py`).
			- Consultas devuelven diccionarios (no se expone la ORM hacia la capa 3).
	- `fabrica.py`: inyección de dependencias.
	- `errores.py`: excepciones de dominio (mapeadas a HTTP en capa 3).
	- `resultados.py`: dataclasses de retorno de comandos (CrearPartidaResultado, IniciarPartidaResultado, RepartirCartasResultado, etc.).
		- `convertidores.py`: helpers para convertir ORM→dict en la capa 2.
- Capa 3: API (routers, DTOs, websockets) (`app/capa_3_api`)
	- `dtos/`: DTOs de entrada/salida de endpoints.
	- `routers/`: endpoints finos (“bonitos”), usan try/except, delegan al servicio y devuelven lo mínimo.
	- `mapeadores.py`: mapea dicts (provenientes de la capa 2) → DTOs. La capa 3 no importa modelos de la ORM.
	- `websockets/ApiWS.py`: administrador de conexiones para notificaciones a jugadores/salas.

## Patrón de endpoints “bonitos”

- En capa 3, los routers solo:
	- Hacen `try/except` y traducen errores de dominio a HTTP (404/400).
	- Delegan toda la lógica/orquestación a `ServicioJuego` (capa 2).
	- Disparan notificaciones WS mínimas y devuelven un payload simple esperado por el frontend/tests.
- Ejemplo: `PATCH /partidas/{id}/iniciar` llama a `ServicioJuego.iniciar_y_preparar_partida(...)` (que usa dataclasses de resultado) y responde `{mensaje, estado}`.

## Requisitos y ejecución

### 1) Crear y activar entorno
```
python -m venv .venv
source .venv/bin/activate
```

### 2) Instalar dependencias
```
pip install -r requirements.txt
```

### 3) Levantar el servidor
```
uvicorn app.main:app --reload
```

## Tests

Ejecutar la suite completa de tests:
```
python -m pytest Backend/tests
```

Opcional, con coverage:
```
pytest --cov=app Backend/tests
```

