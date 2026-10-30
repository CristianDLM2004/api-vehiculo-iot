from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from app.routes.api import router
import os

# 1. Desactivamos el docs_url por defecto para poder personalizarlo
app = FastAPI(
    title="API Vehículo IoT",
    description="API conectada a Amazon RDS para la gestión de vehículos IoT y WebSockets.",
    version="1.0",
    docs_url=None 
)

# 2. Escudo CORS abierto
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Incluimos las rutas del CRUD y WebSockets que ya tenías
app.include_router(router, prefix="/api")

# 4. Montar la carpeta "webapp" para servir la página web
# Verificamos que la carpeta exista para que Uvicorn no arroje error al arrancar
os.makedirs("webapp", exist_ok=True) 
app.mount("/control", StaticFiles(directory="webapp", html=True), name="webapp")

# 5. Sobrescribir Swagger UI para inyectar el botón interactivo
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    # Generamos el HTML original de Swagger
    swagger_html = get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=app.title + " - Swagger UI"
    ).body.decode("utf-8")
    
    # Inyectamos un botón flotante estilizado justo antes de cerrar la etiqueta body
    boton_flotante = """
    <style>
        .btn-control-2d {
            position: fixed;
            top: 13px;
            right: 250px;
            z-index: 9999;
            background-color: #e69c24;
            color: #1a1a1a;
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: 900;
            text-decoration: none;
            font-family: sans-serif;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            transition: transform 0.2s, background-color 0.2s;
            border: 2px solid #b87a1c;
        }
        .btn-control-2d:hover {
            transform: scale(1.05);
            background-color: #f5b041;
        }
    </style>
    <a href="/control" target="_blank" class="btn-control-2d">🎮 Modo Control 2D</a>
    </body>
    """
    custom_html = swagger_html.replace("</body>", boton_flotante)
    return HTMLResponse(custom_html)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)