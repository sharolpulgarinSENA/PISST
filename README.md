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
app/
  core/        # Configuración, base de datos, dependencias, seguridad
  models/      # Modelos SQLAlchemy
  schemas/     # Schemas Pydantic
  routers/     # Endpoints FastAPI
  services/    # Lógica de negocio y generación de PDFs
migrations/    # Migraciones Alembic
main.py        # Punto de entrada
```

---

## Ramas

| Rama | Propósito |
|---|---|
| `barner-acosta` | Desarrollo principal |
| `Dev` | Integración — rama base para PRs |
| `main` | Producción — Render despliega desde aquí |
