# Documentación Técnica — PISST
## Plataforma Integral de Seguridad y Salud en el Trabajo
**Versión:** 2.0 | **Fecha:** 2026-06-11 | **Estado:** Producción

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
- **Tests automáticos:** 440 tests pasando al 100% ✅
- **Cobertura de código:** 95%+ ✅

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
│  • Cloudinary (fotos de perfil)                         │
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
| Login con JWT | Access token (30 min) + Refresh token (7 días). La respuesta incluye `id`, `role`, `nombre` y `debe_cambiar_password` para que el frontend no necesite decodificar el JWT |
| Cambio de contraseña obligatorio | Primer login fuerza cambio de contraseña temporal. El flag aplica a todos los roles creados por el admin (SST, Gerencia) y por el SST (empleados) |
| Bloqueo por intentos | 5 intentos fallidos → bloqueo 5 minutos |
| Recuperación de contraseña | Token por correo, expira en 30 minutos |
| Validación de contraseña | Mínimo 8 caracteres, mayúscula, minúscula, número y símbolo |
| Logout real | Invalida refresh y session token en BD |
| Gestión de empleados | SST crea empleados con área y cargo asignados |
| Sesión única | Cada login invalida la sesión anterior; session_token validado en cada request |
| Filtro de usuarios | `GET /usuarios/?activo=true\|false` filtra por estado; sin parámetro devuelve todos |
| Nombres en respuesta | `GET /usuarios/` incluye `area_nombre` y `cargo_nombre` listos para el frontend |
| Editar perfil propio | `PATCH /usuarios/me` — el usuario edita su propio `nombre` y `telefono`. No puede cambiar rol, cargo ni email |
| Foto de perfil | `PUT /usuarios/me/foto` — sube o reemplaza foto (JPG/PNG/WEBP, máx 2 MB). Almacenada en Cloudinary, retorna `foto_url` |
| Actividad propia | `GET /usuarios/me/actividad` — historial paginado de acciones del usuario. Retención: 30 días |

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
| Consultar investigación | `GET /incidentes/{id}/investigacion` — 404 si no existe |
| Actualizar investigación | `PATCH /incidentes/{id}/investigacion` — actualiza campos enviados, 404 si no existe |
| Consultar acciones | `GET /incidentes/{id}/acciones` — lista todas las acciones, [] si no hay |

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
| Evaluaciones | Preguntas de opción múltiple con calificación automática. `respuesta_dada` acepta la clave `"a"/"b"/"c"/"d"` o el texto completo de la opción |
| Certificados PDF | Generación automática al aprobar |
| Cobertura | Porcentaje del plan anual de capacitaciones cumplido |
| Filtro por estado | `GET /capacitaciones/` devuelve **todas** por defecto. `?activo=true` solo activas, `?activo=false` solo inactivas |
| Historial empleado | `GET /capacitaciones/empleados/{id}/historial` — empleado ve su propio historial; SST ve cualquiera. Response incluye nombre de capacitación, fecha de sesión, evaluación con preguntas (`opciones` como `[{"clave": "a", "texto": "..."}]`) y resultado del empleado |

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
| No conformidades anidadas | `GET /auditorias/{id}/hallazgos` incluye `no_conformidades: []` en cada hallazgo — nunca `null` |
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
| Motor de IA | Google Gemini AI (gemini-2.5-flash) |
| Reporte rápido | Empleado reporta incidente directamente desde el chat |
| Historial | Historial de conversaciones paginado por usuario |
| Modo emergencia | Detección de palabras clave críticas con respuesta especial |
| Escalamiento SST | `POST /chat/escalar` — envía historial al coordinador SST por correo vía Resend |
| Análisis de archivos | `POST /chat/archivo` — analiza PDF e imágenes con Gemini vision. DOC/DOCX sugiere convertir a PDF. Límite: 10 MB |

### 3.8 Analytics — Analítica Integrada

**Endpoints:** `/analytics/*`

Módulo de solo lectura. Usa **agregaciones SQL** (`func.count`, `GROUP BY`, `joinedload`) para máximo rendimiento. Pandas se conserva únicamente para el cálculo de tendencia mensual (requiere operaciones de periodo de fecha). No toca ningún servicio existente ni escribe en la BD.

| Endpoint | Rol | Parámetros | Qué devuelve |
|---|---|---|---|
| `GET /analytics/incidentes` | sst, gerencia | `limit` (≤1000), `offset`, `fecha_desde`, `fecha_hasta` | Distribución por tipo y severidad, tasa mensual promedio, tendencia (aumento/baja/estable) |
| `GET /analytics/riesgos` | sst, gerencia | `limit` (≤1000), `offset` | Distribución por nivel (bajo/medio/alto/crítico), % con medidas implementadas, peligros críticos sin control |
| `GET /analytics/capacitaciones` | sst, gerencia | `limit` (≤1000), `offset`, `fecha_desde`, `fecha_hasta` | Tasa de aprobación global, asistencia promedio, alertas de empleados con asistencia < 80%, capacitaciones sin sesión realizada |
| `GET /analytics/cumplimiento` | sst, gerencia | — | Score SG-SST (0–100) y desglose por módulo: incidentes investigados, peligros con control, capacitaciones realizadas, NC cerradas |

