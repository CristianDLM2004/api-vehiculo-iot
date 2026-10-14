import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from app.models.schemas import MovimientoPost, DemoPost
from app.services.iot_service import IoTService
from app.services.ws_manager import ws_manager

router = APIRouter()
iot_service = IoTService()

# Diccionario para controlar si una DEMO está corriendo y permitir cancelarla
demos_activas = {}

@router.post("/vehiculos/{id_vehiculo}/movimientos", status_code=201, summary="Registra un movimiento individual")
async def registrar_movimiento(id_vehiculo: int, movimiento: MovimientoPost):
    if id_vehiculo != movimiento.id_vehiculo:
        raise HTTPException(status_code=400, detail="ID del vehículo no coincide.")
    
    try:
        resultado = iot_service.registrar_movimiento_individual(
            id_vehiculo, movimiento.id_comando, movimiento.conectado, movimiento.origen
        )
        # Notificar a los clientes conectados por WebSocket
        await ws_manager.broadcast(id_vehiculo, {
            "evento": "MOVIMIENTO_INDIVIDUAL",
            "id_comando": movimiento.id_comando,
            "origen": movimiento.origen,
            "timestamp": datetime.now().isoformat()
        })
        return resultado
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/vehiculos/{id_vehiculo}/historial", summary="Obtiene los últimos 10 movimientos")
def obtener_historial(id_vehiculo: int):
    try:
        return {"id_vehiculo": id_vehiculo, "historial": iot_service.obtener_historial_limitado(id_vehiculo)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ZONA WEBSOCKET Y DEMO ---

@router.websocket("/vehiculos/{id_vehiculo}/ws")
async def websocket_endpoint(websocket: WebSocket, id_vehiculo: int):
    await ws_manager.connect(websocket, id_vehiculo)
    
    # Enviar último estado al conectarse (Regla de la práctica)
    estado_actual = iot_service.obtener_ultimo_estado(id_vehiculo)
    if estado_actual:
        # PARCHE: Convertir la fecha de MySQL a texto para que no rompa el JSON
        if estado_actual.get('fecha_actualizacion'):
            estado_actual['fecha_actualizacion'] = str(estado_actual['fecha_actualizacion'])
        await websocket.send_json({"evento": "ESTADO_INICIAL", "datos": estado_actual})
    
    try:
        while True:
            # Escuchar si el cliente manda un comando de "CANCELAR"
            data = await websocket.receive_text()
            if data == "CANCELAR":
                demos_activas[id_vehiculo] = True # Activamos la bandera de cancelación
                await ws_manager.broadcast(id_vehiculo, {"evento": "CANCELACION", "mensaje": "DEMO abortada."})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, id_vehiculo)

async def ejecutar_secuencia_demo(id_vehiculo: int, id_demo: int):
    """Ejecuta los movimientos de la DEMO leyendo los tiempos desde RDS."""
    movimientos = iot_service.obtener_movimientos_demo(id_demo)
    if not movimientos:
        return

    demos_activas[id_vehiculo] = False # False significa "corriendo sin cancelar"
    await ws_manager.broadcast(id_vehiculo, {"evento": "INICIO_DEMO", "total_movimientos": len(movimientos)})

    for mov in movimientos:
        if demos_activas.get(id_vehiculo) == True: # Alguien canceló
            break
            
        iot_service.actualizar_solo_estado(id_vehiculo, mov['id_comando'])
        
        await ws_manager.broadcast(id_vehiculo, {
            "evento": "MOVIMIENTO_DEMO",
            "comando": mov['comando'],
            "duracion_ms": mov['duracion_ms'],
            "pausa_ms": mov['pausa_ms']
        })
        
        # Ejecutar tiempos (ms a segundos)
        await asyncio.sleep(mov['duracion_ms'] / 1000.0)
        await asyncio.sleep(mov['pausa_ms'] / 1000.0)

    if demos_activas.get(id_vehiculo) != True:
        await ws_manager.broadcast(id_vehiculo, {"evento": "FIN_DEMO"})
    
    demos_activas.pop(id_vehiculo, None)

@router.post("/vehiculos/{id_vehiculo}/demos/{id_demo}/iniciar", summary="Inicia una secuencia DEMO")
async def iniciar_demo(id_vehiculo: int, id_demo: int, background_tasks: BackgroundTasks):
    if id_vehiculo in demos_activas and demos_activas[id_vehiculo] == False:
        raise HTTPException(status_code=409, detail="Ya hay una DEMO en curso para este vehículo.")
    
    # Arranca la tarea asíncrona y devuelve la respuesta HTTP inmediatamente
    background_tasks.add_task(ejecutar_secuencia_demo, id_vehiculo, id_demo)
    return {"status": "success", "mensaje": "DEMO iniciada. Monitorear movimientos por WebSocket."}