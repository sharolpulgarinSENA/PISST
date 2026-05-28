# main.py
import os
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
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
from app.routers import riesgo_router
from app.routers import auditoria_router
from app.routers import usuario_router
from app.routers import admin_router
from app.routers.area_router import router as area_router
from app.routers.cargo_router import router as cargo_router

load_dotenv()

_REQUIRED_ENV = ["DATABASE_URL", "SECRET_KEY", "GEMINI_API_KEY", "RESEND_API_KEY"]
_missing = [v for v in _REQUIRED_ENV if not os.getenv(v)]
if _missing:
    raise RuntimeError(f"Variables de entorno faltantes: {_missing}")

_dev = os.getenv("ENVIRONMENT") == "development"

app = FastAPI(
    title="PISST API",
    description="Plataforma Integral de Seguridad y Salud en el Trabajo",
    version="1.0.0",
    docs_url="/docs" if _dev else None,
    redoc_url="/redoc" if _dev else None,
    openapi_url="/openapi.json" if _dev else None,
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://pisst-frontend.vercel.app",
    os.getenv("FRONTEND_URL", ""),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in origins if o],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(chat_router.router)
app.include_router(incidente_router.router)
app.include_router(capacitacion_router.router)
app.include_router(metricas_router.router)
app.include_router(riesgo_router.router)
app.include_router(auditoria_router.router)
app.include_router(usuario_router.router)
app.include_router(admin_router.router)
app.include_router(area_router)
app.include_router(cargo_router)

@app.get("/", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected", "proyecto": "PISST", "version": "1.0.0"}
    except Exception:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
