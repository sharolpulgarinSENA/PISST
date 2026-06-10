# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.models.audit_log import AuditLog  # noqa: F401 — registra tabla en metadata
from app.models.empresa import Empresa
from app.models.notificacion import (  # noqa: F401 — registra tabla en metadata
    Notificacion,
)
from app.models.user import RoleEnum, User

SQLALCHEMY_TEST_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    db = TestingSessionLocal()
    yield db
    db.rollback()
    db.close()


@pytest.fixture
def client(db):
    import os

    os.environ.setdefault("SECRET_KEY", "test-secret-key-para-tests-unitarios")
    os.environ.setdefault("GEMINI_API_KEY", "fake")
    os.environ.setdefault("RESEND_API_KEY", "fake")
    os.environ.setdefault("DATABASE_URL", SQLALCHEMY_TEST_URL)

    from main import app

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def empresa(db):
    import uuid as _uuid

    nit = str(_uuid.uuid4())[:12].replace("-", "")
    emp = Empresa(nombre="Empresa Test", nit=nit, sector="Pruebas")
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


@pytest.fixture
def usuario_sst(db, empresa):
    import uuid as _uuid

    email = f"sst_{_uuid.uuid4().hex[:8]}@test.com"
    user = User(
        nombre="SST Test",
        email=email,
        password_hash=get_password_hash("password123"),
        role=RoleEnum.sst,
        empresa_id=empresa.id,
        activo=True,
        debe_cambiar_password=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def usuario_admin(db):
    import uuid as _uuid

    email = f"admin_{_uuid.uuid4().hex[:8]}@test.com"
    user = User(
        nombre="Admin Test",
        email=email,
        password_hash=get_password_hash("Admin1!2345"),
        role=RoleEnum.admin,
        empresa_id=None,
        activo=True,
        debe_cambiar_password=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_headers(usuario_admin):
    import os

    os.environ.setdefault("SECRET_KEY", "test-secret-key-para-tests-unitarios")
    from app.core.security import create_access_token

    token = create_access_token({"sub": str(usuario_admin.id)})
    return {"Authorization": f"Bearer {token}"}
