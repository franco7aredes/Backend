from app.capa_2_logica.convertidores import _estado_a_str, partida_a_dict, jugador_a_dict

def test_estado_a_str_con_value():
    class DummyEstado:
        value = "en_juego"
    assert _estado_a_str(DummyEstado()) == "en_juego"

def test_estado_a_str_sin_value():
    assert _estado_a_str("finalizada") == "finalizada"

def test_partida_a_dict():
    class DummyPartida:
        id_partida = 1
        minimo = 2
        maximo = 4
        id_jugador_creador = 5
        estado = type("E", (), {"value": "en_juego"})()
        cantidad_jugadores = 3
        turno_actual = 1
    d = partida_a_dict(DummyPartida())
    assert d["id_partida"] == 1
    assert d["estado"] == "en_juego"

def test_jugador_a_dict():
    class DummyJugador:
        id_jugador = 1
        nombre = "Ana"
        fecha_nacimiento = "2000-01-01"
        id_avatar = None
        orden_turno = None
    d = jugador_a_dict(DummyJugador())
    assert d["id_jugador"] == 1
    assert d["nombre"] == "Ana"