**Principios del módulo:**
- Estrictamente de solo lectura (`db.query()` únicamente — nunca `db.add/commit/delete`)
- Multi-tenant: toda query filtra por `empresa_id` del usuario autenticado
- No invasivo: un error en analytics no afecta el backend principal
- Reutiliza el mismo JWT/RBAC del resto del proyecto
- Paginación protegida: `limit` máximo 1000 — valores mayores retornan 422

---

### 3.9 Notificaciones y Feed de Actividad

**Endpoints:** `/notificaciones/*`

Feed de eventos en tiempo real, segmentado por rol. Diferente a `/metricas/alertas` (alertas son problemas activos; el feed es historial de lo que ocurrió).

| Endpoint | Rol | Descripción |
|---|---|---|
| `GET /notificaciones/feed` | Autenticado | Feed paginado del más reciente al más antiguo, filtrado según rol |
| `PATCH /notificaciones/{id}/leido` | Autenticado | Marca una notificación como leída |
| `PATCH /notificaciones/leer-todas` | Autenticado | Marca todas las notificaciones no leídas como leídas |

**Segmentación del feed por rol:**

| Rol | Qué ve |
|---|---|
| `sst`, `gerencia`, `admin` | Notificaciones de empresa (incidentes, riesgos, auditorías, capacitaciones creadas) |
| `empleado` | Solo sus notificaciones personales (capacitaciones asignadas) |

**Eventos generados automáticamente:**

| Tipo | Cuándo | Destinatario | url_destino |
|---|---|---|---|
| `reporte_nuevo` | Empleado crea un reporte | Empresa | `/incidentes?reporte={id}` |
| `reporte_estado_cambio` | SST cambia estado de un incidente | Empresa | `/incidentes` |
| `accion_correctiva_nueva` | SST crea acción correctiva | Empresa | `/incidentes` |
| `accion_correctiva_completada` | SST marca acción como completada | Empresa | `/incidentes` |
| `investigacion_completada` | SST completa investigación | Empresa | `/incidentes` |
| `capacitacion_nueva` | SST crea una capacitación | Empresa | `/capacitaciones` |
| `capacitacion_sesion_programada` | SST programa una sesión | Empresa | `/capacitaciones` |
| `capacitacion_sesion_realizada` | SST cierra sesión como realizada | Empresa | `/capacitaciones` |
| `capacitacion_sesion_cancelada` | SST cancela una sesión | Empresa | `/capacitaciones` |
| `capacitacion_sesion_reprogramada` | SST reprograma una sesión | Empresa | `/capacitaciones` |
| `capacitacion_asignada` | SST registra asistencia de empleado | **Personal** | `/capacitaciones/historial` |
| `riesgo_nuevo` | SST identifica un nuevo peligro | Empresa | `/riesgos` |
| `auditoria_nueva` | SST crea una auditoría | Empresa | `/auditorias` |
| `hallazgo_nuevo` | SST registra un hallazgo | Empresa | `/auditorias` |
| `auditoria_vencida` | Cron diario detecta auditoría sin cerrar | Empresa | `/auditorias` |

**Política de retención:** registros con más de 30 días se eliminan automáticamente en cada consulta al feed.

---

### 3.10 Administración del Sistema

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
| ORM | SQLAlchemy | 2.0.50 |
| Validación | Pydantic v2 | 2.13.x |
| Servidor ASGI | Uvicorn | 0.49.0 |
| Autenticación | python-jose (JWT) | 3.5.0 |
| Hashing contraseñas | passlib + bcrypt | 1.7.4 / 4.0.1 |
| Migraciones BD | Alembic | 1.18.x |
| Rate limiting | SlowAPI | 0.1.9 |
| PDF | ReportLab | 4.5.x |
| Excel | openpyxl | 3.1.5 |
| Analítica de datos | Pandas | >=2.0.0 |
| HTTP client | httpx | 0.28.x |
| IA | Google Gemini (google-genai) | 2.2.0 |
| Correo | Resend | 2.30.x |
| Multipart (archivos) | python-multipart | ≥0.0.9 |
| Almacenamiento imágenes | cloudinary | 1.44.2 |

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
| Cloudinary | Almacenamiento de fotos de perfil (JPG/PNG/WEBP, máx 2 MB) |

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
| Rate limiting | SlowAPI por IP: 5/min en `/auth/login`, 20/min en `POST /chat/mensaje` |
| Emails en logs | Enmascarados: `b*****@empresa.com` |
| reCAPTCHA | Validado antes de consultar la BD |
| CORS | Solo origins autorizados; localhost solo en `development` |
| Validación de entrada | Pydantic v2 en todos los schemas de request. Enums en campos `tipo`, `estado`, `severidad`, `prioridad`: valor inválido → 422 antes de tocar la BD |
| Serialización segura | `response_model` en todos los endpoints → nunca se expone `password_hash` |
| Límites de paginación | `Query(ge=1, le=N)` en todos los endpoints de listado. Intentar `limit=999999` retorna 422 |
| Reset de contraseña seguro | Token de 64 chars hex, uso único, expira 24h. Tabla `reset_tokens` en BD; el correo nunca contiene la contraseña en texto plano |
| Claim `iat` en JWT | Access tokens incluyen `issued_at` para auditoría y detección de tokens antiguos |
| Verificación de empresa activa | `refrescar_token` verifica `empresa.activo` y `user.activo` antes de emitir nuevo access token |
| CVEs | Dependencias auditadas con `pip-audit` y Dependabot activo |
| Sesión única por dispositivo | `session_token` en JWT validado contra BD en cada request y en cambio de contraseña |

