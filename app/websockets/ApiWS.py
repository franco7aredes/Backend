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
        # Salas por partida: cada partida_id tiene múltiples websockets suscritos (tableros)
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

    async def broadcast(self, message: str):
        # Envía un mensaje a todos los clientes conectados (con id)
        for connection in list(self.active_connections.values()):
            await connection.send_text(message)

    # ---- Manejo de salas por partida ----
    async def join_room(self, partida_id: int, websocket: WebSocket):
        await websocket.accept()
        self.rooms.setdefault(partida_id, []).append(websocket)
        print(f"WS unido a sala partida {partida_id}. Conexiones: {len(self.rooms[partida_id])}")

    def leave_room(self, partida_id: int, websocket: WebSocket | None):
        if partida_id in self.rooms and websocket is not None:
            try:
                self.rooms[partida_id].remove(websocket)
                if not self.rooms[partida_id]:
                    del self.rooms[partida_id]
            except ValueError:
                pass

    async def broadcast_to_partida(self, partida_id: int, message: Dict[str, Any]):
        # Envía JSON a todos los sockets suscritos a la sala de esa partida
        if partida_id not in self.rooms:
            return
        dead: List[WebSocket] = []
        for ws in list(self.rooms.get(partida_id, [])):
            try:
                await ws.send_json(message)
            except RuntimeError as e:
                print(f"Error al enviar a sala {partida_id}: {e}")
                dead.append(ws)
        for ws in dead:
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


# WS de sala por partida, para notificar eventos del tablero
@ws_router.websocket("/ws/partida/{partida_id}")
async def websocket_partida_room(websocket: WebSocket, partida_id: int):
    await manager.join_room(partida_id, websocket)
    try:
        while True:
            # podemos aceptar pings/mensajes del cliente si hace falta
            _ = await websocket.receive_text()
            # actualmente ignoramos los mensajes del cliente para esta sala
    except WebSocketDisconnect:
        manager.leave_room(partida_id, websocket)
