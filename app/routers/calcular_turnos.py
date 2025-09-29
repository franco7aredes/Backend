from datetime import date
from typing import List
from app.db.models.jugadores_models import Jugador as JugadorModel

# Fecha de referencia
fecha_referencia = date(1980, 9, 15)

def calcular_diferencia(fecha_nacimiento: date) -> int:
    """
    Calcula la diferencia en días entre la fecha de nacimiento del jugador y la fecha de referencia.
    """
    diferencia = abs((fecha_nacimiento - fecha_referencia).days)  # Días de diferencia
    return diferencia

def asignar_turnos(jugadores: List[JugadorModel]) -> List[JugadorModel]:
    """
    Ordena a los jugadores según la proximidad a la fecha de referencia (15-09-1980).
    Asigna un turno a cada jugador.
    """
    # Ordenar los jugadores según la diferencia de días con respecto a la fecha de referencia
    jugadores_ordenados = sorted(jugadores, key=lambda jugador: calcular_diferencia(jugador.fecha_nacimiento))

    # Asignar turnos a los jugadores (el primer turno es el más cercano)
    for i, jugador in enumerate(jugadores_ordenados):
        jugador.orden_turno = i + 1  # Persistir en la columna correcta
        print(f"Jugador: {jugador.nombre}, Fecha Nacimiento: {jugador.fecha_nacimiento}, Turno Asignado: {jugador.orden_turno}")

    
    return jugadores_ordenados
