from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Any, List
import json

# Creamos el router para agrupar las rutas WebSocket
ws_router = APIRouter()

# Clase para manejar las conexiones activas
class ConnectionManager:
    def __init__(self):
        # Hace una lista vacia donde van a ir los clientes conectados
        self.active_connections: Dict[int, WebSocket] = {}
        # Salas por partida: partida_id -> lista de websockets conectados a esa sala
        self.rooms: Dict[int, List[WebSocket]] = {}

    async def connect(self, id_jugador:int, websocket: WebSocket):
        # Acepta la conexión y la agrega a la lista
        await websocket.accept()
        self.active_connections[id_jugador] = websocket
        print(f"Jugador {id_jugador} conectado.")

    def disconnect(self, id_jugador: int):
        # Elimina la conexión de la lista
        if id_jugador in self.active_connections:
            del self.active_connections[id_jugador]
            print(f"Jugador {id_jugador} desconectado")

    async def send_message(self, message: Dict[str, Any], id_jugador: int):
        # Envía un mensaje a un cliente específico
        if id_jugador in self.active_connections:
            try:
                # usamos send_json para enviar cosas
                await self.active_connections[id_jugador].send_json(message)
            except RuntimeError as e:
                print(f"Error al enviar mensaje al jugador {id_jugador}: {e}")
                self.disconnect(id_jugador)

    async def send_text(self, id_jugador: int, message: str):
        # Envía texto plano a un cliente específico
        if id_jugador in self.active_connections:
            try:
                await self.active_connections[id_jugador].send_text(message)
            except RuntimeError as e:
                print(f"Error al enviar mensaje al jugador {id_jugador}: {e}")
                self.disconnect(id_jugador)

    async def broadcast(self, message: str):
        # Envía un mensaje a todos los clientes conectados (con id)
        for connection in list(self.active_connections.values()):
            await connection.send_text(message)

    # --- Manejo de salas por partida ---
    def join_room(self, partida_id: int, websocket: WebSocket):
        if partida_id not in self.rooms:
            self.rooms[partida_id] = []
        self.rooms[partida_id].append(websocket)

    def leave_room(self, partida_id: int, websocket: WebSocket):
        if partida_id in self.rooms:
            try:
                self.rooms[partida_id].remove(websocket)
            except ValueError:
                pass
            if not self.rooms[partida_id]:
                del self.rooms[partida_id]

    async def broadcast_to_partida(self, partida_id: int, message: Any):
        # Envía un mensaje a todos los websockets conectados a la sala de esa partida
        if partida_id not in self.rooms:
            return
        for ws in list(self.rooms[partida_id]):
            try:
                if isinstance(message, (dict, list)):
                    await ws.send_json(message)
                else:
                    await ws.send_text(str(message))
            except RuntimeError:
                # si falla, removemos esa conexión de la sala
                self.leave_room(partida_id, ws)



manager = ConnectionManager()

# Endpoint WebSocket
@ws_router.websocket("/ws/{id_jugador}")
async def websocket_endpoint(websocket: WebSocket, id_jugador: int):
    await manager.connect(id_jugador, websocket)
    try:
        while True:
            text = await websocket.receive_text()
            print(f"Mensaje recibido de {id_jugador}: {text}")
            # Ejemplo de eco
            await manager.send_message({"evento": "echo", "data": text}, id_jugador)
            # También broadcasteamos el texto a todos los jugadores conectados
            await manager.broadcast(text)
    except WebSocketDisconnect:
        manager.disconnect(id_jugador)

# Endpoint WebSocket por partida (sala)
@ws_router.websocket("/ws/partida/{partida_id}")
async def websocket_partida_endpoint(websocket: WebSocket, partida_id: int):
    # Aceptamos y agregamos la conexión a la sala correspondiente
    await websocket.accept()
    manager.join_room(partida_id, websocket)
    try:
        while True:
            # Podemos leer mensajes entrantes si los usamos; por ahora, ignoramos o logueamos
            data = await websocket.receive_text()
            print(f"WS sala {partida_id} recibió: {data}")
            # No reenviamos nada por defecto
    except WebSocketDisconnect:
        manager.leave_room(partida_id, websocket)
