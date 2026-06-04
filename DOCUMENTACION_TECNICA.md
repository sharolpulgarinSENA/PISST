# Documentación Técnica — PISST
## Plataforma Integral de Seguridad y Salud en el Trabajo
**Versión:** 1.5 | **Fecha:** 2026-06-04 | **Estado:** Producción

---

## Tabla de Contenidos

1. [Visión General](#1-visión-general)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Módulos del Sistema](#3-módulos-del-sistema)
4. [Stack Tecnológico](#4-stack-tecnológico)
5. [Seguridad](#5-seguridad)
6. [Guía de Desarrollo](#6-guía-de-desarrollo)
7. [API Reference](#7-api-reference)
8. [Historial de Cambios](#8-historial-de-cambios)

---

## 1. Visión General

### 1.1 ¿Qué es PISST?

PISST es una plataforma web integral diseñada para digitalizar y automatizar la gestión del **Sistema de Gestión de Seguridad y Salud en el Trabajo (SG-SST)** en empresas colombianas, en cumplimiento del **Decreto 1072 de 2015** y la **Resolución 0312 de 2019** del Ministerio del Trabajo.

El sistema centraliza en una sola plataforma:
- El reporte y seguimiento de incidentes laborales
- La generación del FURAT (Formulario Único de Reporte de Accidente de Trabajo)
- La gestión de riesgos y peligros ocupacionales
- El control de capacitaciones y evaluaciones del personal
- La planificación y ejecución de auditorías internas
- La generación de métricas, KPIs e informes ejecutivos en PDF y Excel
- Un asistente de IA (SASBOT) para orientación en SST

### 1.2 Contexto y Propósito

| Aspecto | Detalle |
|---|---|
| **Contexto** | Proyecto académico-empresarial desarrollado en el SENA |
| **Normativa aplicable** | Decreto 1072/2015, Resolución 0312/2019, Resolución 0156/2005 (FURAT) |
| **Problema que resuelve** | Eliminar la gestión manual en papel del SG-SST, reducir tiempos de respuesta ante incidentes y mejorar la trazabilidad de acciones correctivas |
| **Versión actual** | V1.4 |

### 1.3 Roles del Sistema y Matriz de Acceso

El sistema implementa **control de acceso basado en roles (RBAC)** con 4 niveles:

| Rol | Descripción | Acceso principal |
|---|---|---|
| `admin` | Administrador del sistema | Crear empresas, crear SST y Gerencia. Solo 1 SST y 1 Gerencia por empresa. |
| `sst` | Encargado de Seguridad y Salud en el Trabajo | Gestión completa de incidentes, riesgos, capacitaciones, auditorías y reportes |
| `gerencia` | Usuario de gerencia de la empresa | Consulta de dashboards, métricas, KPIs e informes ejecutivos |
| `empleado` | Trabajador de la empresa | Reporte de incidentes, participación en capacitaciones, uso del chat SASBOT |

**Reglas de creación de usuarios:**
- El `admin` crea el primer SST y el primer Gerencia de cada empresa (máximo 1 de cada uno por empresa)
- El `sst` crea únicamente empleados, asignándoles área y cargo

### 1.4 Estado Actual del Proyecto

- **Backend:** En producción en Render ✅
- **Frontend:** En producción en Vercel ✅
- **Base de datos:** Neon PostgreSQL (cloud) ✅
- **CI/CD:** GitHub Actions ejecutándose en cada push ✅
- **Tests automáticos:** 207 tests pasando al 100% ✅
- **Cobertura de código:** 91% ✅

---

## 2. Arquitectura del Sistema

### 2.1 Arquitectura General

```
┌─────────────────────────────────────────────────────────┐
│                     USUARIOS                            │
│         (Admin / SST / Gerencia / Empleado)             │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS
┌────────────────────────▼────────────────────────────────┐
│              FRONTEND (Vercel)                          │
│         Stack: [Sharon / Santiago]                      │
│         Dominio: pisst-frontend.vercel.app              │
│              app.pisst.online                           │
└────────────────────────┬────────────────────────────────┘
                         │ REST API / JSON
                         │ JWT Bearer Token
┌────────────────────────▼────────────────────────────────┐
│              BACKEND (Render)                           │
│              FastAPI + Python 3.12                      │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │ Routers  │→ │ Services │→ │ Models (SQLAlchemy) │  │
│  │ (HTTP)   │  │(Negocio) │  │ (ORM)              │  │
│  └──────────┘  └──────────┘  └────────────────────┘  │
│                                                         │
│  Integraciones externas:                                │
│  • Google Gemini AI (SASBOT)                            │
│  • Resend (correo transaccional)                        │
│  • Google reCAPTCHA v2                                  │
└────────────────────────┬────────────────────────────────┘
                         │ psycopg2 / SSL
┌────────────────────────▼────────────────────────────────┐
│           BASE DE DATOS (Neon PostgreSQL)               │
│           PostgreSQL 16 — Cloud serverless              │
│           Migraciones gestionadas con Alembic           │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Arquitectura por Capas (Backend)

El backend implementa una **arquitectura en capas estricta**:

```
HTTP Request
     │
┌─────────────┐
│   Routers   │  Capa de presentación: parseo de request, validación
│ (app/routers)│  de entrada con Pydantic, control de autenticación/roles,
│             │  serialización de respuesta con response_model
└───────┬─────┘
       │
┌─────────────┐
│  Services   │  Capa de negocio: toda la lógica de dominio,
│(app/services)│  reglas de negocio, orquestación de operaciones,
│             │  integración con servicios externos
└───────┬─────┘
       │
┌─────────────┐
│   Models    │  Capa de datos: definición de tablas con SQLAlchemy ORM,
│ (app/models)│  relaciones entre entidades, constraints e índices
└───────┬─────┘
       │
┌─────────────┐
│  PostgreSQL │  Base de datos relacional en Neon
│   (Neon)    │
└─────────────┘
```

Adicionalmente:
- **`app/schemas/`** → DTOs Pydantic para validación de entrada y serialización de salida
- **`app/core/`** → Infraestructura transversal: BD, seguridad, dependencias JWT
- **`app/services/`** → Toda la lógica de negocio separada de los routers (cada módulo tiene su propio servicio)

### 2.3 Flujo de Autenticación

```
1. Login (POST /auth/login)
   ├─ Verifica reCAPTCHA
   ├─ Verifica credenciales
   ├─ Controla intentos fallidos (bloqueo temporal a los 5 intentos)
   └─ Genera access_token (JWT, 30 min) + refresh_token (7 días)

2. Uso de endpoints protegidos
   ├─ Extrae y valida JWT del header Authorization: Bearer <token>
   ├─ Verifica rol del usuario con require_role()
   ├─ Verifica session_token activo en BD (sesión única por usuario)
   └─ Verifica que el usuario deba cambiar contraseña (primer login)

3. Renovación de sesión (POST /auth/refresh)
   ├─ Valida refresh_token en BD
   └─ Genera nuevo access_token sin pedir login

4. Cierre de sesión (POST /auth/logout)
   └─ Invalida refresh_token y session_token en BD

5. Cambiar contraseña (POST /auth/cambiar-password)
   ├─ Valida JWT (incluyendo session_token — no usa get_current_user
   │  para permitir el cambio cuando debe_cambiar_password=True)
   └─ Verifica contraseña actual antes de actualizar
```

### 2.4 Modelo de Multitenencia

El sistema es **multi-tenant por empresa**. Cada entidad del dominio está ligada a una `empresa_id`. Todas las queries filtran por empresa antes de retornar datos, garantizando el **aislamiento completo entre empresas**.

---

## 3. Módulos del Sistema

### 3.1 Autenticación y Usuarios

**Endpoints:** `/auth/*`, `/usuarios/*`

| Funcionalidad | Detalle |
|---|---|
| Login con JWT | Access token (30 min) + Refresh token (7 días). La respuesta incluye `debe_cambiar_password` para que el frontend redirija sin esperar un 403 |
| Cambio de contraseña obligatorio | Primer login fuerza cambio de contraseña temporal. El flag aplica a todos los roles creados por el admin (SST, Gerencia) y por el SST (empleados) |
| Bloqueo por intentos | 5 intentos fallidos → bloqueo 5 minutos |
| Recuperación de contraseña | Token por correo, expira en 30 minutos |
| Validación de contraseña | Mínimo 8 caracteres, mayúscula, minúscula, número y símbolo |
| Logout real | Invalida refresh y session token en BD |
| Gestión de empleados | SST crea empleados con área y cargo asignados |
| Sesión única | Cada login invalida la sesión anterior; session_token validado en cada request |
| Filtro de usuarios | `GET /usuarios/?activo=true\|false` filtra por estado; sin parámetro devuelve todos |
| Nombres en respuesta | `GET /usuarios/` incluye `area_nombre` y `cargo_nombre` listos para el frontend |

### 3.2 Gestión de Incidentes y FURAT

**Endpoints:** `/incidentes/*`

Ciclo de vida de un incidente:
```
borrador → en_revision → abierto → en_investigacion → cerrado
```

| Funcionalidad | Detalle |
|---|---|
| Tipos de incidente | accidente, incidente, cuasi_accidente, condicion_insegura |
| Niveles de severidad | sin_lesion, leve, moderada, grave, mortal |
| Registro de lesiones | Tipo de lesión, parte afectada, días de incapacidad |
| Testigos | Registro de testigos con nombre y relato |
| Investigación de causas | Método 5 Por Qué, causas inmediatas, básicas y lecciones aprendidas |
| Acciones correctivas | Seguimiento con fecha límite, responsable y evidencia de cierre |
| FURAT en PDF | Generación automática del formulario oficial |
| Progreso | Porcentaje de acciones correctivas completadas |

### 3.3 Riesgos y Peligros

**Endpoints:** `/riesgos/*`

| Funcionalidad | Detalle |
|---|---|
| Tipos de peligro | Físico, químico, biológico, ergonómico, psicosocial, locativo |
| Evaluación de riesgo | Probabilidad × Severidad → Nivel (bajo/medio/alto/crítico) |
| Evaluación residual | Verificación de riesgo tras aplicar controles |
| Medidas de control | Jerarquía: eliminación, sustitución, ingeniería, administrativo, EPP |
| Matriz de riesgos | Agrupamiento por nivel para visualización |

### 3.4 Capacitaciones y Evaluaciones

**Endpoints:** `/capacitaciones/*`

| Funcionalidad | Detalle |
|---|---|
| Programas de capacitación | Asociados a áreas de la empresa |
| Sesiones | Programación de fechas y lugar, reprogramación |
| Asistencia | Registro por empleado (presente/ausente/justificado) |
| Evaluaciones | Preguntas de opción múltiple con calificación automática |
| Certificados PDF | Generación automática al aprobar |
| Cobertura | Porcentaje del plan anual de capacitaciones cumplido |
| Filtro por estado | `GET /capacitaciones/` devuelve **todas** por defecto. `?activo=true` solo activas, `?activo=false` solo inactivas |

### 3.5 Auditorías Internas

**Endpoints:** `/auditorias/*`

Ciclo de vida:
```
planificada → en_ejecucion → completada
```

| Funcionalidad | Detalle |
|---|---|
| Planificación | Fecha, objetivos, área y auditor |
| Hallazgos | Clasificación: conformidad, NC menor, NC mayor, observación |
| No conformidades | Seguimiento con fecha límite y evidencia de cierre |
| Progreso | Porcentaje de no conformidades cerradas |

### 3.6 Métricas y Reportes Ejecutivos

**Endpoints:** `/metricas/*`

| Funcionalidad | Detalle |
|---|---|
| KPIs de seguridad | Tasa de accidentalidad, índice de frecuencia, índice de severidad |
| Dashboard gerencia | Cumplimiento SG-SST, incidentes activos, capacitaciones |
| Alertas inteligentes | Incidentes sin investigar, acciones vencidas |
| Reporte PDF ejecutivo | Tablas de KPIs y resumen por período |
| Reporte Excel ejecutivo | Mismo contenido exportado a .xlsx |
| Períodos | mensual / trimestral / anual |

### 3.7 Chat IA — SASBOT

**Endpoints:** `/chat/*`

| Funcionalidad | Detalle |
|---|---|
| Chat contextual | Respuestas personalizadas según cargo y área del empleado |
| Motor de IA | Google Gemini AI |
| Reporte rápido | Empleado reporta incidente directamente desde el chat |
| Historial | Historial de conversaciones paginado por usuario |
| Modo emergencia | Detección de palabras clave críticas con respuesta especial |

### 3.8 Analytics — Analítica Integrada

**Endpoints:** `/analytics/*`

Módulo de solo lectura que usa **Pandas** y **NumPy** sobre los datos existentes para generar KPIs avanzados y alertas. No toca ningún servicio existente ni escribe en la BD.

| Endpoint | Rol | Qué devuelve |
|---|---|---|
| `GET /analytics/incidentes` | sst, gerencia | Distribución por tipo y severidad, tasa mensual promedio, tendencia (aumento/baja/estable) |
| `GET /analytics/riesgos` | sst, gerencia | Distribución por nivel (bajo/medio/alto/crítico), % con medidas implementadas, peligros críticos sin control |
| `GET /analytics/capacitaciones` | sst, gerencia | Tasa de aprobación global, asistencia promedio, alertas de empleados con asistencia < 80%, capacitaciones sin sesión realizada |
| `GET /analytics/cumplimiento` | sst, gerencia | Score SG-SST (0–100) y desglose por módulo: incidentes investigados, peligros con control, capacitaciones realizadas, NC cerradas |

**Principios del módulo:**
- Estrictamente de solo lectura (`db.query()` únicamente — nunca `db.add/commit/delete`)
- Multi-tenant: toda query filtra por `empresa_id` del usuario autenticado
- No invasivo: un error en analytics no afecta el backend principal
- Reutiliza el mismo JWT/RBAC del resto del proyecto

---

### 3.9 Administración del Sistema

**Endpoints:** `/admin/*`

Protegidos con `X-Admin-Key` en el header.

| Funcionalidad | Detalle |
|---|---|
| Crear empresa | Registro de nueva empresa en el sistema |
| Crear SST | Un único SST por empresa |
| Crear Gerencia | Un único Gerencia por empresa |
| Listar empresas | Vista de todas las empresas registradas |
| Limpiar tokens | Limpia refresh tokens y sesiones caducadas del sistema |

---

## 4. Stack Tecnológico

### 4.1 Backend

| Componente | Tecnología | Versión |
|---|---|---|
| Lenguaje | Python | 3.12 |
| Framework web | FastAPI | 0.136.x |
| ORM | SQLAlchemy | 2.0.49 |
| Validación | Pydantic v2 | 2.13.x |
| Servidor ASGI | Uvicorn | 0.46.x |
| Autenticación | python-jose (JWT) | 3.5.0 |
| Hashing contraseñas | passlib + bcrypt | 1.7.4 / 4.0.1 |
| Migraciones BD | Alembic | 1.18.x |
| Rate limiting | SlowAPI | 0.1.9 |
| PDF | ReportLab | 4.5.x |
| Excel | openpyxl | 3.1.5 |
| Analítica de datos | Pandas | 3.0.3 |
| Cómputo numérico | NumPy | 2.4.6 |
| HTTP client | httpx | 0.28.x |
| IA | Google Gemini (google-genai) | 2.2.0 |
| Correo | Resend | 2.30.x |

### 4.2 Frontend

| Componente | Tecnología |
|---|---|
| Stack | *(a completar por Sharon / Santiago)* |
| Despliegue | Vercel |
| Dominio principal | app.pisst.online |
| Dominio pruebas | pisst-frontend.vercel.app |

### 4.3 Base de Datos

| Componente | Detalle |
|---|---|
| Motor | PostgreSQL 16 |
| Proveedor | Neon (serverless cloud) |
| Conector | psycopg2-binary |
| SSL | Requerido (sslmode=require) |
| Índices | ix_incidentes_empresa_estado, ix_users_empresa_activo, ix_acciones_incidente_estado |
| Entorno tests | SQLite en memoria |

### 4.4 Servicios Externos

| Servicio | Propósito |
|---|---|
| Google Gemini AI | Motor del asistente SASBOT |
| Resend | Correos transaccionales (bienvenida, reset de contraseña) |
| Google reCAPTCHA v2 | Protección del endpoint de login |

### 4.5 Infraestructura y Despliegue

| Componente | Herramienta |
|---|---|
| Backend hosting | Render |
| Frontend hosting | Vercel |
| Base de datos | Neon PostgreSQL |
| Control de versiones | GitHub |
| CI/CD | GitHub Actions |
| Actualizaciones de dependencias | Dependabot (semanal) |

---

## 5. Seguridad

### 5.1 Control de Acceso por Roles

- Todos los endpoints protegidos usan la dependencia `require_role()` o `get_current_user()`
- El JWT incluye `sub` (user_id), `role` y `sid` (session_id)
- La sesión es única: cada login invalida la sesión anterior
- `POST /cambiar-password` valida el `session_token` manualmente (no usa `get_current_user` para permitir el cambio cuando `debe_cambiar_password=True`, pero sí valida la sesión activa)
- `POST /admin/*` protegido adicionalmente con `ADMIN_SECRET_KEY` en header

### 5.2 Mecanismos de Protección Implementados

| Mecanismo | Implementación |
|---|---|
| Autenticación | JWT (access 30 min) + Refresh token (7 días) |
| Aislamiento multi-tenant | Toda query filtra por `empresa_id` del JWT |
| Bloqueo de cuenta | 5 intentos fallidos → bloqueo 5 minutos |
| Validación de contraseña | 8+ chars, mayúscula, minúscula, número y símbolo |
| Cambio forzado en primer login | Campo `debe_cambiar_password` verificado en cada request |
| No enumeración de usuarios | Login devuelve siempre el mismo mensaje de error |
| Rate limiting | SlowAPI por token de usuario (no por IP) |
| Emails en logs | Enmascarados: `b*****@empresa.com` |
| reCAPTCHA | Validado antes de consultar la BD |
| CORS | Solo origins autorizados; localhost solo en `development` |
| Validación de entrada | Pydantic v2 en todos los schemas de request |
| Serialización segura | `response_model` en todos los endpoints → nunca se expone `password_hash` |
| CVEs | Dependencias auditadas con `pip-audit` y Dependabot activo |
| Sesión única por dispositivo | `session_token` en JWT validado contra BD en cada request y en cambio de contraseña |

### 5.3 Auditoría y Trazabilidad

- **Tabla `audit_logs`:** Registra automáticamente creación de usuarios, cambios de estado de incidentes y cierre de acciones correctivas
- **Soft delete:** Entidades críticas usan campo `activo` → nunca se eliminan físicamente
- **Historial de chat:** Todas las conversaciones del SASBOT quedan registradas por usuario
- **Logging estructurado:** `logging.basicConfig` con niveles INFO/WARNING/ERROR en toda la app

---

## 6. Guía de Desarrollo

### 6.1 Configuración del Entorno Local

```bash
# 1. Clonar el repositorio
git clone https://github.com/sharolpulgarinSENA/PISST.git
cd PISST

# 2. Crear entorno virtual
python -m venv venv
venv/Scripts/activate        # Windows
source venv/bin/activate     # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Instalar hooks de pre-commit
pre-commit install

# 5. Copiar y configurar variables de entorno
cp .env.example .env
# Editar .env con los valores correspondientes

# 6. Aplicar migraciones
alembic upgrade head

# 7. (Opcional) Cargar datos demo
python seed.py

# 8. Iniciar el servidor
uvicorn main:app --reload
```

### 6.2 Variables de Entorno Requeridas

Ver [.env.example](.env.example) para la lista completa. Variables críticas:

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | URL de conexión a PostgreSQL (Neon) |
| `SECRET_KEY` | Clave para firmar los JWT (generar con `secrets.token_hex(32)`) |
| `GEMINI_API_KEY` | API key de Google Gemini AI |
| `RESEND_API_KEY` | API key de Resend para correos |
| `ADMIN_SECRET_KEY` | Clave para endpoints de administración |
| `ENVIRONMENT` | `development` activa /docs y omite reCAPTCHA |

### 6.3 Migraciones de Base de Datos

```bash
# Crear nueva migración (después de cambiar un modelo)
alembic revision --autogenerate -m "sprint_N_descripcion_corta"

# Aplicar migraciones pendientes
alembic upgrade head

# Revertir última migración
alembic downgrade -1

# Ver estado actual
alembic current
```

**Convención de nombres:** `sprint_N_descripcion_corta` donde N es el número de sprint.

### 6.4 Cómo Correr los Tests

Los tests usan **SQLite en memoria** — no requieren conexión a Neon ni variables de entorno configuradas.

#### Comandos básicos

```bash
# Correr todos los tests
.\venv\Scripts\python.exe -m pytest

# Ver nombre de cada test (modo verbose)
.\venv\Scripts\python.exe -m pytest -v

# Correr solo un archivo específico
.\venv\Scripts\python.exe -m pytest tests/test_auth_service.py -v

# Correr un test específico por nombre
.\venv\Scripts\python.exe -m pytest tests/test_auth_service.py::test_login_exitoso -v
```

#### Ver cobertura de código

```bash
# Reporte en terminal con líneas sin cubrir
.\venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing

# Solo el porcentaje total (más limpio)
.\venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing -q
```

#### Archivos de tests disponibles

| Archivo | Qué prueba | Tests |
|---|---|---|
| `tests/test_auth.py` | Endpoints HTTP de autenticación | 5 |
| `tests/test_auth_service.py` | Lógica del servicio de auth directamente | 25 |
| `tests/test_incidente_service.py` | Servicio de incidentes, investigaciones y acciones correctivas | 18 |
| `tests/test_riesgo_service.py` | Servicio de peligros, evaluaciones y medidas de control | 18 |
| `tests/test_capacitacion_service.py` | Servicio de capacitaciones, sesiones, asistencia y evaluaciones | 22 |
| `tests/test_auditoria_service.py` | Servicio de auditorías, hallazgos y no conformidades | 18 |
| `tests/test_usuario_service.py` | Servicio de usuarios — crear, filtrar, actualizar, área y cargo | 26 |
| `tests/test_admin_router.py` | Endpoints HTTP de administración con X-Admin-Key + flag debe_cambiar_password | 18 |
| `tests/test_capacitacion_service.py` | Servicio de capacitaciones, sesiones, asistencia y evaluaciones + filtro activo | 24 |
| `tests/test_furat_service.py` | Generación del PDF FURAT con distintos escenarios | 6 |
| `tests/test_metricas_service.py` | KPIs, dashboard, alertas, PDF y Excel ejecutivos | 20 |
| `tests/test_deps.py` | Autenticación HTTP: token inválido/expirado, usuario inexistente, sesión inválida, rol insuficiente | 8 |
| `tests/test_metricas.py` | Endpoints HTTP de métricas | 2 |
| `tests/test_usuarios.py` | Endpoints HTTP de usuarios | 6 |
| `tests/test_analytics_service.py` | Servicio analítico: incidentes, riesgos, capacitaciones, cumplimiento, multi-tenancy | 12 |

**Total: 207 tests — cobertura global: 91%**

#### Diferencia entre tests de endpoint y tests de servicio

- **Tests de endpoint** (`test_auth.py`, `test_metricas.py`, `test_usuarios.py`): hacen requests HTTP reales usando `TestClient`. Prueban el flujo completo incluyendo autenticación, schemas y serialización.
- **Tests de servicio** (`test_auth_service.py`, `test_incidente_service.py`, etc.): llaman las funciones del servicio directamente con una sesión de BD. Son más rápidos, más aislados y más fáciles de mantener.

#### Estructura del entorno de tests (`tests/conftest.py`)

```python
# Fixtures disponibles para todos los tests:
db        # sesión de SQLite, hace rollback al terminar cada test
client    # TestClient de FastAPI con BD sobreescrita
empresa   # empresa de prueba ya creada en BD
usuario_sst  # usuario con rol SST ya creado en BD
```

### 6.5 Flujo de Trabajo Git

```bash
# 1. Trabajar en tu rama
git checkout barner-acosta

# 2. Hacer cambios, add y commit
git add archivo.py
git commit -m "tipo(scope): descripción"
# Los hooks de pre-commit corren automáticamente: black, isort, flake8

# 3. Push de tu rama
git push origin barner-acosta

# 4. Merge a Dev
git checkout Dev
git merge barner-acosta --no-edit
git push origin Dev

# 5. Merge a main
git checkout main
git merge Dev --no-edit
git push origin main

# 6. Volver a tu rama
git checkout barner-acosta
```

### 6.6 Convenciones de Código

El proyecto usa **pre-commit hooks** que se ejecutan automáticamente antes de cada `git commit`:

| Herramienta | Función |
|---|---|
| `black` | Formateo automático del código |
| `isort` | Ordenamiento automático de imports |
| `flake8` | Linting y detección de errores de estilo |

Configuración en [.flake8](.flake8) y [.pre-commit-config.yaml](.pre-commit-config.yaml).

---

## 7. API Reference

### 7.1 Autenticación de Requests

```
Authorization: Bearer <access_token>
```

Para endpoints admin:
```
X-Admin-Key: <ADMIN_SECRET_KEY>
```

### 7.2 Endpoints por Módulo

| Módulo | Prefijo | Roles permitidos |
|---|---|---|
| Autenticación | `/auth` | Público / Autenticado |
| Usuarios | `/usuarios` | sst |
| Incidentes | `/incidentes` | sst, empleado |
| Riesgos | `/riesgos` | sst, gerencia |
| Capacitaciones | `/capacitaciones` | sst, gerencia, empleado |
| Auditorías | `/auditorias` | sst, gerencia |
| Métricas | `/metricas` | sst, gerencia |
| Chat IA | `/chat` | Autenticado |
| Áreas | `/areas` | sst |
| Cargos | `/cargos` | sst |
| Administración | `/admin` | X-Admin-Key |
| Analytics | `/analytics` | sst, gerencia |

> Documentación interactiva disponible en `/docs` (solo en `ENVIRONMENT=development`)

### 7.3 Códigos de Error Estándar

| Código | Significado | Ejemplo |
|---|---|---|
| `400` | Datos de entrada inválidos | Email ya registrado |
| `401` | No autenticado o token expirado | Token inválido o sesión revocada |
| `403` | Sin permisos o acción bloqueada | `debe_cambiar_password` |
| `404` | Recurso no encontrado | Usuario no existe |
| `422` | Error de validación Pydantic | Campo requerido faltante |
| `429` | Demasiadas peticiones | Cuenta bloqueada por intentos |
| `500` | Error interno del servidor | Error inesperado |
| `503` | Servicio no disponible | Base de datos no accesible |

Todos los errores retornan:
```json
{ "detail": "Descripción del error", "status_code": N }
```

---

## 8. Historial de Cambios

### Sprint 10 — Módulo de Analytics con Pandas y NumPy (195 → 207 tests)

**Objetivo:** Implementar analítica integrada dentro del proyecto PISST, sin crear un servicio separado. El módulo es estrictamente de solo lectura y usa Pandas y NumPy para procesar datos existentes en Neon.

**Archivos nuevos:**

| Archivo | Descripción |
|---|---|
| `app/services/analytics_service.py` | 4 funciones analíticas con Pandas/NumPy |
| `app/routers/analytics_router.py` | 4 endpoints `/analytics/*` con RBAC |
| `tests/test_analytics_service.py` | 12 tests de servicio |
| `notebooks/01_exploracion_incidentes.ipynb` | Exploración de incidentes para sustentación |
| `notebooks/02_exploracion_riesgos.ipynb` | Exploración de peligros y controles para sustentación |
| `notebooks/03_exploracion_capacitaciones.ipynb` | Exploración de asistencia y evaluaciones para sustentación |

**Archivos modificados:**

| Archivo | Cambio |
|---|---|
| `main.py` | Registro de `analytics_router` |
| `requirements.txt` | Agrega `pandas>=2.0.0` y `numpy>=1.24.0` |

**Endpoints nuevos:**

| Endpoint | Qué calcula |
|---|---|
| `GET /analytics/incidentes` | Distribución por tipo/severidad, tasa mensual, tendencia |
| `GET /analytics/riesgos` | Niveles de riesgo, % con medidas implementadas, críticos sin control |
| `GET /analytics/capacitaciones` | Tasa de aprobación, asistencia promedio, alertas < 80% |
| `GET /analytics/cumplimiento` | Score SG-SST 0–100 desglosado en 4 componentes |

**Tests — +12 tests (195 → 207):**
- `test_analytics_incidentes_sin_datos`: respuesta vacía sin explotar
- `test_analytics_incidentes_con_datos`: distribuciones por tipo y severidad correctas
- `test_analytics_multitenant_incidentes`: empresa A no ve datos de empresa B
- `test_analytics_riesgos_sin_datos` / `_distribucion` / `_pct_control`: cobertura completa
- `test_analytics_capacitaciones_sin_datos` / `_aprobacion` / `_alerta_asistencia` / `_sin_sesion_realizada`
- `test_analytics_cumplimiento_vacio`: score 0 sin datos, desglose con las 4 claves
- `test_analytics_cumplimiento_con_datos_parciales`: score parcial cuando hay capacitaciones realizadas

**Total: 207 tests — cobertura global: 91%**

---

### Integración Frontend II — GET /capacitaciones/ devuelve todas por defecto

**Solicitud de Sharon:** el frontend necesita recibir todas las capacitaciones (activas e inactivas) y filtrar localmente.

**Cambio:** `GET /capacitaciones/` ahora devuelve **todas** por defecto en lugar de solo las activas.

| Request | Antes | Ahora |
|---------|-------|-------|
| `GET /capacitaciones/` | Solo activas | **Todas** |
| `GET /capacitaciones/?activo=true` | Solo activas | Solo activas |
| `GET /capacitaciones/?activo=false` | Solo inactivas | Solo inactivas |

**Archivos modificados:** `capacitacion_service.py` y `capacitacion_router.py` (default `activo=True` → `activo=None`).

**Tests:** +2 tests verifican que el default devuelve activas e inactivas, y que el filtro explícito sigue funcionando. Total: 187 → **189 tests**.

---

### Integración Frontend — Ajustes de contrato, bugs y calidad (91% cobertura)

**Cambios en contrato de API solicitados por el equipo frontend:**

- **`POST /auth/login`** ahora devuelve `debe_cambiar_password: bool` en la respuesta. El frontend puede redirigir a `/cambiar-password` directamente tras el login sin esperar un 403 posterior.
- **`GET /capacitaciones/`** acepta parámetro opcional `?activo=true|false`. Sin parámetro devuelve solo activas (comportamiento anterior). Ahora también tiene `response_model=List[CapacitacionResponse]` que faltaba.

**Bugs corregidos:**

- **`POST /admin/crear-sst` y `POST /admin/crear-gerencia`**: los usuarios creados por el admin no tenían `debe_cambiar_password=True`, por lo que podían entrar sin cambiar su contraseña temporal. Corregido explicitando el flag en ambos endpoints (igual que `POST /usuarios/`).
- **`deps.py`**: `user_id` del JWT se pasaba como string al filtro de BD — falla silenciosa en SQLite. Corregido con `UUID(user_id)` explícito (mismo fix ya aplicado en `auth_service.py`).

**Símbolos válidos en `validar_fortaleza_password`** (confirmado para el frontend):
```
! @ # $ % ^ & * ( ) , . ? " : { } | < > _ -
```
Regex exacto: `[!@#$%^&*(),.?\":{}|<>_\-]`

**Tests — +11 tests (176 → 187):**

| Archivo | Cambio |
|---|---|
| `test_auth.py` | Verifica `debe_cambiar_password=False` en login normal y `=True` en primer login |
| `test_admin_router.py` | 2 tests nuevos: consultan la BD tras crear SST/Gerencia y verifican el flag |
| `test_deps.py` | Nuevo — 8 tests HTTP cubren todos los paths de error de `get_current_user` y `require_role` |

**Cobertura: `deps.py` 38% → 100% | Global: 90% → 91%**

---

### Sprint 8 — Cobertura total de metricas_service (84% → 90%)

**Tests — 20 tests nuevos:**

| Función | Casos cubiertos |
|---|---|
| `get_kpis` | empresa vacía (todo cero), con empleados, con accidentes, con días de incapacidad, incidentes que no son accidentes no cuentan |
| `get_dashboard_gerencia` | vacío (cumplimiento 100%), incidentes activos, cumplimiento con acciones, acciones vencidas, incidentes del último mes |
| `get_alertas` | sin alertas, incidente abierto sin investigación (crítico), acción vencida (crítico), acción próxima 7 días (medio), casos negativos donde NO debe alertar |
| `generar_reporte_pdf` | retorna PDF válido (`%PDF`) para los 3 períodos: mensual, trimestral, anual |
| `generar_reporte_excel` | retorna `.xlsx` válido abierto con openpyxl, hoja "Reporte PISST" con KPIs |

**Cobertura: `metricas_service` 16% → 100% | Global: 84% → 90%**

---

### Sprint 7 — Cobertura de admin_router y furat_service (79% → 84%)

**`admin_router` (47% → 97%) — 16 tests HTTP:**
- `POST /admin/empresas`: crear exitoso, NIT duplicado, sin header (422), clave incorrecta (403)
- `GET /admin/empresas`: listar, clave incorrecta
- `POST /admin/crear-sst`: exitoso, empresa inexistente, SST duplicado por empresa, email duplicado, correo fallido no explota
- `POST /admin/crear-gerencia`: exitoso, duplicada, empresa inexistente
- `POST /admin/limpiar-tokens`: sin caducados, con usuario de token expirado

**`furat_service` (17% → 100%) — 6 tests:**
- Retorna bytes con firma `%PDF` válida
- Con lesión, con investigación de causas, con trabajador afectado
- Incidente inexistente → 404

---

### Sprint 6 — Cobertura de auditoria_service y usuario_service + Feature usuarios (74% → 79%)

**`auditoria_service` (21% → 100%) — 18 tests:**
- Auditorías: crear, buscar, no encontrado, cambiar estado a `en_ejecucion` (registra `fecha_ejecucion`) y a `completada`
- Hallazgos: crear, auditoría inexistente, listar
- No conformidades: crear, hallazgo inexistente, cerrar sin evidencia (400), cerrar con evidencia (registra `fecha_cierre`)
- Progreso: sin hallazgos (100%), con NC abierta (0%), con NC cerrada (100%)

**`usuario_service` (36% → 99%) — 26 tests:**
- `generar_password_temporal` con longitud por defecto y personalizada
- Listar, buscar, no encontrado
- Crear empleado: exitoso, rol no empleado (403), email duplicado (400), con área y cargo por nombre, área inexistente (404), cargo inexistente (404), correo fallido no explota
- Actualizar: nombre, desactivar, asignar área y cargo
- `area_nombre` y `cargo_nombre`: None cuando no tiene, con nombre correcto cuando tiene

**Feature `/usuarios/` — Solicitud de Sharon:**
- `GET /usuarios/?activo=true|false` filtra por estado activo/inactivo; sin parámetro devuelve todos
- `UsuarioResponse` incluye `area_nombre` y `cargo_nombre` listos para el frontend (via properties ORM en el modelo `User`)

---

### Sprint 5 — Deuda técnica: arquitectura de servicios y cobertura de tests

**Arquitectura:**
- Extracción de `auth_service.py` — toda la lógica de negocio de autenticación movida del router al servicio dedicado. El router queda solo con schemas y delegación.

**Seguridad:**
- Corrección de bug en `POST /auth/cambiar-password`: el endpoint no validaba el `session_token`, permitiendo que un JWT revocado (por logout o login desde otro dispositivo) pudiera cambiar la contraseña. Ahora el servicio valida `session_id` contra la BD antes de proceder.
- Corrección de type annotation: `user_id` convertido explícitamente a `UUID` en la query de `cambiar_password` (necesario para compatibilidad con SQLite en tests y correctitud semántica).

**Tests — de 11 a 94 tests (+83 tests):**

| Archivo nuevo | Cobertura |
|---|---|
| `test_auth_service.py` | login, registro, cambiar password (incluyendo session_token inválido), refresh, logout, reset |
| `test_incidente_service.py` | incidentes, investigaciones, acciones correctivas, progreso |
| `test_riesgo_service.py` | peligros, evaluaciones de riesgo (4 niveles), medidas de control, matriz |
| `test_capacitacion_service.py` | capacitaciones, sesiones, asistencia, evaluaciones, responder evaluación, cobertura |

**Cobertura global: 64% → 74%**

| Servicio | Antes | Después |
|---|---|---|
| `auth_service` | — (nuevo) | 92% |
| `incidente_service` | 22% | 100% |
| `riesgo_service` | 19% | 97% |
| `capacitacion_service` | 14% | 79% |
| `audit_service` | 71% | 100% |

---

### Revisión Técnica — Mejoras de arquitectura y seguridad

**Seguridad:**
- `POST /auth/logout` que invalida refresh y session token en BD
- Emails enmascarados en logs del servidor
- CVEs resueltos: starlette, urllib3, idna actualizados
- Emails enmascarados en todos los warnings de correo

**Roles y permisos:**
- SST restringido a crear solo empleados (rol `empleado`)
- Máximo 1 SST activo por empresa
- Máximo 1 Gerencia activa por empresa
- `GET /cargos/` incluye `area_id` y `area_nombre`

**Calidad de código:**
- `isort` agregado al pre-commit (imports ordenados automáticamente)
- Handler global de errores (formato consistente en toda la API)
- Dependabot activo (alertas semanales de CVEs)
- Plantillas de PR e Issue en GitHub
- `POST /admin/limpiar-tokens` para mantenimiento de tokens caducados
- Validación con `Literal` en endpoint de reporte rápido del chat

**Migraciones aplicadas:**
- `sprint_4_agregar_debe_cambiar_password`
- `sprint_4_agregar_refresh_token`
- `sprint_4_tabla_audit_log`
- `sprint_4_agregar_indices_criticos`

---

### Sprint 4 — Correcciones críticas y fundamentos de producción

**Seguridad:**
- Corrección de aislamiento multi-tenant en `/auth/register`
- Validación de fortaleza de contraseña en todos los flujos
- Guard contra `None` en `reset_token_expira`
- Validación de `SECRET_KEY` al arranque del servidor
- CORS restrictivo por entorno

**Nuevas funcionalidades:**
- Refresh tokens (access 30 min + refresh 7 días)
- Cambio de contraseña obligatorio en primer login
- Health check con verificación real de BD
- Paginación en todos los endpoints de listado
- Auditoría de acciones críticas (tabla `audit_logs`)

**Corrección de bugs:**
- Comparaciones Enum con strings en queries SQL
- `datetime.utcnow()` deprecado → `datetime.now(timezone.utc)`
- Paquetes Google AI duplicados
- Encoding UTF-16 en `requirements.txt`

**Calidad:**
- `response_model` Pydantic en todos los endpoints
- Logging estructurado (eliminados todos los `print()`)
- Migración a Pydantic v2 (`ConfigDict`)
- `declarative_base` actualizado a SQLAlchemy 2.0
- 3 índices compuestos en BD
- 11 tests automatizados con pytest
- CI/CD con GitHub Actions

---

*Documentación actualizada el 2026-06-04*
*Proyecto PISST — SENA*
