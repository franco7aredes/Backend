import pytest
from unittest.mock import AsyncMock, MagicMock
from app.capa_1_acceso_datos.repositorios.jugador_sqlalchemy import RepositorioJugadorSQLAlchemy
from app.capa_0_definicion_bd.models.jugadores_modelos import Jugador as JugadorModelo
from app.capa_0_definicion_bd.models.secretos_modelos import EstadoSecreto
from tests.mocks.repos_mocks import crear_secreto

@pytest.fixture
def jugador_valido():
    return JugadorModelo(id_jugador=1, id_partida=2, nombre="Test")

@pytest.fixture
def db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.add_all = MagicMock()
    db.add = MagicMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock()
    db.delete = AsyncMock()
    return db

class DummyScalars:
    def __init__(self, items):
        self._items = items
    def all(self):
        return self._items

@pytest.mark.asyncio
async def test_listar_por_partida(db, jugador_valido):
    db.execute.return_value.scalars = lambda: DummyScalars([jugador_valido])
    repo = RepositorioJugadorSQLAlchemy(db)
    res = await repo.listar_por_partida(2)
    assert res == [jugador_valido]

@pytest.mark.asyncio
async def test_listar_por_partida_vacio(db):
    db.execute.return_value.scalars = lambda: DummyScalars([])
    repo = RepositorioJugadorSQLAlchemy(db)
    res = await repo.listar_por_partida(2)
    assert res == []

@pytest.mark.asyncio
async def test_crear(db, jugador_valido):
    repo = RepositorioJugadorSQLAlchemy(db)
    await repo.crear(jugador_valido)
    db.add.assert_called_with(jugador_valido)
    db.flush.assert_awaited()
    db.refresh.assert_awaited_with(jugador_valido)

@pytest.mark.asyncio
async def test_obtener(db, jugador_valido):
    db.get.return_value = jugador_valido
    repo = RepositorioJugadorSQLAlchemy(db)
    res = await repo.obtener(1)
    db.get.assert_awaited_with(JugadorModelo, 1)
    assert res == jugador_valido

@pytest.mark.asyncio
async def test_obtener_none(db):
    db.get.return_value = None
    repo = RepositorioJugadorSQLAlchemy(db)
    res = await repo.obtener(999)
    db.get.assert_awaited_with(JugadorModelo, 999)
    assert res is None

@pytest.mark.asyncio
async def test_guardar_muchos(db, jugador_valido):
    repo = RepositorioJugadorSQLAlchemy(db)
    await repo.guardar_muchos([jugador_valido])
    db.add_all.assert_called_with([jugador_valido])
    db.flush.assert_awaited()

@pytest.mark.asyncio
async def test_eliminar(db, jugador_valido):
    db.get.return_value = jugador_valido
    repo = RepositorioJugadorSQLAlchemy(db)
    await repo.eliminar(1)
    db.get.assert_awaited_with(JugadorModelo, 1)
    db.delete.assert_awaited_with(jugador_valido)
    db.flush.assert_awaited()

# No usamos los repos de jugador para manejar en_desgracia_social, porque es un property.
# y las property no son asincronas. Sin embargo, testeamos el property directamente.

@pytest.mark.asyncio
async def test_en_desgracia_social_false_sin_secretos():
    j = JugadorModelo()
    j.secretos = []
    assert j.en_desgracia_social is False

@pytest.mark.asyncio
async def test_en_desgracia_social_false_con_al_menos_uno_oculto():
    j = JugadorModelo()
    s1 = crear_secreto(estado=EstadoSecreto.revelado)
    s2 = crear_secreto(estado=EstadoSecreto.oculto)
    j.secretos = [s1, s2]
    assert j.en_desgracia_social is False

@pytest.mark.asyncio
async def test_en_desgracia_social_true_todos_revelados():
    j = JugadorModelo()
    s1 = crear_secreto(estado=EstadoSecreto.revelado)
    s2 = crear_secreto(estado=EstadoSecreto.revelado)
    j.secretos = [s1, s2]
    assert j.en_desgracia_social is True

@pytest.mark.asyncio
async def test_en_desgracia_social_false_todos_ocultos():
    j = JugadorModelo()
    s1 = crear_secreto(estado=EstadoSecreto.oculto)
    s2 = crear_secreto(estado=EstadoSecreto.oculto)
    j.secretos = [s1, s2]
    assert j.en_desgracia_social is False

@pytest.mark.asyncio
async def test_en_desgracia_social_true_uno_revelado():
    j = JugadorModelo()
    s1 = crear_secreto(estado=EstadoSecreto.revelado)
    j.secretos = [s1]
    assert j.en_desgracia_social is True

@pytest.mark.asyncio
async def test_en_desgracia_social_false_uno_oculto():
    j = JugadorModelo()
    s1 = crear_secreto(estado=EstadoSecreto.oculto)
    j.secretos = [s1]
    assert j.en_desgracia_social is False