### 5.3 API Keys para servicios externos

Las API Keys permiten que procesos automáticos (cron jobs, servicios externos) se autentiquen sin JWT.

**Uso actual:** el cron job de cron-job.org que ejecuta `POST /auditorias/verificar-vencidas` diariamente usa una API Key en el header `X-API-Key: sk_...`.

**Gestión:**

| Acción | Endpoint |
|---|---|
| Crear nueva API Key | `POST /auth/api-keys` (solo admin) |
| Revocar API Key | endpoint de revocación por ID |

**Formato de la clave:** `sk_` + 60 chars hex, generados con `secrets.token_hex(30)`.

**Ciclo de vida recomendado:**
- Generar **una sola vez** por integración. No expira automáticamente.
- **Rotar cada 90 días** como buena práctica de seguridad.
- Si una clave se filtra o compromete, revocarla inmediatamente y generar una nueva.

**Proceso de rotación:**
1. `POST /auth/api-keys` → copiar la nueva clave `sk_...`
2. Actualizar el header `X-API-Key` en cron-job.org con la nueva clave
3. Revocar la clave anterior

### 5.4 Auditoría y Trazabilidad

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
| `CLOUDINARY_CLOUD_NAME` | Nombre del cloud en Cloudinary |
| `CLOUDINARY_API_KEY` | API key de Cloudinary |
| `CLOUDINARY_API_SECRET` | API secret de Cloudinary |
| `BACKEND_URL` | URL pública del backend (requerida para cron jobs en producción) |

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
| `tests/test_auth.py` | Endpoints HTTP de autenticación: login, register, forgot/reset password, cambiar password, refresh, logout | 20 |
| `tests/test_auth_service.py` | Lógica del servicio de auth: login, refresh, reset token seguro, empresa activa | 34 |
| `tests/test_incidente_service.py` | Servicio de incidentes, investigaciones y acciones correctivas | 18 |
| `tests/test_riesgo_service.py` | Servicio de peligros, evaluaciones y medidas de control | 18 |
| `tests/test_capacitacion_service.py` | Servicio de capacitaciones, sesiones, asistencia, evaluaciones y generación de certificado PDF | 41 |
| `tests/test_auditoria_service.py` | Servicio de auditorías, hallazgos y no conformidades | 24 |
| `tests/test_usuario_service.py` | Servicio de usuarios — crear, filtrar, actualizar, área y cargo | 20 |
| `tests/test_admin_router.py` | Endpoints HTTP de administración con X-Admin-Key | 18 |
| `tests/test_furat_service.py` | PDF FURAT con datos reales + helper `_obtener_datos_furat` | 10 |
| `tests/test_metricas_service.py` | KPIs, dashboard, alertas, PDF y Excel ejecutivos | 20 |
| `tests/test_deps.py` | Autenticación HTTP: token inválido/expirado, sesión inválida, rol insuficiente | 8 |
| `tests/test_metricas.py` | Endpoints HTTP de métricas | 2 |
| `tests/test_usuarios.py` | Endpoints HTTP de usuarios | 6 |
| `tests/test_analytics_service.py` | Analytics: SQL aggregations, paginación, filtros de fecha, multi-tenancy | 16 |
| `tests/test_api_keys.py` | CRUD de API keys y autenticación con X-API-Key | 14 |
| `tests/test_perfil_notificaciones.py` | Perfil propio y notificaciones | 15 |
| `tests/test_routers.py` | Límites de paginación: 422 en exceso, 200 en válido — 6 endpoints | 15 |
| `tests/test_schemas.py` | Validación Enum en schemas: tipo, estado, severidad, prioridad | 24 |
| `tests/test_migrations.py` | Integridad estructural de migraciones Alembic (sin DB) | 10 |
| `tests/test_email_service.py` | Envío de correos transaccionales (reset, bienvenida, FURAT) con mocks de httpx | 13 |
| `tests/test_ai_service.py` | Servicio IA (Gemini): contexto SST, historial, manejo de errores, respuestas vacías | 15 |
| `tests/test_chat_router.py` | Endpoints HTTP del chat SASBOT: enviar mensaje, historial, auth 401/403 | 16 |
| `tests/test_capacitacion_router.py` | Endpoints HTTP de capacitaciones: CRUD, sesiones, asistencia, evaluaciones, certificado | 20 |
| `tests/test_area_router.py` | Endpoints HTTP de áreas: listar, crear, duplicado, 401/403 | 9 |
| `tests/test_cargo_router.py` | Endpoints HTTP de cargos: listar, crear, área inexistente, área otra empresa, duplicado | 8 |
| `tests/test_incidente_router.py` | Endpoints HTTP de incidentes: CRUD, investigación, acciones correctivas, FURAT | 26 |

