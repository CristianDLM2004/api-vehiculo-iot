import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from app.models.schemas import MovimientoPost, DemoPost, VehiculoSchema, ComandoSchema, DemoSchema
from app.services.iot_service import IoTService
from app.services.ws_manager import ws_manager

router = APIRouter()
iot_service = IoTService()
demos_activas = {}

# ==================== VEHÍCULOS ====================
@router.get("/vehiculos", tags=["Vehículos"], summary="Obtener todos los vehículos")
def get_vehiculos():
    return iot_service.obtener_vehiculos()

@router.get("/vehiculos/{id_vehiculo}", tags=["Vehículos"], summary="Obtener un vehículo")
def get_vehiculo(id_vehiculo: int):
    return iot_service.obtener_vehiculo(id_vehiculo)

@router.post("/vehiculos", tags=["Vehículos"], summary="Crear un vehículo")
def post_vehiculo(data: VehiculoSchema):
    return iot_service.crear_vehiculo(data.nombre, data.modelo, data.descripcion, data.microcontrolador)

@router.put("/vehiculos/{id_vehiculo}", tags=["Vehículos"], summary="Actualizar vehículo")
def put_vehiculo(id_vehiculo: int, data: VehiculoSchema):
    return iot_service.actualizar_vehiculo(id_vehiculo, data.nombre, data.modelo, data.descripcion, data.microcontrolador, data.activo)

@router.delete("/vehiculos/{id_vehiculo}", tags=["Vehículos"], summary="Eliminar vehículo")
def delete_vehiculo(id_vehiculo: int):
    return iot_service.eliminar_vehiculo(id_vehiculo)

# ==================== COMANDOS ====================
@router.get("/vehiculos/{id_vehiculo}/comandos", tags=["Comandos"], summary="Ver comandos de un vehículo")
def get_comandos(id_vehiculo: int):
    return iot_service.obtener_comandos_vehiculo(id_vehiculo)

@router.post("/vehiculos/{id_vehiculo}/comandos", tags=["Comandos"], summary="Agregar comando")
def post_comando(id_vehiculo: int, data: ComandoSchema):
    return iot_service.crear_comando(id_vehiculo, data.nombre, data.codigo, data.descripcion)

@router.put("/comandos/{id_comando}", tags=["Comandos"], summary="Actualizar comando")
def put_comando(id_comando: int, data: ComandoSchema):
    return iot_service.actualizar_comando(id_comando, data.nombre, data.codigo, data.descripcion, data.activo)

@router.delete("/comandos/{id_comando}", tags=["Comandos"], summary="Eliminar comando")
def delete_comando(id_comando: int):
    return iot_service.eliminar_comando(id_comando)

# ==================== ESTADO E HISTORIAL ====================
@router.get("/vehiculos/{id_vehiculo}/estado", tags=["Estado e Historial"], summary="Ver estado actual")
def get_estado(id_vehiculo: int):
    return iot_service.obtener_estado(id_vehiculo)

@router.get("/vehiculos/{id_vehiculo}/historial", tags=["Estado e Historial"], summary="Ver historial (Max 10)")
def get_historial(id_vehiculo: int):
    return {"id_vehiculo": id_vehiculo, "historial": iot_service.obtener_historial_limitado(id_vehiculo)}

@router.post("/vehiculos/{id_vehiculo}/movimientos", tags=["Estado e Historial"], status_code=201, summary="Registrar movimiento individual")
async def registrar_movimiento(id_vehiculo: int, mov: MovimientoPost):
    if id_vehiculo != mov.id_vehiculo: raise HTTPException(400, "ID no coincide")
    try:
        res = iot_service.registrar_movimiento_individual(id_vehiculo, mov.id_comando, mov.conectado, mov.origen)
        await ws_manager.broadcast(id_vehiculo, {"evento": "MOV_INDIVIDUAL", "id_comando": mov.id_comando, "origen": mov.origen})
        return res
    except Exception as e: raise HTTPException(500, str(e))

# ==================== DEMOS Y MOVIMIENTOS ====================
@router.get("/vehiculos/{id_vehiculo}/demos", tags=["Demos"], summary="Ver demos del vehículo")
def get_demos(id_vehiculo: int):
    return iot_service.obtener_demos(id_vehiculo)

@router.post("/vehiculos/{id_vehiculo}/demos", tags=["Demos"], summary="Crear demo")
def post_demo(id_vehiculo: int, data: DemoSchema):
    return iot_service.crear_demo(id_vehiculo, data.nombre, data.descripcion)

