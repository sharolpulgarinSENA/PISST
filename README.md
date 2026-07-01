# PISST — Plataforma Integral de Seguridad y Salud en el Trabajo

Backend desarrollado con FastAPI + SQLAlchemy + PostgreSQL (Neon).

---

## Requisitos previos

- Python 3.11 o superior
- Git
- Acceso a una base de datos PostgreSQL (el proyecto usa Neon en producción)

---

## Instalación local (primera vez)

### 1. Clonar el repositorio y ubicarse en la rama de desarrollo

```bash
git checkout Dev
git pull origin Dev
```

### 2. Crear y activar el entorno virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Copia el archivo de ejemplo y completa los valores:

```bash
cp .env.example .env
```

Abre `.env` y configura al menos estas variables obligatorias:

```
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
SECRET_KEY=cualquier-cadena-aleatoria-larga
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=development
FRONTEND_URL=http://localhost:5173
ADMIN_SECRET_KEY=otra-cadena-aleatoria
```

> Las variables de Gemini, Resend, reCAPTCHA y Cloudinary son opcionales para correr el servidor localmente. Sin ellas, el SASBOT y el envío de correos no funcionarán.

### 5. Aplicar migraciones a la base de datos

```bash
alembic upgrade head
```

> `alembic init migrations` y `alembic revision` ya fueron ejecutados. No volver a correrlos.

### 6. Iniciar el servidor

```bash
uvicorn main:app --reload
```

El servidor queda disponible en: `http://localhost:8000`

Documentación interactiva (Swagger): `http://localhost:8000/docs`

---

## Producción

- **Backend:** Render — despliega automáticamente desde la rama `main`
- **Frontend:** Vercel
- **Base de datos:** Neon (PostgreSQL serverless)
- **URL producción:** https://app.pisst.online

---

## Estructura del proyecto

```
PISST/
│
├── app/                          # Código fuente principal
│   ├── core/
│   │   ├── database.py           # Conexión SQLAlchemy a Neon, función get_db
│   │   ├── security.py           # JWT (crear/decodificar), bcrypt, validación de contraseña
│   │   └── deps.py               # get_current_user, require_role, require_api_key
│   ├── models/                   # 17 modelos SQLAlchemy (tablas de BD)
│   ├── schemas/                  # DTOs Pydantic: validan entrada y serializan salida
│   ├── routers/                  # 13 routers FastAPI (endpoints HTTP)
│   └── services/                 # Lógica de negocio, generación de PDF/Excel
│
├── docs/                         # Documentación técnica del proyecto
│   ├── DOCUMENTACION_TECNICA.md  # Referencia técnica completa (sprints, endpoints, BD)
│   ├── RESUMEN_PROYECTO.md       # Resumen ejecutivo del backend
│   ├── sustentacion_backend_pisst.md   # Guía de sustentación técnica
│   └── simulacro_sustentacion_pisst.md # 27 preguntas con respuestas para practicar
│
├── migrations/                   # Migraciones Alembic (21 en cadena lineal)
│   └── versions/                 # Archivos de migración por sprint
│
├── notebooks/                    # Jupyter Notebooks de analítica de datos
│   ├── 01_exploracion_incidentes.ipynb
│   ├── 02_exploracion_riesgos.ipynb
│   └── 03_exploracion_capacitaciones.ipynb
│
├── tests/                        # 26 archivos de tests, 440 tests
│
├── data/                         # Datos procesados por los notebooks (ignorado por git)
│
├── main.py                       # Punto de entrada: app FastAPI, middlewares, routers
├── requirements.txt              # Dependencias Python del proyecto
├── runtime.txt                   # Versión de Python para Render (python-3.11.0)
├── render.yaml                   # Configuración de despliegue en Render (infra como código)
├── alembic.ini                   # Configuración de Alembic para migraciones
├── pytest.ini                    # Configuración de pytest (pythonpath, testpaths)
├── .flake8                       # Reglas de linting (max-line-length, exclusiones)
├── .pre-commit-config.yaml       # Hooks pre-commit: black, isort, flake8
├── docker-compose.yml            # PostgreSQL local para desarrollo sin Neon
├── CONTRIBUTING.md               # Guía de contribución: convenciones de migraciones y ramas
├── .env.example                  # Plantilla de variables de entorno (sin valores reales)
├── .env                          # Variables de entorno reales — NUNCA se sube a git
├── seed.py                       # Script para poblar la BD con datos de prueba
│
│   ── Generados automáticamente (ignorados por git) ──
├── venv/                         # Entorno virtual Python
├── htmlcov/                      # Reporte HTML de cobertura (pytest --cov)
├── test.db                       # Base de datos SQLite generada por los tests
└── .coverage                     # Archivo binario de cobertura de pytest
```

---

## Ramas

| Rama | Propósito |
|---|---|
| `barner-acosta` | Desarrollo principal |
| `Dev` | Integración — rama base para PRs |
| `main` | Producción — Render despliega desde aquí |
