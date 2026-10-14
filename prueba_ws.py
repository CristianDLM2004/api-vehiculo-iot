import asyncio
import websockets
import json

async def escuchar_demo():
    uri = "ws://127.0.0.1:8000/api/vehiculos/1/ws"
    try:
        async with websockets.connect(uri) as websocket:
            print("🟢 ¡Conectado al WebSocket del Vehículo 1!")
            while True:
                mensaje = await websocket.recv()
                datos = json.loads(mensaje)
                # Imprime el JSON con indentación para que se vea claro
                print(f"📩 {json.dumps(datos, indent=2)}")
    except Exception as e:
        print(f"🔴 Error: {e}")

asyncio.run(escuchar_demo())