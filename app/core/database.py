# app/core/database.py
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()  # carga las variables del archivo .env

DATABASE_URL = os.getenv("DATABASE_URL")

# pool_pre_ping=True → verifica la conexión antes de usarla
# pool_recycle=300  → renueva conexiones cada 5 minutos
# sslmode=require   → Neon siempre requiere SSL
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"sslmode": "require"},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
