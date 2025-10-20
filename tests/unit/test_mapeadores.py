from datetime import date
from app.capa_3_api.mapeadores import (
    mapear_partida_a_dict, mapear_partidas_a_dict,
    mapear_jugador_a_dict, mapear_jugadores_a_dict,
    mapear_partida_a_dto, mapear_partidas_a_dto,
    mapear_jugador_a_dto, mapear_jugadores_a_dto,
    mapear_carta_a_dto, mapear_cartas_a_dto,
    mapear_secreto_a_dto, mapear_secretos_a_dto,
    mapear_set_a_dto
)
from tests.mocks.repos_mocks import (
    crear_partida_en_espera, crear_jugador, crear_carta, crear_secreto, crear_set
)

def test_mapear_partida_a_dict_objeto():
    partida = crear_partida_en_espera(id_partida=1)
    res = mapear_partida_a_dict(partida)
    assert res["id_partida"] == 1

def test_mapear_partida_a_dict_dict():
    partida_dict = {
        "id_partida": 2,
        "minimo": 2,
        "maximo": 4,
        "id_jugador_creador": 11,
        "estado": "en_espera",
        "cantidad_jugadores": 3,
        "turno_actual": 1,
        "jugadores": []
    }
    res = mapear_partida_a_dict(partida_dict)
    assert res["id_partida"] == 2

def test_mapear_partidas_a_dict():
    partidas = [crear_partida_en_espera(id_partida=1), crear_partida_en_espera(id_partida=2)]
    res = mapear_partidas_a_dict(partidas)
    assert isinstance(res, list)
    assert res[0]["id_partida"] == 1

def test_mapear_jugador_a_dict_objeto():
    jugador = crear_jugador(id_jugador=10, nombre="Ana", fecha_nacimiento=date(2000, 1, 1))
    res = mapear_jugador_a_dict(jugador)
    assert res["id_jugador"] == 10
    assert res["nombre"] == "Ana"

def test_mapear_jugador_a_dict_dict():
    jugador_dict = {
        "id_jugador": 20,
        "nombre": "Beto",
        "fecha_nacimiento": date(1999, 5, 5),
        "id_avatar": 2,
        "orden_turno": 1
    }
    res = mapear_jugador_a_dict(jugador_dict)
    assert res["id_jugador"] == 20
    assert res["nombre"] == "Beto"

def test_mapear_jugadores_a_dict():
    jugadores = [crear_jugador(id_jugador=10), crear_jugador(id_jugador=11)]
    res = mapear_jugadores_a_dict(jugadores)
    assert isinstance(res, list)
    assert res[0]["id_jugador"] == 10

def test_mapear_partida_a_dto():
    partida = crear_partida_en_espera(id_partida=1)
    dto = mapear_partida_a_dto(partida)
    assert dto.id_partida == 1

def test_mapear_partidas_a_dto():
    partidas = [crear_partida_en_espera(id_partida=1), crear_partida_en_espera(id_partida=2)]
    dtos = mapear_partidas_a_dto(partidas)
    assert isinstance(dtos, list)
    assert dtos[0].id_partida == 1

def test_mapear_jugador_a_dto():
    jugador = crear_jugador(id_jugador=10, nombre="Ana", fecha_nacimiento=date(2000, 1, 1))
    dto = mapear_jugador_a_dto(jugador)
    assert dto.id_jugador == 10
    assert dto.nombre == "Ana"

def test_mapear_jugadores_a_dto():
    jugadores = [
    crear_jugador(id_jugador=10, nombre="Ana", fecha_nacimiento=date(2000, 1, 1)),
    crear_jugador(id_jugador=11, nombre="Beto", fecha_nacimiento=date(1999, 5, 5))
    ]
    dtos = mapear_jugadores_a_dto(jugadores)
    assert isinstance(dtos, list)
    assert dtos[0].id_jugador == 10

def test_mapear_carta_a_dto():
    carta = crear_carta(id_carta=1, id_partida=1, posicion="mazo")
    carta.nombre = "A"
    # Usá el enum correcto para tipo si lo requiere el DTO
    carta.tipo = "detective"
    dto = mapear_carta_a_dto(carta)
    assert dto.id_carta == 1
    assert dto.nombre == "A"

def test_mapear_cartas_a_dto():
    carta1 = crear_carta(id_carta=1, id_partida=1, posicion="mazo")
    carta1.nombre = "A"
    carta1.tipo = "detective"
    carta2 = crear_carta(id_carta=2, id_partida=1, posicion="mazo")
    carta2.nombre = "B"
    carta2.tipo = "event"
    dtos = mapear_cartas_a_dto([carta1, carta2])
    assert isinstance(dtos, list)
    assert dtos[0].id_carta == 1
    assert dtos[1].nombre == "B"

def test_mapear_secreto_a_dto():
    secreto = crear_secreto(id_secreto=1, tipo="asesino", estado="oculto")
    dto = mapear_secreto_a_dto(secreto)
    assert dto.id_secreto == 1
    assert dto.tipo == "asesino"

def test_mapear_secretos_a_dto():
    secretos = [crear_secreto(id_secreto=1), crear_secreto(id_secreto=2)]
    dtos = mapear_secretos_a_dto(secretos)
    assert isinstance(dtos, list)
    assert dtos[0].id_secreto == 1

def test_mapear_set_a_dto():
    set_obj = crear_set(id_set=1, nombre="Set1")
    dto = mapear_set_a_dto(set_obj)
    assert dto.id_set == 1
    assert dto.nombre == "Set1"