**Total: 440 tests — cobertura global: 95%+**

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

### 6.5 Jupyter Notebooks — Análisis de Datos

Los notebooks están en la carpeta `notebooks/` y se usan para exploración y sustentación de datos.

| Notebook | Contenido |
|---|---|
| `01_exploracion_incidentes.ipynb` | Distribución de incidentes por tipo, severidad y tendencia mensual |
| `02_exploracion_riesgos.ipynb` | Peligros y controles por nivel de riesgo |
| `03_exploracion_capacitaciones.ipynb` | Asistencia, aprobación y alertas de capacitaciones |

**Filtro por empresa (multi-tenant)**

Cada notebook filtra los datos por empresa. Antes de arrancar, agregar al `.env`:

```
EMPRESA_ID=<uuid-de-la-empresa>
```

Para obtener el UUID: `SELECT id, nombre FROM empresas;` en Neon, o `GET /admin/empresas` en Swagger.

> **Nota:** El contador "Total incidentes en BD" que aparece al conectar es global (toda la BD, sin filtro) — solo sirve para verificar la conexión. Los gráficos y análisis sí filtran por la empresa configurada.

**Cómo arrancar Jupyter:**

```bash
# 1. Activar el entorno virtual (Windows)
venv\Scripts\activate

# 2. Arrancar Jupyter
jupyter notebook
```

Esto abre automáticamente el navegador en `http://localhost:8888`. Desde ahí navegá a la carpeta `notebooks/` y abrí el archivo `.ipynb` que necesites. Ejecutar con **Kernel → Restart & Run All**.

> Si `jupyter` no está instalado: `pip install jupyter`

### 6.6 Flujo de Trabajo Git

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
| Usuarios | `/usuarios` | sst / Autenticado (perfil propio: `GET /me`, `PATCH /me`, `PUT /me/foto`, `GET /me/actividad`) |
| Incidentes | `/incidentes` | sst, empleado |
| Riesgos | `/riesgos` | sst, gerencia |
| Capacitaciones | `/capacitaciones` | sst, gerencia, empleado |
| Auditorías | `/auditorias` | sst, gerencia |
| Métricas | `/metricas` | sst, gerencia |
| Chat IA | `/chat` | Autenticado |
| Notificaciones | `/notificaciones` | Autenticado |
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

### Sprint 15 — Hardening de seguridad y cobertura de tests (308 → 440 tests)

#### 15.1 Rate limiting

| Endpoint | Límite anterior | Límite nuevo |
|---|---|---|
| `POST /auth/login` | 20/min por IP | **5/min por IP** |
| `POST /chat/mensaje` | Sin límite | **20/min por IP** |

El limitador de `/auth/login` usa `Limiter(key_func=get_remote_address)` local al router; no depende del limiter global de `main.py`. El del chat también usa IP. Los tests evitan el endpoint `/auth/login` usando `_tokens_para(db, usuario)` que crea tokens directamente en BD.

**Archivos:** `app/routers/auth_router.py`, `app/routers/chat_router.py`

#### 15.2 Sanitización de inputs en generación de PDF (FURAT)

Se añadieron dos helpers a `furat_service.py`:

```python
def _safe(value, max_len: int = 500) -> str:
    s = str(value) if value is not None else ""
    s = "".join(c for c in s if c >= " " or c in "\n\r\t")
    return s[:max_len]

def _nr(value, max_len: int = 500) -> str:
    s = _safe(value, max_len).strip()
    return s if s else "No registrado"
```

`_safe()` elimina caracteres de control y trunca cadenas largas. Aunque `reportlab` con `Table` de strings planos no parsea XML (no hay riesgo de inyección hoy), el helper protege contra cambios futuros que usen `Paragraph`.

**Archivo:** `app/services/furat_service.py`

#### 15.3 Auditoría de dependencias (pip-audit)

Ejecutado `pip-audit` sobre todas las dependencias de la aplicación:

- **Resultado:** 0 CVEs en dependencias de la app
- Las 5 CVEs reportadas pertenecen al propio gestor `pip` (no es una dependencia de la app)
- `pip` actualizado de la versión anterior a **26.1.2**

#### 15.4 CORS verificado

La configuración de CORS en `main.py` ya estaba correcta: lista explícita de dominios autorizados (`pisst.online`, `app.pisst.online`, `pisst-frontend.vercel.app`, y `localhost` solo en modo `development`). No se usa `allow_origins=["*"]` en producción.

#### 15.5 Variables de entorno en producción confirmadas

Verificadas en los paneles de Render y Railway:
- `DATABASE_URL` (Neon PostgreSQL)
- `SECRET_KEY` (cadena larga aleatoria)
- `RESEND_API_KEY`
- `GEMINI_API_KEY`
- `RECAPTCHA_SECRET_KEY`
- `ADMIN_SECRET_KEY`
- `BACKEND_URL`
- `CLOUDINARY_*`

La `SECRET_KEY` puede rotarse en cualquier momento desde el panel de Render; al deployar, los JWT existentes quedan invalidados automáticamente.

