import pytest
from unittest.mock import AsyncMock, MagicMock
from app.capa_1_acceso_datos.repositorios.carta_sqlalchemy import RepositorioCartaSQLAlchemy
from app.capa_0_definicion_bd.models.cartas_modelos import Carta as CartaModelo, PosicionCarta

class DummyScalars:
    def __init__(self, items):
        self._items = items
    def all(self):
        return self._items

@pytest.fixture
def carta_valida():
    return CartaModelo(id_carta=1, id_partida=2, nombre="A", tipo="T", posicion=PosicionCarta.mano)

@pytest.fixture
def carta_invalida():
    return CartaModelo(id_carta=2, id_partida=2, nombre=None, tipo=None, posicion=PosicionCarta.mano)

@pytest.fixture
def db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.add_all = MagicMock()
    db.add = MagicMock()
    return db

@pytest.mark.asyncio
async def test_crear_muchas_y_guardar_muchas_ok(db, carta_valida):
    repo = RepositorioCartaSQLAlchemy(db)
    await repo.crear_muchas([carta_valida])
    await repo.guardar_muchas([carta_valida])
    db.add_all.assert_called()
    db.flush.assert_awaited()

@pytest.mark.asyncio
async def test_crear_muchas_error(db, carta_invalida):
    repo = RepositorioCartaSQLAlchemy(db)
    with pytest.raises(ValueError):
        await repo.crear_muchas([carta_invalida])

@pytest.mark.asyncio
async def test_guardar_muchas_error(db, carta_invalida):
    repo = RepositorioCartaSQLAlchemy(db)
    with pytest.raises(ValueError):
        await repo.guardar_muchas([carta_invalida])

@pytest.mark.asyncio
async def test_contar_en_mano(db):
    db.execute.return_value.scalar = lambda: 5
    repo = RepositorioCartaSQLAlchemy(db)
    res = await repo.contar_en_mano(1, 2)
    assert res == 5

@pytest.mark.asyncio
async def test_obtener_mazo_disponible(db, carta_valida):
    db.execute.return_value.scalars = lambda: DummyScalars([carta_valida])
    repo = RepositorioCartaSQLAlchemy(db)
    res = await repo.obtener_mazo_disponible(1, 1)
    assert res == [carta_valida]

@pytest.mark.asyncio
async def test_contar_en_mazo(db):
    db.execute.return_value.scalar = lambda: 3
    repo = RepositorioCartaSQLAlchemy(db)
    res = await repo.contar_en_mazo(1)
    assert res == 3

@pytest.mark.asyncio
async def test_guardar_ok(db, carta_valida):
    repo = RepositorioCartaSQLAlchemy(db)
    await repo.guardar(carta_valida)
    db.add.assert_called()
    db.flush.assert_awaited()

@pytest.mark.asyncio
async def test_guardar_error(db, carta_invalida):
    repo = RepositorioCartaSQLAlchemy(db)
    with pytest.raises(ValueError):
        await repo.guardar(carta_invalida)

@pytest.mark.asyncio
async def test_obtener_draft(db, carta_valida):
    db.execute.return_value.scalars = lambda: DummyScalars([carta_valida])
    repo = RepositorioCartaSQLAlchemy(db)
    res = await repo.obtener_draft(1)
    assert res == [carta_valida]

@pytest.mark.asyncio
async def test_obtener_cartas_en_mano(db, carta_valida):
    db.execute.return_value.scalars = lambda: DummyScalars([carta_valida])
    repo = RepositorioCartaSQLAlchemy(db)
    res = await repo.obtener_cartas_en_mano(1, 2)
    assert res == [carta_valida]

@pytest.mark.asyncio
async def test_obtener_carta(db, carta_valida):
    db.execute.return_value.scalars = lambda: MagicMock(first=lambda: carta_valida)
    repo = RepositorioCartaSQLAlchemy(db)
    res = await repo.obtener_carta(1, 2, 1)
    assert res == carta_valida

@pytest.mark.asyncio
async def test_obtener_cantidad_descartadas(db):
    db.execute.return_value.scalar = lambda: 7
    repo = RepositorioCartaSQLAlchemy(db)
    res = await repo.obtener_cantidad_descartadas(1)
    assert res == 7

@pytest.mark.asyncio
async def test_obtener_draft_disponible(db, carta_valida):
    db.execute.return_value.scalars = lambda: DummyScalars([carta_valida])
    repo = RepositorioCartaSQLAlchemy(db)
    res = await repo.obtener_draft_disponible(1, 1)
    assert res == [carta_valida]

@pytest.mark.asyncio
async def test_mover_primera_carta_mazo_a_draft(db, carta_valida):
    repo = RepositorioCartaSQLAlchemy(db)
    repo.obtener_mazo_disponible = AsyncMock(return_value=[carta_valida])
    db.flush = AsyncMock()
    res = await repo.mover_primera_carta_mazo_a_draft(1)
    assert res.posicion == PosicionCarta.draft
    assert res.id_jugador is None
    db.add.assert_called()
    db.flush.assert_awaited()

@pytest.mark.asyncio
async def test_mover_primera_carta_mazo_a_draft_none(db):
    repo = RepositorioCartaSQLAlchemy(db)
    repo.obtener_mazo_disponible = AsyncMock(return_value=[])
    res = await repo.mover_primera_carta_mazo_a_draft(1)
    assert res is None

@pytest.mark.asyncio
async def test_obtener_primeras_de_descarte(db, carta_valida):
    db.execute.return_value.scalars = lambda: DummyScalars([carta_valida])
    repo = RepositorioCartaSQLAlchemy(db)
    res = await repo.obtener_primeras_de_descarte(1)
    assert res == [carta_valida]