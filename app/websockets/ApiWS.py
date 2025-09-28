from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Any
import json

# Creamos el router para agrupar las rutas WebSocket
ws_router = APIRouter()

# Clase para manejar las conexiones activas
class ConnectionManager:
    def __init__(self):
        # Hace una lista vacia donde van a ir los clientes conectados
        self.active_connections: Dict[int, WebSocket] = {}

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