#### 15.6 Nuevos archivos de tests — routers

| Archivo | Tests | Cobertura ganada |
|---|---|---|
| `tests/test_area_router.py` | 9 | area_router: 62% → 100% |
| `tests/test_cargo_router.py` | 8 | cargo_router: 56% → 100% |
| `tests/test_incidente_router.py` | 26 | incidente_router: 56% → 90%+ |
| `tests/test_email_service.py` | 13 | email_service: 0% → 95%+ |
| `tests/test_ai_service.py` | 15 | ai_service: 0% → 90%+ |
| `tests/test_chat_router.py` | 16 | chat_router: 0% → 90%+ |
| `tests/test_capacitacion_router.py` | 20 | capacitacion_router: 0% → 85%+ |

`test_incidente_router.py` incluye helpers `payload_incidente(**kwargs)` y `crear_incidente_via_api(client, headers, **kwargs)`. Cubre CRUD completo, investigación, acciones correctivas y FURAT (con `furat_service.generar_furat` mockeado).

#### 15.7 Expansión de tests existentes

| Archivo | Tests añadidos | Cobertura ganada |
|---|---|---|
| `tests/test_auth.py` | +14 (register, forgot/reset password, cambiar password, refresh, logout) | auth_router: 84% → 98%+ |
| `tests/test_capacitacion_service.py` | +11 (area_ids, activo, sesion 404, empleado 404, historial con evaluación aprobada, `generar_certificado`) | capacitacion_service: 80% → 100% |

El test `test_generar_certificado_ok` cubre el flujo completo: crear capacitacion → crear sesion → crear evaluacion → responder correctamente → generar PDF. Verifica que el buffer empiece con `b"%PDF"`.

#### 15.8 Helper `_tokens_para` en tests de auth

Para evitar que el rate limit de 5/min en `/auth/login` bloquee los tests de auth (que comparten la IP ficticia `testclient`), se creó el helper:

```python
def _tokens_para(db, usuario):
    """Crea access + refresh token directamente en BD sin pasar por el rate-limited /login."""
    session_id = secrets.token_hex(16)
    refresh = secrets.token_hex(40)
    usuario.session_token = session_id
    usuario.refresh_token = refresh
    usuario.refresh_token_expira = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)
    db.commit()
    access = create_access_token({"sub": str(usuario.id), "role": usuario.role.value, "sid": session_id})
    return {"access_token": access, "refresh_token": refresh}
```

Este patrón también está disponible en `test_incidente_router.py` y `test_cargo_router.py` para que los tests de esos routers no dependan de hacer login.

#### 15.9 Bugs corregidos durante los tests

| Bug | Síntoma | Fix |
|---|---|---|
| `POST /capacitaciones/` devolvía `{}` | `response_model` no declarado en el router | Agregado `response_model=CapacitacionResponse` |
| `POST /capacitaciones/sesiones` devolvía `{}` | Igual que el anterior | Agregado `response_model=SesionResponse` |
| Estado inicial incidente es `"borrador"`, no `"abierto"` | Tests asumían `"abierto"` | Corregidas aserciones en `test_incidente_router.py` |
| Estado inicial acción correctiva es `"planificada"`, no `"pendiente"` | Test asumía `"pendiente"` | Corregida aserción |
| Enum usa `"en_ejecucion"`, no `"en_progreso"` | Test enviaba valor inválido | Corregido valor en el test |
| `patch("app.services.auth_service.enviar_correo_reset")` no existe | `enviar_correo_reset` se importa dentro de la función, no como atributo del módulo | Cambiado a `patch("app.services.email_service.httpx.post")` |

#### 15.10 Resumen del sprint

- **Nuevos tests:** +132 (308 → 440)
- **Sin regresiones** en ninguno de los 308 tests previos
- **Cobertura global:** 91% → 95%+
- **CVEs en dependencias de la app:** 0

---

### Sprint 14 — Seguridad, calidad y deuda técnica (228 → 308 tests)

#### 14.1 Fix cron-job 422 en producción

- `POST /auditorias/verificar-vencidas` rechazaba el header `X-API-Key` de cron-job.org con 422 porque la dependencia usaba `x_admin_key: str = Header(...)` (nombre incorrecto). Corregido a `require_admin_or_api_key` que acepta JWT admin O header `X-API-Key`.
- Cron diario de cron-job.org ahora retorna 200 OK.

#### 14.2 Seguridad del refresh token

| Cambio | Descripción |
|---|---|
| `empresa.activo` verificado | `refrescar_token` verifica que la empresa del usuario esté activa |
| Claim `iat` en JWT | `create_access_token` incluye `issued_at` en cada token |
| Expiración máxima 7 días | Refresh tokens no pueden extenderse indefinidamente |

**Archivos:** `app/core/security.py`, `app/services/auth_service.py`

#### 14.3 Reset de contraseña con tokens seguros

Reemplaza el flujo anterior (contraseña temporal en texto plano por correo).

