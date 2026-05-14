# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.routers import auth_router
from app.routers import chat_router
from app.routers import incidente_router
from app.routers import capacitacion_router
from app.routers import metricas_router

load_dotenv()

app = FastAPI(
    title="PISST API",
    description="Plataforma Integral de Seguridad y Salud en el Trabajo",
    version="1.0.0"
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS: permite que el frontend llame a esta API desde otro dominio
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # URL del frontend en desarrollo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(chat_router.router)
app.include_router(incidente_router.router)
app.include_router(capacitacion_router.router)
app.include_router(metricas_router.router)

# Endpoint de prueba para verificar que la API está viva
@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "proyecto": "PISST", "version": "1.0.0"}