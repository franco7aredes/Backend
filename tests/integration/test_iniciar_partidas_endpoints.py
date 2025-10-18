import pytest
from unittest.mock import AsyncMock
import app.capa_3_api.routers.partidas as rpart
from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.errores import PartidaYaEnJuego, PartidaNoEncontrada, MaximoJugadoresAlcanzado, MinimoJugadoresNoAlcanzado
from tests.mocks.repos_mocks import crear_partida_en_espera, crear_jugador, crear_secreto



@pytest.mark.asyncio
async def test_iniciar_partida_con_exito_bonito(async_client, monkeypatch):
    class S:
        async def iniciar_y_preparar_partida(self, *args, **kwargs): ...
    mock_service = S()
    setattr(mock_service, "iniciar_y_preparar_partida", AsyncMock(return_value={"repartidas": {}}))
    def _dep():
        return mock_service
    fastapi_app.dependency_overrides[obtener_servicio_juego] = _dep

    monkeypatch.setattr(rpart, "_notify_players_async", AsyncMock())
    monkeypatch.setattr(rpart.administrador, "difundir_a_partida", AsyncMock())

    resp = await async_client.patch("/partidas/2/iniciar", json={})
    assert resp.status_code == 200
    assert resp.json()["mensaje"] == "La partida comenzo"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_iniciar_partida_ya_iniciada_bonito(async_client):
    class S:
        async def iniciar_y_preparar_partida(self, *args, **kwargs): ...
    async def raise_err(*_, **__):
        raise PartidaYaEnJuego()
    mock_service = S()
    setattr(mock_service, "iniciar_y_preparar_partida", raise_err)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    resp = await async_client.patch("/partidas/3/iniciar", json={})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "La partida ya esta en juego"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_iniciar_partida_no_encontrada_bonito(async_client):
    class S:
        async def iniciar_y_preparar_partida(self, *args, **kwargs): ...
    async def raise_nf(*_, **__):
        raise PartidaNoEncontrada()
    mock_service = S()
    setattr(mock_service, "iniciar_y_preparar_partida", raise_nf)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    resp = await async_client.patch("/partidas/999/iniciar", json={})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Partida no encontrada"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_unirse_a_partida_con_exito_bonito(async_client, monkeypatch):
    class P:
        id_partida = 4
        estado = "En espera"
        id_jugador_creador = 1
    class J:
        id_jugador = 55
        nombre = "TestJugador"
        id_avatar = 1
        orden_turno = 1

    class S:
        async def unirse_a_partida(self, *args, **kwargs): ...
        async def listar_jugadores(self, partida_id: int): ...
    mock_service = S()
    setattr(mock_service, "unirse_a_partida", AsyncMock(return_value=(P(), J())))
    setattr(mock_service, "listar_jugadores", AsyncMock(return_value=[J()]))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    monkeypatch.setattr(rpart.administrador, "enviar_mensaje", AsyncMock())
    monkeypatch.setattr(rpart.administrador, "difundir_a_partida", AsyncMock())

    jugador_data = {"nombre": "TestJugador", "fecha_nacimiento": "1990-01-01T00:00:00"}
    resp = await async_client.put("/partidas/4/unirse", json=jugador_data)
    assert resp.status_code == 201
    body = resp.json()
    assert body["mensaje"] == "jugador agregado"
    assert body["jugador_id"] == 55

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_unirse_a_partida_llena_bonito(async_client):
    class S:
        async def unirse_a_partida(self, *args, **kwargs): ...
    async def raise_full(*_, **__):
        raise MaximoJugadoresAlcanzado()
    mock_service = S()
    setattr(mock_service, "unirse_a_partida", raise_full)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    jugador_data = {"nombre": "JugadorExtra", "fecha_nacimiento": "1990-01-01T00:00:00"}
    resp = await async_client.put("/partidas/5/unirse", json=jugador_data)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "La partida ya tiene el máximo de jugadores"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_unirse_a_partida_no_encontrada_bonito(async_client):
    class S:
        async def unirse_a_partida(self, *args, **kwargs): ...
    async def raise_nf(*_, **__):
        raise PartidaNoEncontrada()
    mock_service = S()
    setattr(mock_service, "unirse_a_partida", raise_nf)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    jugador_data = {"nombre": "JugadorInexistente", "fecha_nacimiento": "1990-01-01T00:00:00"}
    resp = await async_client.put("/partidas/999/unirse", json=jugador_data)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Partida no encontrada"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_iniciar_partida_minimo_jugadores_no_alcanzado(async_client):
    class S:
        async def iniciar_y_preparar_partida(self, *args, **kwargs):
            raise MinimoJugadoresNoAlcanzado()
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: S()
    resp = await async_client.patch("/partidas/10/iniciar", json={})
    assert resp.status_code == 400
    assert "cantidad mínima de jugadores" in resp.text
    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_iniciar_partida_error_interno(async_client):
    class S:
        async def iniciar_y_preparar_partida(self, *args, **kwargs):
            raise Exception("fallo inesperado")
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: S()
    resp = await async_client.patch("/partidas/12/iniciar", json={})
    assert resp.status_code == 500
    assert "Error interno del servidor" in resp.text
    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_iniciar_partida_envia_secretos_a_jugadores(async_client, monkeypatch):

    # Simula dos jugadores con secretos
    secreto1 = crear_secreto(id_secreto=1, id_jugador=10)
    secreto2 = crear_secreto(id_secreto=2, id_jugador=20)
    secretos_repartidos = {
        10: [secreto1],
        20: [secreto2],
    }

    class Resultado:
        secretos = secretos_repartidos
        repartidas = None

    class ServicioMock:
        async def iniciar_y_preparar_partida(self, *a, **k): return Resultado()

    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: ServicioMock()

    # Mock administrador.enviar_mensaje para verificar llamadas
    import app.capa_3_api.websockets.ApiWS as wsmod
    enviar_mensaje_mock = AsyncMock()
    monkeypatch.setattr(wsmod.administrador, "enviar_mensaje", enviar_mensaje_mock)
    monkeypatch.setattr(wsmod.administrador, "difundir_a_partida", AsyncMock())

    resp = await async_client.patch("/partidas/1/iniciar", json={})
    assert resp.status_code == 200

    # Verifica que se llamó enviar_mensaje para cada jugador con los secretos correspondientes
    called_jugadores = set()
    for call in enviar_mensaje_mock.call_args_list:
        args, kwargs = call
        mensaje, jugador_id = args
        assert mensaje["evento"] == "partida_iniciada"
        assert "secretos" in mensaje["data"]
        called_jugadores.add(jugador_id)
    assert called_jugadores == {10, 20}

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_unirse_a_partida_objeto_res_unirse_repos(async_client, monkeypatch):
    from tests.mocks.repos_mocks import crear_partida_en_espera, crear_jugador

    partida_mock = crear_partida_en_espera(id_partida=5)
    partida_mock.id_jugador_creador = 99
    partida_mock.estado = "En espera"

    jugador_mock = crear_jugador(id_jugador=55, nombre="Nuevo", orden_turno=1)
    jugador_mock.id_avatar = 3
    jugador_mock.fecha_nacimiento = "2001-01-01"

    class ResUnirse:
        partida = partida_mock
        jugador = jugador_mock

    class ServicioMock:
        async def unirse_a_partida(self, *args, **kwargs): return ResUnirse()
        async def listar_jugadores(self, partida_id: int): return [jugador_mock]

    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: ServicioMock()

    import app.capa_3_api.routers.partidas as rpart
    monkeypatch.setattr(rpart.administrador, "enviar_mensaje", AsyncMock())
    monkeypatch.setattr(rpart.administrador, "difundir_a_partida", AsyncMock())

    jugador_data = {"nombre": "Nuevo", "fecha_nacimiento": "2001-01-01T00:00:00", "id_avatar": 3}
    resp = await async_client.put("/partidas/5/unirse", json=jugador_data)
    assert resp.status_code == 201
    body = resp.json()
    assert body["mensaje"] == "jugador agregado"
    assert body["jugador_id"] == 55
    assert body["id_partida"] == 5
    assert body["id_jugador_creador"] == 99

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_unirse_a_partida_error_interno(async_client):
    class ServicioMock:
        async def unirse_a_partida(self, *args, **kwargs):
            raise Exception("fallo inesperado")
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: ServicioMock()

    jugador_data = {"nombre": "Error", "fecha_nacimiento": "2000-01-01T00:00:00", "id_avatar": 1}
    resp = await async_client.put("/partidas/99/unirse", json=jugador_data)
    assert resp.status_code == 500
    assert "Error interno del servidor" in resp.text

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)