| Componente | Detalle |
|---|---|
| `ResetToken` (nuevo modelo) | Token de 64 chars hex, uso único (`usado=True` tras primer uso), expira 24h |
| `POST /admin/usuarios/{id}/reset-password` | Admin solicita reset → genera token → envía enlace por correo |
| `POST /auth/reset-password` | Acepta token seguro O el flow anterior (retrocompatibilidad) |
| Migración `d2e3f4a5b6c7` | Crea tabla `reset_tokens` en Neon |

**Archivos:** `app/models/reset_token.py` (nuevo), `app/services/auth_service.py`, `app/routers/auth_router.py`, `app/routers/admin_router.py`

#### 14.4 FURAT con datos reales

Elimina placeholders `"N/A"` y `"Empleado"` hardcodeados.

| Cambio | Descripción |
|---|---|
| `ciudad`, `direccion`, `telefono` en `Empresa` | Nuevas columnas en el modelo y en `POST /admin/empresas` |
| `tipo_vinculacion` en `User` | Reemplaza el string `"Empleado"` hardcodeado |
| Helper `_obtener_datos_furat()` | Función pública que retorna el dict de datos FURAT — testeable sin parsear PDF |
| `_nr()` helper | Reemplaza `None` por `"No registrado"` en lugar de `"N/A"` |
| Testigos en sección 3 | Se muestran los testigos reales del incidente |

**Migración:** `b1c2d3e4f5a6` — agrega 4 columnas (idempotente: usa `_column_exists()`)
**Archivos:** `app/models/empresa.py`, `app/models/user.py`, `app/services/furat_service.py`

#### 14.5 Optimización de analytics con SQL

Reemplaza todos los `.all()` con agregaciones SQL puras.

| Función | Antes | Después |
|---|---|---|
| `analizar_incidentes` | `.all()` + Python | `func.count()`, `GROUP BY` SQL; Pandas solo para tendencia |
| `analizar_riesgos` | `.all()` + pandas | `func.count()`, `joinedload` para evaluar N+1 |
| `analizar_capacitaciones` | pandas completo | SQL `JOIN + COUNT`, `case()` para asistencia |
| `calcular_cumplimiento` | `.all()` + numpy | 100% SQL, `sum()` Python puro |

**Parámetros nuevos en router:** `limit` (≤1000), `offset`, `fecha_desde`, `fecha_hasta` en incidentes y capacitaciones.
**Archivos:** `app/services/analytics_service.py`, `app/routers/analytics_router.py`

#### 14.6 Validación de límites de paginación

Todos los endpoints de listado protegidos con `Query(ge=1, le=N)`.

| Endpoint | Parámetro | Límite máximo |
|---|---|---|
| `GET /chat/historial` | `limite` | 500 |
| `GET /usuarios/` | `limit` | 1000 |
| `GET /usuarios/me/actividad` | `limit` | 200 |
| `GET /incidentes/` | `limit` | 500 |
| `GET /riesgos/peligros` | `limit` | 500 |
| `GET /auditorias/` | `limit` | 500 |

**Archivos:** `app/routers/chat_router.py`, `app/routers/usuario_router.py`, `app/routers/incidente_router.py`, `app/routers/riesgo_router.py`, `app/routers/auditoria_router.py`

#### 14.7 Validación con Enums en schemas de entrada

Reemplaza `str` por Enums en todos los campos de entrada que tienen valores predefinidos. Valor inválido retorna 422 antes de tocar la BD.

| Schema | Campo | Enum |
|---|---|---|
| `IncidenteCreate` | `tipo` | `TipoIncidenteEnum` |
| `IncidenteCreate` | `severidad` | `SeveridadEnum` |
| `IncidenteEstadoUpdate` | `estado` | `EstadoIncidenteEnum` |
| `AccionCorrectivaCreate/Update` | `prioridad` | `PrioridadAccionEnum` |
| `AccionCorrectivaUpdate` | `estado` | `EstadoAccionEnum` |
| `PeligroCreate` | `tipo` | `TipoPeligroEnum` |
| `MedidaControlCreate` | `tipo` | `TipoControlEnum` |
| `MedidaControlUpdate` | `estado` | `EstadoControlEnum` |
| `AsistenciaCreate` | `estado` | `EstadoAsistenciaEnum` |

**Nuevos Enums en modelo:** `EstadoSesionEnum`, `EstadoAsistenciaEnum` en `app/models/capacitacion.py`
**Archivos:** `app/schemas/incidente.py`, `app/schemas/riesgo.py`, `app/schemas/capacitacion.py`

#### 14.8 Limpieza de migraciones Alembic

| Problema | Solución |
|---|---|
| 2 migraciones no-op (`0b9763c56777`, `116df49d1acf`) | Eliminadas; `738b68b2392d.down_revision` actualizado |
| `op.create_foreign_key(None, ...)` en `4b8c830edc2c` | Renombrado a `notificaciones_usuario_id_fkey` (nombre real en Neon) |
| Nombre misleading `318f5a54c35c_add_telefono...` | Renombrado a `318f5a54c35c_allow_null_sesion_estado` |
| `api_keys` sin migración (tabla existía en Neon) | Migración `c1d2e3f4a5b6` idempotente + `alembic stamp` |
| `reset_tokens` sin migración y sin tabla en Neon | Migración `d2e3f4a5b6c7` + `alembic upgrade head` |
| `b1c2d3e4f5a6` falló por `DuplicateColumn` | Convertida a idempotente con `_column_exists()` |

