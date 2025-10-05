"""Compatibilidad de esquemas.

Este módulo re-exporta los DTOs definidos en capa_3_api/dtos/partidas para unificar
la definición en un solo lugar, manteniendo compatibilidad con los nombres que
utilizan los endpoints y tests actuales (PartidaCreada, JugadorCreate, etc.).
"""

from app.capa_3_api.dtos.partidas import (
    Jugador as Jugador,
    Partida as Partida,
    JugadorCrear as _JugadorCrear,
    PartidaCrear as _PartidaCrear,
)

# Aliases compatibles con nombres existentes en el código y tests
JugadorCreate = _JugadorCrear
PartidaCreada = _PartidaCrear

