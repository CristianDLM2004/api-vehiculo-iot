from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        # Diccionario para agrupar clientes por id_vehiculo: {1: [ws1, ws2], 2: [ws3]}
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, id_vehiculo: int):
        await websocket.accept()
        if id_vehiculo not in self.active_connections:
            self.active_connections[id_vehiculo] = []
        self.active_connections[id_vehiculo].append(websocket)

    def disconnect(self, websocket: WebSocket, id_vehiculo: int):
        if id_vehiculo in self.active_connections:
            if websocket in self.active_connections[id_vehiculo]:
                self.active_connections[id_vehiculo].remove(websocket)

    async def broadcast(self, id_vehiculo: int, message: dict):
        """Envía un mensaje JSON a todos los clientes conectados a un vehículo específico."""
        if id_vehiculo in self.active_connections:
            desconectados = []
            for connection in self.active_connections[id_vehiculo]:
                try:
                    await connection.send_json(message)
                except Exception:
                    desconectados.append(connection)
            for c in desconectados:
                self.disconnect(c, id_vehiculo)

ws_manager = ConnectionManager()