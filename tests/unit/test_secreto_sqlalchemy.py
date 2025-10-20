import pytest
from unittest.mock import AsyncMock, MagicMock
from app.capa_1_acceso_datos.repositorios.secreto_sqlalchemy import RepositorioSecretoSQLAlchemy
from app.capa_0_definicion_bd.models.secretos_modelos import SecretoDB, EstadoSecreto, TipoSecreto

@pytest.fixture
def secreto_valido():
    return SecretoDB(
        id_secreto=1,
        id_partida=2,
        id_jugador=3,
        tipo=TipoSecreto.asesino,
        estado=EstadoSecreto.oculto,
    )

@pytest.fixture
def db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.add_all = MagicMock()
    return db

class DummyScalars:
    def __init__(self, items):
        self._items = items
    def all(self):
        return self._items
    def first(self):
        return self._items[0] if self._items else None

@pytest.mark.asyncio
async def test_crear_muchos(db, secreto_valido):
    repo = RepositorioSecretoSQLAlchemy(db)
    await repo.crear_muchos([secreto_valido])
    db.add_all.assert_called_with([secreto_valido])
    db.flush.assert_awaited()

@pytest.mark.asyncio
async def test_obtener_secretos(db, secreto_valido):
    db.execute.return_value.scalars = lambda: DummyScalars([secreto_valido])
    repo = RepositorioSecretoSQLAlchemy(db)
    res = await repo.obtener_secretos(2, 3)
    assert res == [secreto_valido]

@pytest.mark.asyncio
async def test_obtener_secretos_vacio(db):
    db.execute.return_value.scalars = lambda: DummyScalars([])
    repo = RepositorioSecretoSQLAlchemy(db)
    res = await repo.obtener_secretos(2, 3)
    assert res == []

@pytest.mark.asyncio
async def test_obtener_secreto_asesino(db, secreto_valido):
    db.execute.return_value.scalars = lambda: DummyScalars([secreto_valido])
    repo = RepositorioSecretoSQLAlchemy(db)
    res = await repo.obtener_secreto_asesino(2)
    assert res == secreto_valido

@pytest.mark.asyncio
async def test_obtener_secreto_asesino_none(db):
    db.execute.return_value.scalars = lambda: DummyScalars([])
    repo = RepositorioSecretoSQLAlchemy(db)
    res = await repo.obtener_secreto_asesino(2)
    assert res is None

@pytest.mark.asyncio
async def test_contar_secretos_jugador(db):
    db.execute.return_value.scalar = lambda: 5
    repo = RepositorioSecretoSQLAlchemy(db)
    res = await repo.contar_secretos_jugador(2, 3)
    assert res == 5

@pytest.mark.asyncio
async def test_contar_secretos_jugador_none(db):
    db.execute.return_value.scalar = lambda: None
    repo = RepositorioSecretoSQLAlchemy(db)
    res = await repo.contar_secretos_jugador(2, 3)
    assert res == 0
