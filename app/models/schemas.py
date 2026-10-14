from pydantic import BaseModel

class MovimientoPost(BaseModel):
    id_vehiculo: int
    id_comando: int
    conectado: bool = True
    origen: str = "API_LOCAL"

class DemoPost(BaseModel):
    id_vehiculo: int
    id_demo: int