# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="PISST API",
    description="Plataforma Integral de Seguridad y Salud en el Trabajo",
    version="1.0.0"
)

# CORS: permite que el frontend llame a esta API desde otro dominio
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # URL del frontend en desarrollo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoint de prueba para verificar que la API está viva
@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "proyecto": "PISST", "version": "1.0.0"}