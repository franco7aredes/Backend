import pytest
from app.capa_0_definicion_bd.base_datos_sqlalchemy import get_async_db, AsyncSessionLocal

@pytest.mark.asyncio
async def test_get_async_db_commit(monkeypatch):
    class DummySession:
        def __init__(self):
            self.committed = False
            self.rolled_back = False
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): return False
        async def commit(self): self.committed = True
        async def rollback(self): self.rolled_back = True

    monkeypatch.setattr("app.capa_0_definicion_bd.base_datos_sqlalchemy.AsyncSessionLocal", lambda: DummySession())
    gen = get_async_db()
    session = await gen.__anext__()
    # Simula uso normal, luego cierra el generador para disparar el commit
    try:
        await gen.__anext__()
    except StopAsyncIteration:
        pass
    assert session.committed is True
    assert session.rolled_back is False

@pytest.mark.asyncio
async def test_get_async_db_rollback(monkeypatch):
    class DummySession:
        def __init__(self):
            self.committed = False
            self.rolled_back = False
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): return False
        async def commit(self): raise Exception("fail")
        async def rollback(self): self.rolled_back = True

    monkeypatch.setattr("app.capa_0_definicion_bd.base_datos_sqlalchemy.AsyncSessionLocal", lambda: DummySession())
    gen = get_async_db()
    session = await gen.__anext__()
    # Simula excepción en commit al cerrar el generador
    try:
        await gen.__anext__()
    except Exception:
        pass
    assert session.rolled_back is True