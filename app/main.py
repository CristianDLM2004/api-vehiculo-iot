from fastapi import FastAPI
from app.routes.api import router

app = FastAPI(
    title="API Vehículo IoT",
    description="API local conectada a Amazon RDS para la gestión de vehículos IoT y WebSockets.",
    version="1.0"
)

# Incluimos las rutas que acabas de crear
app.include_router(router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    # Se ejecuta exclusivamente en localhost:8000 como pide la práctica
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)