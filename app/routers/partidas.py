# Defino los endpoints de partidas

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.partidas import PartidaCreada, Jugador

partidas_router= APIRouter()

@partidas_router.get(path="/partidas")
async def listar_partidas():
    # Aca se define la logica para listar partidas no empezadas,
    # y enviar al usuario
    return {"mensaje":f"aca estan las partidas"}

@partidas_router.post(path="/partidas", status_code=status.HTTP_201_CREATED)
async def crear_partida(partida: PartidaCreada):
    # Aca se define la logica para crear una partida
    return {"mensaje": f"partida creada con exito"}
