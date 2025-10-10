import pytest
from unittest.mock import patch
from app.capa_2_logica.servicio_juego import ServicioJuego
from tests.mocks.repos_mocks import (
    crear_repo_partida_mock,
    crear_repo_jugador_mock,
    crear_repo_carta_mock,
    crear_repo_secreto_mock,
    crear_jugador,
)


@pytest.mark.asyncio
@patch('app.capa_2_logica.servicio_juego.random.shuffle', lambda x: None)
async def test_repartir_cartas_equitativamente():
    repo_p = crear_repo_partida_mock()
    repo_j = crear_repo_jugador_mock(
        listar_por_partida_return=[crear_jugador(id_jugador=1), crear_jugador(id_jugador=2)]
    )
    repo_c = crear_repo_carta_mock(contar_en_mano_return=0, obtener_mazo_disponible_return=[])
    repo_s = crear_repo_secreto_mock()

    s = ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c, secretos=repo_s)

    datos = await s.repartir_cartas(1, 3)

    # Assert: estructura válida en dataclass
    assert hasattr(datos, 'repartidas') and hasattr(datos, 'mazo')
    assert isinstance(datos.repartidas, dict)


@pytest.mark.asyncio
async def test_repartir_cartas_sin_jugadores():
    repo_p = crear_repo_partida_mock()
    repo_j = crear_repo_jugador_mock(listar_por_partida_return=[])
    repo_c = crear_repo_carta_mock(contar_en_mano_return=0, obtener_mazo_disponible_return=[])

    repo_s = crear_repo_secreto_mock()
    s = ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c, secretos=repo_s)
    datos = await s.repartir_cartas(1, 3)
    assert datos.repartidas == {}
    assert datos.mazo == []

@pytest.mark.asyncio
async def test_repartir_secretos_bonito():
    repo_p = crear_repo_partida_mock()
    repo_j = crear_repo_jugador_mock(
        listar_por_partida_return=[crear_jugador(id_jugador=1), crear_jugador(id_jugador=2)]
    )
    repo_s = crear_repo_secreto_mock()
    repo_c = crear_repo_carta_mock(contar_en_mano_return=0, obtener_mazo_disponible_return=[])

    s = ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c, secretos=repo_s)
    datos = await s.repartir_secretos(1)

    assert hasattr(datos, 'secretos_repartidos')
    assert isInstance(datos.secretos_repartidos, dict)

@pytest.mark.asyncio
async def test_repartir_secretos_sin_jugadores():
    repo_p = crear_repo_partida_mock()
    repo_j = crear_repo_jugador_mock(listar_por_partida_return=[])
    repo_c = crear_repo_carta_mock(contar_en_mano_return=0, obtener_mazo_disponible_return=[])

    repo_s = crear_repo_secreto_mock()
    s = ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c, secretos=repo_s)
    datos = await s.repartir_secretos(1)
    assert datos.secretos_repartidos == {}