**Estado final Neon:** `d2e3f4a5b6c7 (head)` — 21 migraciones, cadena lineal, sin bifurcaciones.

**Tests nuevos:** `tests/test_migrations.py` — 10 tests de integridad estructural (sin conexión a BD)

#### 14.9 Tests añadidos en este sprint

| Archivo | Tests nuevos | Total |
|---|---|---|
| `test_auth_service.py` | +9 (refresh token, reset token seguro) | 34 |
| `test_furat_service.py` | +4 (datos reales, sin N/A, campos empresa) | 10 |
| `test_analytics_service.py` | +4 (paginación, agregaciones, filtros fecha) | 16 |
| `test_routers.py` | +15 (422/200 paginación en 6 endpoints) | 15 |
| `test_schemas.py` | +24 (Enum válido/inválido por schema) | 24 |
| `test_migrations.py` | +10 (integridad cadena alembic) | 10 |

**Total: 228 → 308 tests (+80) — sin regresiones**

---

### Sprint 13 — Notificaciones personales, cron de vencimiento y fixes Santiago (228 tests)

**Solicitudes de Santiago y Sharon (equipo frontend):**

**Fixes de contrato de API:**

| Cambio | Descripción |
|---|---|
| `POST /auth/login` | La respuesta ahora incluye `id: str` (UUID del usuario). El frontend ya no necesita extraerlo decodificando el JWT |
| `POST /capacitaciones/evaluaciones/responder` | Fix del 500: columna `respuesta_dada` ampliada de `VARCHAR(1)` a `VARCHAR(500)`. La comparación ahora acepta tanto la clave `"a"/"b"/"c"/"d"` como el texto completo de la opción |
| `GET /capacitaciones/empleados/{id}/historial` | Las opciones de cada pregunta ahora se devuelven como `[{"clave": "a", "texto": "..."}, ...]` en lugar de una lista de strings |

**Notificaciones personales por rol:**

- Modelo `Notificacion` ampliado con campo `usuario_id` (nullable). Notificaciones de empresa tienen `usuario_id=NULL`; notificaciones personales llevan el UUID del destinatario
- `GET /notificaciones/feed`: SST/Gerencia ven notificaciones de empresa; empleados ven solo las suyas
- `PATCH /notificaciones/{id}/leido` y `PATCH /notificaciones/leer-todas`: filtran correctamente según rol
- Nuevo evento `capacitacion_asignada`: cuando el SST registra la asistencia de un empleado, ese empleado recibe una notificación personal automática

**Cron job — auditorías vencidas:**

- `POST /auditorias/verificar-vencidas` (protegido con `X-Admin-Key`): detecta auditorías con `fecha_programada` vencida sin cerrar y NC con `fecha_limite` vencida
- Cron job diario en Render (6am UTC) llama al endpoint vía `BACKEND_URL` + `ADMIN_SECRET_KEY`
- Variable de entorno nueva: `BACKEND_URL` (ej: `https://pisst.onrender.com`)

**Archivos modificados:**

| Archivo | Cambio |
|---|---|
| `app/models/notificacion.py` | Agrega columna `usuario_id` (FK nullable a `users`) |
| `app/models/capacitacion.py` | `respuesta_dada` de `String(1)` → `String(500)` |
| `app/services/notificacion_service.py` | `crear_notificacion` acepta `usuario_id` opcional; `get_feed`, `marcar_leido` y `marcar_todas_leidas` segmentan por rol |
| `app/services/auditoria_service.py` | Agrega `verificar_auditorias_vencidas` |
| `app/services/capacitacion_service.py` | Opciones de preguntas con clave; comparación de respuestas acepta texto completo |
| `app/routers/notificacion_router.py` | Pasa `usuario_id` y `role` al servicio |
| `app/routers/auditoria_router.py` | Agrega `POST /auditorias/verificar-vencidas` |
| `app/routers/capacitacion_router.py` | Hook `capacitacion_asignada` en `POST /asistencia` |
| `app/routers/auth_router.py` | Agrega `id: str` a `LoginResponse` |
| `app/services/auth_service.py` | Incluye `id` en el dict de retorno del login |
| `render.yaml` | Agrega cron job `pisst-verificar-vencidas` y variable `BACKEND_URL` |

**Migraciones aplicadas:**

| Migración | Descripción |
|---|---|
| `25c610b4119f` | Amplía `respuesta_dada` de `VARCHAR(1)` a `VARCHAR(500)` |
| `4b8c830edc2c` | Agrega columna `usuario_id` a tabla `notificaciones` |

**Tests:** +21 nuevos (207 → 228) — sin regresiones

---

### Sprint 12 — Perfil de usuario, notificaciones y fixes de contrato (207 tests)

**Solicitudes de Sharon y Santiago (equipo frontend):**

**Fixes de contrato de API:**

