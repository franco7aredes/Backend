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