@router.put("/demos/{id_demo}", tags=["Demos"], summary="Actualizar demo")
def put_demo(id_demo: int, data: DemoSchema):
    return iot_service.actualizar_demo(id_demo, data.nombre, data.descripcion, data.activo)

@router.delete("/demos/{id_demo}", tags=["Demos"], summary="Eliminar demo")
def delete_demo(id_demo: int):
    return iot_service.eliminar_demo(id_demo)

@router.get("/demos/{id_demo}/movimientos", tags=["Demos"], summary="Ver secuencia de una demo")
def get_mov_demos(id_demo: int):
    return iot_service.obtener_movimientos_demo(id_demo)

# Nota: Para este post de movimientos de Demo, por simplicidad para la demostración
# dejaremos los parámetros directos en la función, para evitar crear un modelo adicional.
@router.post("/demos/{id_demo}/movimientos", tags=["Demos"], summary="Agregar paso a demo")
def post_mov_demo(id_demo: int, id_comando: int, orden: int, duracion_ms: int, pausa_ms: int = 0):
    return iot_service.agregar_movimiento_demo(id_demo, id_comando, orden, duracion_ms, pausa_ms)

@router.put("/demo_movimientos/{id_mov}", tags=["Demos"], summary="Actualizar paso")
def put_mov_demo(id_mov: int, id_comando: int, orden: int, duracion_ms: int, pausa_ms: int = 0):
    return iot_service.actualizar_movimiento_demo(id_mov, id_comando, orden, duracion_ms, pausa_ms)

@router.delete("/demo_movimientos/{id_mov}", tags=["Demos"], summary="Eliminar paso")
def delete_mov_demo(id_mov: int):
    return iot_service.eliminar_movimiento_demo(id_mov)

# ==================== WEBSOCKET Y EJECUCIÓN DEMO ====================
@router.websocket("/vehiculos/{id_vehiculo}/ws")
async def websocket_endpoint(websocket: WebSocket, id_vehiculo: int):
    await ws_manager.connect(websocket, id_vehiculo)
    estado = iot_service.obtener_estado(id_vehiculo)
    if estado:
        if estado.get('fecha_actualizacion'): estado['fecha_actualizacion'] = str(estado['fecha_actualizacion'])
        await websocket.send_json({"evento": "ESTADO_INICIAL", "datos": estado})
    try:
        while True:
            if await websocket.receive_text() == "CANCELAR":
                demos_activas[id_vehiculo] = True
                await ws_manager.broadcast(id_vehiculo, {"evento": "CANCELADO", "msg": "Demo abortada"})
    except WebSocketDisconnect: ws_manager.disconnect(websocket, id_vehiculo)

async def ejecutar_secuencia_demo(id_vehiculo: int, id_demo: int):
    movs = iot_service.obtener_movimientos_demo(id_demo)
    if not movs: return
    demos_activas[id_vehiculo] = False
    await ws_manager.broadcast(id_vehiculo, {"evento": "INICIO_DEMO", "total": len(movs)})
    for mov in movs:
        if demos_activas.get(id_vehiculo): break
        iot_service.actualizar_solo_estado(id_vehiculo, mov['id_comando'])
        await ws_manager.broadcast(id_vehiculo, {"evento": "MOV_DEMO", "comando": mov['comando'], "duracion_ms": mov['duracion_ms'], "pausa_ms": mov['pausa_ms']})
        await asyncio.sleep((mov['duracion_ms'] + mov['pausa_ms']) / 1000.0)
    if not demos_activas.get(id_vehiculo): await ws_manager.broadcast(id_vehiculo, {"evento": "FIN_DEMO"})
    demos_activas.pop(id_vehiculo, None)

@router.post("/vehiculos/{id_vehiculo}/demos/{id_demo}/iniciar", tags=["Ejecución en Tiempo Real"], summary="Iniciar DEMO por WebSocket")
async def iniciar_demo(id_vehiculo: int, id_demo: int, bg_tasks: BackgroundTasks):
    if demos_activas.get(id_vehiculo) is False: raise HTTPException(409, "Demo ya en curso")
    bg_tasks.add_task(ejecutar_secuencia_demo, id_vehiculo, id_demo)
    return {"status": "success", "mensaje": "Demo iniciada en WebSocket."}