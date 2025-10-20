import pytest
from unittest.mock import AsyncMock, MagicMock
from app.capa_1_acceso_datos.repositorios.partida_sqlalchemy import RepositorioPartidaSQLAlchemy
from app.capa_0_definicion_bd.models.partidas_modelos import Partida as PartidaModelo, EstadoPartida

@pytest.fixture
def partida_valida():
    return PartidaModelo(id_partida=1, estado=EstadoPartida.en_espera)

@pytest.fixture
def db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db

class DummyScalars:
    def __init__(self, items):
        self._items = items
    def all(self):
        return self._items

@pytest.mark.asyncio
async def test_crear(db, partida_valida):
    repo = RepositorioPartidaSQLAlchemy(db)
    await repo.crear(partida_valida)
    db.add.assert_called_with(partida_valida)
    db.flush.assert_awaited()
    db.refresh.assert_awaited_with(partida_valida)

@pytest.mark.asyncio
async def test_obtener(db, partida_valida):
    db.get.return_value = partida_valida
    repo = RepositorioPartidaSQLAlchemy(db)
    res = await repo.obtener(1)
    db.get.assert_awaited_with(PartidaModelo, 1)
    assert res == partida_valida

@pytest.mark.asyncio
async def test_obtener_none(db):
    db.get.return_value = None
    repo = RepositorioPartidaSQLAlchemy(db)
    res = await repo.obtener(999)
    db.get.assert_awaited_with(PartidaModelo, 999)
    assert res is None

@pytest.mark.asyncio
async def test_listar_en_espera(db, partida_valida):
    db.execute.return_value.scalars = lambda: DummyScalars([partida_valida])
    repo = RepositorioPartidaSQLAlchemy(db)
    res = await repo.listar_en_espera()
    assert res == [partida_valida]

@pytest.mark.asyncio
async def test_listar_en_espera_vacio(db):
    db.execute.return_value.scalars = lambda: DummyScalars([])
    repo = RepositorioPartidaSQLAlchemy(db)
    res = await repo.listar_en_espera()
    assert res == []

@pytest.mark.asyncio
async def test_guardar(db, partida_valida):
    repo = RepositorioPartidaSQLAlchemy(db)
    await repo.guardar(partida_valida)
    db.add.assert_called_with(partida_valida)
    db.flush.assert_awaited()

@pytest.mark.asyncio
async def test_confirmar_commit(db):
    repo = RepositorioPartidaSQLAlchemy(db)
    await repo.confirmar()
    db.commit.assert_awaited()
    db.rollback.assert_not_awaited()

@pytest.mark.asyncio
async def test_confirmar_rollback(db):
    db.commit = AsyncMock(side_effect=Exception("fail"))
    repo = RepositorioPartidaSQLAlchemy(db)
    await repo.confirmar()
    db.commit.assert_awaited()
    db.rollback.assert_awaited()
