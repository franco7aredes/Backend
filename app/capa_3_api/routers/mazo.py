from fastapi import APIRouter, status, Depends, HTTPException
from app.capa_3_api.websockets.ApiWS import manager
from app.capa_2_logica.servicio_juego import ServicioJuego
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.errores import PartidaNoEncontrada
from app.capa_3_api.dtos.mazo import (
	ReponerRequest,
	ReponerResponse,
	DescartarRequest,
	DescartarResponse,
	ManoResponse,
)

mazo_router = APIRouter()


@mazo_router.put("/partida/{partida_id}/reponer", response_model=ReponerResponse, status_code=status.HTTP_200_OK)
async def reponer_mazo(partida_id: int, data: ReponerRequest, service: ServicioJuego = Depends(obtener_servicio_juego)):
	MAX_CARTAS_EN_MANO = 6

	jugador_id = data.jugador_id

	# Usar servicio
	try:
		resultado = await service.reponer_del_mazo(partida_id, jugador_id, MAX_CARTAS_EN_MANO)
	except PartidaNoEncontrada:
		raise HTTPException(status_code=404, detail="Partida no encontrada")
	except ValueError as e:
		if str(e) == "jugador_no_encontrado":
			raise HTTPException(status_code=404, detail="Jugador no encontrado")
		if str(e) == "jugador_no_en_partida":
			raise HTTPException(status_code=400, detail="El jugador no pertenece a la partida indicada")
		raise

	if resultado["max_alcanzado"]:
		return ReponerResponse(mensaje="El jugador ya tiene el maximo de cartas en la mano")

	if resultado["sin_cartas"]:
		# notificar fin de mazo
		try:
			await manager.send_text(jugador_id, "fin_de_mazo")
			await manager.send_message({"evento": "fin_de_mazo", "partida_id": partida_id}, jugador_id)
			await manager.broadcast_to_partida(partida_id, {"evento": "fin_de_mazo", "partida_id": partida_id})
		except Exception:
			pass
		# No hay cartas para reponer: devolver 404
		raise HTTPException(status_code=404, detail="No hay cartas disponibles en el mazo")

	if resultado["fin_de_mazo"]:
		try:
			await manager.send_text(jugador_id, "fin_de_mazo")
			await manager.send_message({"evento": "fin_de_mazo", "partida_id": partida_id}, jugador_id)
			await manager.broadcast_to_partida(partida_id, {"evento": "fin_de_mazo", "partida_id": partida_id})
		except Exception:
			pass

	cartas = resultado["cartas"]
	return ReponerResponse(
		mensaje=f"Se repusieron {len(cartas)} cartas",
		cartas=[{"id": c.id_carta, "posicion": c.posicion.value} for c in cartas],
	)


@mazo_router.patch("/partida/{partida_id}/descartar", response_model=DescartarResponse, status_code=status.HTTP_200_OK)
async def descartar_carta_por_jugador(partida_id: int, data: DescartarRequest, service: ServicioJuego = Depends(obtener_servicio_juego)):
	jugador_id = data.jugador_id
	carta_id = await service.descartar_carta(partida_id, jugador_id)
	if carta_id is None:
		raise HTTPException(status_code=404, detail="No se encontró carta para descartar en esta partida")
	return DescartarResponse(mensaje=f"Carta {carta_id} descartada por jugador {jugador_id} en partida {partida_id}")


@mazo_router.get("/partida/{partida_id}/mano/{jugador_id}", response_model=ManoResponse, status_code=status.HTTP_200_OK)
async def obtener_mano_jugador(partida_id: int, jugador_id: int, service: ServicioJuego = Depends(obtener_servicio_juego)):
	"""Devuelve la cantidad de cartas en mano del jugador en la partida."""
	cantidad = await service.obtener_cantidad_mano(partida_id, jugador_id)
	return ManoResponse(cantidad=cantidad)
