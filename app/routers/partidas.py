# Defino los endpoints de partidas

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from Backend.app.schemas.partidas import PartidaCreada, Jugador, Partida

partida_router= APIRouter()

@partida_router.get(path="/partidas")
async def listar_partidas() -> List[Partida]:
    # Aca se define la logica para listar partidas no empezadas,
    # y enviar al usuario. Dejo lo siguiente como ejemplo, pero
    # hay que reemplazar
    return [
        Partida(ID=1, minimo=2, maximo=4, cantidad=2),
        Partida(ID=2, minimo=3, maximo=5, cantidad=3)
    ]

@partida_router.post(path="/partidas", status_code=status.HTTP_201_CREATED)
async def crear_partida(partida: PartidaCreada):
    # Aca se define la logica para crear una partida
    return {"mensaje": f"partida creada con exito"}

