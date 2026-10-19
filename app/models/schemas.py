from typing import Optional
from pydantic import BaseModel, Field

class MovimientoPost(BaseModel):
    id_vehiculo: int = Field(..., example=1)
    id_comando: int = Field(..., example=10)
    conectado: bool = Field(True, example=True)
    origen: str = Field("API_LOCAL", example="API_LOCAL")

class DemoPost(BaseModel):
    id_vehiculo: int = Field(..., example=1)
    id_demo: int = Field(..., example=1)

# --- MODELOS PARA EL CRUD CON EJEMPLOS ---

class VehiculoSchema(BaseModel):
    nombre: str = Field(..., example="Excavadora IoT 2.0")
    modelo: Optional[str] = Field(None, example="Modelo Z")
    descripcion: Optional[str] = Field(None, example="Vehículo de pruebas de carga")
    microcontrolador: Optional[str] = Field(None, example="ESP32")
    activo: bool = Field(True, example=True)

class ComandoSchema(BaseModel):
    nombre: str = Field(..., example="ENCENDER_LUCES")
    codigo: int = Field(..., example=10)
    descripcion: Optional[str] = Field(None, example="Enciende los faros delanteros")
    activo: bool = Field(True, example=True)

class DemoSchema(BaseModel):
    nombre: str = Field(..., example="Modo Patrulla")
    descripcion: Optional[str] = Field(None, example="Secuencia automática de vigilancia")
    activo: bool = Field(True, example=True)