# alembic/env.py
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

load_dotenv()

# Importar todos los modelos para que Alembic los detecte
from app.core.database import Base
from app.models import user
from app.models import area
from app.models import cargo
from app.models import empresa
from app.models import chat_historial
from app.models import incidente
from app.models import investigacion
from app.models import lesion
from app.models import testigo
from app.models import accion_correctiva
from app.models import capacitacion
from app.models import riesgo
from app.models import auditoria

config = context.config

# Sobrescribir la URL de la BD con la del .env
db_url = os.getenv("DATABASE_URL", "").replace("postgresql://", "postgresql+psycopg2://")
config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

