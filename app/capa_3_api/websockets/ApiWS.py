from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Any, List
import json

# Router para agrupar las rutas WebSocket (Capa 3 - API)
ws_router = APIRouter()


class AdministradorConexiones:
	"""Administra conexiones WebSocket por jugador y por partida (salas)."""

	def __init__(self):
		# Diccionario de clientes conectados: id_jugador -> WebSocket
		self.conexiones_activas: Dict[int, WebSocket] = {}
		# Salas por partida: partida_id -> lista de WebSockets conectados a esa sala
		self.salas: Dict[int, List[WebSocket]] = {}

	async def conectar(self, id_jugador: int, websocket: WebSocket):
		"""Acepta la conexión y la registra."""
		await websocket.accept()
		self.conexiones_activas[id_jugador] = websocket
		print(f"Jugador {id_jugador} conectado.")

	def desconectar(self, id_jugador: int):
		"""Elimina la conexión de los registros."""
		if id_jugador in self.conexiones_activas:
			del self.conexiones_activas[id_jugador]
			print(f"Jugador {id_jugador} desconectado")

	async def enviar_mensaje(self, mensaje: Dict[str, Any], id_jugador: int):
		"""Envía un mensaje JSON a un cliente específico."""
		if id_jugador in self.conexiones_activas:
			try:
				await self.conexiones_activas[id_jugador].send_json(mensaje)
			except RuntimeError as e:
				print(f"Error al enviar mensaje al jugador {id_jugador}: {e}")
				self.desconectar(id_jugador)

	async def enviar_texto(self, id_jugador: int, mensaje: str):
		"""Envía texto plano a un cliente específico."""
		if id_jugador in self.conexiones_activas:
			try:
				await self.conexiones_activas[id_jugador].send_text(mensaje)
			except RuntimeError as e:
				print(f"Error al enviar mensaje al jugador {id_jugador}: {e}")
				self.desconectar(id_jugador)

	async def difundir(self, mensaje: str):
		"""Envía un texto a todos los clientes conectados."""
		for conexion in list(self.conexiones_activas.values()):
			await conexion.send_text(mensaje)


	# --- Manejo de salas por partida ---
	def unir_sala(self, partida_id: int, websocket: WebSocket):
		if partida_id not in self.salas:
			self.salas[partida_id] = []
		self.salas[partida_id].append(websocket)

	def salir_sala(self, partida_id: int, websocket: WebSocket):
		if partida_id in self.salas:
			try:
				self.salas[partida_id].remove(websocket)
			except ValueError:
				pass
			if not self.salas[partida_id]:
				del self.salas[partida_id]

	async def difundir_a_partida(self, partida_id: int, mensaje: Any):
		"""Envía un mensaje a todos los WebSockets conectados a la sala de esa partida."""
		if partida_id not in self.salas:
			return
		for ws in list(self.salas[partida_id]):
			try:
				if isinstance(mensaje, (dict, list)):
					await ws.send_json(mensaje)
				else:
					await ws.send_text(str(mensaje))
			except RuntimeError:
				# si falla, removemos esa conexión de la sala
				self.salir_sala(partida_id, ws)



administrador = AdministradorConexiones()


# Endpoint WebSocket individual (por jugador)
@ws_router.websocket("/ws/{id_jugador}")
async def websocket_endpoint(websocket: WebSocket, id_jugador: int):
	await administrador.conectar(id_jugador, websocket)
	try:
		while True:
			text = await websocket.receive_text()
			print(f"Mensaje recibido de {id_jugador}: {text}")
			# Eco privado al propio jugador (endpoint individual)
			await administrador.enviar_texto(id_jugador, text)
			# Privacidad: no difundimos a otros desde este endpoint.
			# Para broadcast usar el endpoint de sala (/ws/partida/{partida_id})
			# o invocar administrador.difundir_a_partida desde los routers.
	except WebSocketDisconnect:
		administrador.desconectar(id_jugador)


# Endpoint WebSocket por partida (sala)
@ws_router.websocket("/ws/partida/{partida_id}")
async def websocket_partida_endpoint(websocket: WebSocket, partida_id: int):
	# Aceptamos y agregamos la conexión a la sala correspondiente
	await websocket.accept()
	administrador.unir_sala(partida_id, websocket)
	try:
		while True:
			# Leemos mensajes entrantes y permitimos pedir un broadcast explícito
			data = await websocket.receive_text()
			print(f"WS sala {partida_id} recibió: {data}")
			# Si es JSON con {"evento":"broadcast","mensaje": ...} difundimos a toda la sala
			try:
				payload = json.loads(data)
			except json.JSONDecodeError:
				payload = None
			if isinstance(payload, dict) and payload.get("evento") == "broadcast":
				mensaje = payload.get("mensaje")
				await administrador.difundir_a_partida(partida_id, {
					"evento": "broadcast",
					"sala": partida_id,
					"mensaje": mensaje,
				})
	except WebSocketDisconnect:
		administrador.salir_sala(partida_id, websocket)