| Cambio | Descripción |
|---|---|
| `GET /capacitaciones/empleados/{id}/historial` | Fix de acceso: empleado ahora puede ver su propio historial (antes bloqueado con 403). SST sigue viendo cualquiera |
| `GET /capacitaciones/empleados/{id}/historial` | Response enriquecido: ahora incluye `capacitacion_nombre`, `fecha_sesion`, `evaluacion` completa con preguntas y `resultado` del empleado |
| `GET /auditorias/{id}/hallazgos` | Cada hallazgo ahora incluye `no_conformidades: []` anidadas — nunca `null` |

**Nuevos endpoints — Perfil de usuario:**

| Endpoint | Descripción |
|---|---|
| `PATCH /usuarios/me` | Edita `nombre` y `telefono` del propio usuario. Ignora rol, cargo y email |
| `PUT /usuarios/me/foto` | Sube o reemplaza foto de perfil (JPG/PNG/WEBP, máx 2 MB). Almacenada en Cloudinary |
| `GET /usuarios/me/actividad` | Historial paginado de acciones del usuario autenticado. Retención: 30 días |

**Nuevos endpoints — Notificaciones:**

| Endpoint | Descripción |
|---|---|
| `GET /notificaciones/feed` | Feed paginado de eventos de la empresa, del más reciente al más antiguo |
| `PATCH /notificaciones/{id}/leido` | Marca una notificación como leída |
| `PATCH /notificaciones/leer-todas` | Marca todas las notificaciones no leídas como leídas |

**Archivos nuevos:**

| Archivo | Descripción |
|---|---|
| `app/models/notificacion.py` | Modelo `Notificacion` con tabla `notificaciones` |
| `app/services/notificacion_service.py` | CRUD de notificaciones, purga automática de 30 días |
| `app/services/cloudinary_service.py` | Integración con Cloudinary para subir fotos de perfil |
| `app/routers/notificacion_router.py` | 3 endpoints de notificaciones |

**Archivos modificados:**

| Archivo | Cambio |
|---|---|
| `app/models/user.py` | Agrega columnas `telefono` y `foto_url` |
| `app/models/auditoria.py` | `lazy="selectin"` en relación `no_conformidades` de `Hallazgo` |
| `app/schemas/usuario_schema.py` | Agrega `PerfilUpdate`; añade `telefono` y `foto_url` a `UsuarioResponse` |
| `app/schemas/auditoria.py` | Agrega `no_conformidades: List[NoConformidadResponse]` a `HallazgoResponse` |
| `app/routers/usuario_router.py` | Agrega 3 endpoints de perfil propio |
| `app/routers/capacitacion_router.py` | Fix de acceso en historial + hooks de notificaciones en 4 endpoints |
| `app/routers/incidente_router.py` | Hooks de notificaciones en 5 endpoints |
| `app/routers/riesgo_router.py` | Hook de notificación en `POST /peligros` |
| `app/routers/auditoria_router.py` | Hooks de notificaciones en 2 endpoints |
| `app/services/capacitacion_service.py` | `get_historial_empleado` enriquecido con capacitación, evaluación y resultado |
| `main.py` | Registro de `notificacion_router` |
| `requirements.txt` | Agrega `cloudinary==1.44.2` |

**Migraciones aplicadas:**

| Migración | Descripción |
|---|---|
| `437083986d0b` | Agrega `telefono` y `foto_url` a tabla `users` |
| `7c80bdc74761` | Crea tabla `notificaciones` |

**Tests:** 207 — sin regresiones

---

### Sprint 11 — Integración Frontend III: incidentes y chat (207 tests)

**Solicitudes de Sharon y Santiago (equipo frontend):**

**Nuevos endpoints de incidentes:**

| Endpoint | Descripción |
|---|---|
| `GET /incidentes/{id}/investigacion` | Retorna la investigación del incidente. 404 si no existe |
| `PATCH /incidentes/{id}/investigacion` | Actualiza campos de una investigación existente. 404 si no existe |
| `GET /incidentes/{id}/acciones` | Lista todas las acciones correctivas. `[]` si no hay |

**Nuevos endpoints de chat (SASBOT):**

| Endpoint | Descripción |
|---|---|
| `POST /chat/escalar` | Envía historial de conversación al coordinador SST por correo vía Resend |
| `POST /chat/archivo` | Analiza PDF e imágenes con Gemini vision. DOC/DOCX retorna mensaje de conversión |

**Dependencia nueva:** `python-multipart>=0.0.9` — requerida para `multipart/form-data` en `/chat/archivo`

**Archivos modificados:**

| Archivo | Cambio |
|---|---|
| `app/schemas/incidente.py` | Agrega `InvestigacionUpdate` |
| `app/services/incidente_service.py` | Agrega `get_investigacion`, `get_acciones_correctivas`, `update_investigacion` |
| `app/routers/incidente_router.py` | Agrega 3 endpoints nuevos |
| `app/services/ai_service.py` | Agrega `analizar_archivo_sasbot` con Gemini vision |
| `app/services/email_service.py` | Agrega `enviar_escalar_coordinador` |
| `app/routers/chat_router.py` | Agrega `POST /chat/escalar` y `POST /chat/archivo` |
| `requirements.txt` | Agrega `python-multipart>=0.0.9` |

**Tests:** 207 — sin regresiones

---

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

*Documentación actualizada el 2026-06-10*
*Proyecto PISST — SENA*
