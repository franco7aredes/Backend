import pytest
from unittest.mock import patch
from app.capa_2_logica.servicio_juego import ServicioJuego
from tests.mocks.repos_mocks import (
    crear_repo_partida_mock,
    crear_repo_jugador_mock,
    crear_repo_carta_mock,
    crear_repo_secreto_mock,
    crear_jugador,
    crear_partida_en_espera,
)
from app.capa_0_definicion_bd.models.cartas_modelos import TipoCarta


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
    assert isinstance(datos.secretos_repartidos, dict)

@pytest.mark.asyncio
async def test_repartir_secretos_sin_jugadores():
    repo_p = crear_repo_partida_mock()
    repo_j = crear_repo_jugador_mock(listar_por_partida_return=[])
    repo_c = crear_repo_carta_mock(contar_en_mano_return=0, obtener_mazo_disponible_return=[])

    repo_s = crear_repo_secreto_mock()
    s = ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c, secretos=repo_s)
    datos = await s.repartir_secretos(1)
    assert datos.secretos_repartidos == {}



@pytest.mark.asyncio
async def test_reparto_garantiza_instant_y_compone_mazo():
    # Preparación de repos con partida y 3 jugadores
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_espera(id_partida=77, cantidad_jugadores=3, minimo=2, maximo=6))
    repo_j = crear_repo_jugador_mock(
        listar_por_partida_return=[
            crear_jugador(id_jugador=10, id_partida=77),
            crear_jugador(id_jugador=11, id_partida=77),
            crear_jugador(id_jugador=12, id_partida=77),
        ]
    )
    repo_c = crear_repo_carta_mock()

    s = ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c)

    num_cartas = 6
    datos = await s.repartir_cartas(77, num_cartas)

    # Cada jugador debe recibir una carta instant ("Not so fast") obligatoria
    for jid, cartas in datos.repartidas.items():
        assert len(cartas) == num_cartas
        assert any((c.tipo == TipoCarta.instant and (c.nombre or "").lower() == "not so fast") for c in cartas)
        # Todas las cartas deben tener nombre y tipo seteados
        assert all(c.nombre is not None and c.tipo is not None for c in cartas)

    # El total de cartas creadas debe ser 61: repartidas + mazo restante
    total_creadas = sum(len(v) for v in datos.repartidas.values()) + len(datos.mazo)
    assert total_creadas == 61

    # Validar conteos por (tipo, nombre) según definición
    from collections import Counter
    """ Counter se usa para contar cuántas cartas hay de cada par (tipo, nombre)
      en el conjunto total de cartas (repartidas + mazo)"""
    todas = [*datos.mazo]
    for cartas in datos.repartidas.values():
        todas.extend(cartas)
    def key_tuple(c):
        tipo_str = str(getattr(c.tipo, 'value', c.tipo))
        nombre_str = str(getattr(c, 'nombre', ''))
        return (tipo_str, nombre_str)
    pares = Counter(key_tuple(c) for c in todas)

    # Detectives
    assert pares[("detective", "Harley Quin Wildcard")] == 4
    assert pares[("detective", "Adriane Oliver")] == 3
    assert pares[("detective", "Miss Marple")] == 3
    assert pares[("detective", "Parker Pyne")] == 3
    assert pares[("detective", "Tommy Beresford")] == 2
    assert pares[("detective", 'Lady Eileen "Bundle" Brent')] == 3
    assert pares[("detective", "Tuppence Beresford")] == 2
    assert pares[("detective", "Hercule Poirot")] == 3
    assert pares[("detective", "Mr Satterthwaite")] == 2

    # Instants
    assert pares[("instant", "Not so fast")] == 10

    # Devious
    assert pares[("devious", "Blackmailed")] == 1
    assert pares[("devious", "Social Faux Pas")] == 3

    # Events
    assert pares[("event", "Delay the murderer's espace!")] == 3
    assert pares[("event", "Point your suspicions")] == 3
    assert pares[("event", "Dead card folly")] == 3
    assert pares[("event", "Another Victim")] == 2
    assert pares[("event", "Look into the ashes")] == 3
    assert pares[("event", "Card trade")] == 3
    assert pares[("event", "And then there was one more...")] == 2
    assert pares[("event", "Early train to paddington")] == 2
    assert pares[("event", "Cards off the table")] == 1

