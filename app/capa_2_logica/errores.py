"""
Excepciones personalizadas para la lógica del juego.
Describen errores específicos que pueden ocurrir durante la gestión de partidas y jugadores.
Son en si errores de Dominio (excepciones que representan reglas o estados del negocio,
 no del transporte (HTTP) ni de la infraestructura (BD, red).)
"""

class PartidaNoEncontrada(Exception):
    pass


class PartidaYaEnJuego(Exception):
    pass


class MinimoJugadoresNoAlcanzado(Exception):
    pass


class MaximoJugadoresAlcanzado(Exception):
    pass


class AsesinoNoEncontrado(Exception):
    pass

class JugadorNoEncontrado(Exception):
    pass

class JugadorNoEnPartida(Exception):
    pass

class SetNoEncontrado(Exception):
    pass

class SetNoEnPartida(Exception):
    pass

class NoPuedeRobarSuPropioSet(Exception):
    pass

class SecretoNoEncontrado(Exception):
    pass

class SecretoNoDisponible(Exception):
    pass

class AsesinoRevelado(Exception):
    pass

class PartidaEnJuegoNoAbandonable(Exception):
    pass

class CreadorNoPuedeAbandonarPartida(Exception):
    pass

class SetNoCorrespondeAlJugadorSeleccionado(Exception):
    pass

class CartaNoEsEvento(Exception):
    pass

class EventoNoImplementado(Exception):
  pass

class NoPuedeAplicarseEfectosAsiMismo(Exception):
    pass

class PosicionSecretoNoProporcionada(Exception):
    pass

class SetNoSoportaSeleccionDeJugador(Exception):
    pass

class JugadorEnDesgraciaSocial(Exception):
    pass

class JugadorSaleDeDesgraciaSocial(Exception):
    pass