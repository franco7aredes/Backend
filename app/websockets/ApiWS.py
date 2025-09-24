from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# Creamos el router para agrupar las rutas WebSocket
ws_router = APIRouter()

# Clase para manejar las conexiones activas
class ConnectionManager:
    def __init__(self):
        # Hace una lista vacia donde van a ir los clientes conectados
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        # Acepta la conexión y la agrega a la lista
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        # Elimina la conexión de la lista
        self.active_connections.remove(websocket)

    async def send_message(self, message: str, websocket: WebSocket):
        # Envía un mensaje a un cliente específico
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        # Envía un mensaje a todos los clientes conectados
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()

# Endpoint WebSocket
@ws_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            text = await websocket.receive_text()
            print(f"Mensaje recibido de {websocket}: {text}")
            await manager.broadcast(text)  # Probablemente se modificara en un futuro esto.
    except WebSocketDisconnect:
        manager.disconnect(websocket)
