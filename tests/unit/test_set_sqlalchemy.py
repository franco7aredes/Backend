import pytest
from unittest.mock import AsyncMock, MagicMock
from app.capa_1_acceso_datos.repositorios.set_sqlalchemy import RepositorioSetsSQLAlchemy
from app.capa_0_definicion_bd.models.sets_modelos import Set as SetModelo
from app.capa_0_definicion_bd.models.cartas_modelos import Carta as CartaModelo

@pytest.fixture
def set_valido():
    s = SetModelo(id_set=1, id_partida=2, id_jugador=3, nombre="Set1")
    s.cartas = [CartaModelo(id_carta=1, id_partida=2, nombre="A", tipo="T", posicion="set")]
    return s

@pytest.fixture
def set_sin_cartas():
    s = SetModelo(id_set=2, id_partida=2, id_jugador=3, nombre="Set2")
    s.cartas = []
    return s

@pytest.fixture
def db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    db.refresh = AsyncMock()
    return db

@pytest.mark.asyncio
async def test_crear_set(db, set_valido):
    repo = RepositorioSetsSQLAlchemy(db)
    await repo.crear_set(set_valido)
    db.add.assert_called_with(set_valido)
    db.flush.assert_awaited()
    db.refresh.assert_awaited_with(set_valido)

@pytest.mark.asyncio
async def test_obtener_set_por_id(db, set_valido):
    db.execute.return_value.scalar_one_or_none = lambda: set_valido
    repo = RepositorioSetsSQLAlchemy(db)
    res = await repo.obtener_set_por_id(1)
    assert res == set_valido

@pytest.mark.asyncio
async def test_obtener_set_por_id_none(db):
    db.execute.return_value.scalar_one_or_none = lambda: None
    repo = RepositorioSetsSQLAlchemy(db)
    res = await repo.obtener_set_por_id(999)
    assert res is None

@pytest.mark.asyncio
async def test_guardar_set(db, set_valido):
    repo = RepositorioSetsSQLAlchemy(db)
    await repo.guardar_set(set_valido)
    db.add.assert_called_with(set_valido)
    db.flush.assert_awaited()

@pytest.mark.asyncio
async def test_obtener_cartas_del_set_con_cartas(db, set_valido):
    db.execute.return_value.scalar_one_or_none = lambda: set_valido
    repo = RepositorioSetsSQLAlchemy(db)
    res = await repo.obtener_cartas_del_set(1)
    assert res == set_valido.cartas

@pytest.mark.asyncio
async def test_obtener_cartas_del_set_sin_cartas(db, set_sin_cartas):
    db.execute.return_value.scalar_one_or_none = lambda: set_sin_cartas
    repo = RepositorioSetsSQLAlchemy(db)
    res = await repo.obtener_cartas_del_set(2)
    assert res == []

@pytest.mark.asyncio
async def test_obtener_cartas_del_set_none(db):
    db.execute.return_value.scalar_one_or_none = lambda: None
    repo = RepositorioSetsSQLAlchemy(db)
    res = await repo.obtener_cartas_del_set(999)
    assert res == []