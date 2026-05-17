# PISST — Notas del Proyecto
**Plataforma Integral de Seguridad y Salud en el Trabajo**
*Documento personal — uso interno*

---

## Índice

1. [Visión General](#visión-general)
2. [Stack Técnico](#stack-técnico)
3. [Infraestructura](#infraestructura)
4. [Variables de Entorno](#variables-de-entorno)
5. [Estructura del Proyecto](#estructura-del-proyecto)
6. [Roles y Permisos](#roles-y-permisos)
7. [Módulos Implementados](#módulos-implementados)
8. [Endpoints Completos](#endpoints-completos)
9. [Modelos de Base de Datos](#modelos-de-base-de-datos)
10. [Flujo de Autenticación](#flujo-de-autenticación)
11. [Bugs Encontrados y Corregidos](#bugs-encontrados-y-corregidos)
12. [Deuda Técnica Pendiente](#deuda-técnica-pendiente)
13. [Decisiones de Diseño](#decisiones-de-diseño)

---

## Visión General

PISST es una API REST para gestión del SG-SST (Sistema de Gestión de Seguridad y Salud en el Trabajo) en empresas colombianas. El sistema maneja múltiples empresas (multi-tenant) con aislamiento por `empresa_id` en todas las consultas.

---

## Stack Técnico

| Componente | Tecnología | Versión |
|---|---|---|
| Framework | FastAPI | 0.136.1 |
| ORM | SQLAlchemy | 2.0.49 |
| Base de datos | PostgreSQL (Neon) | — |
| Driver DB | psycopg2-binary | 2.9.12 |
| Migraciones | Alembic | 1.18.4 |
| Autenticación | JWT (python-jose) | 3.5.0 |
| Hash contraseñas | bcrypt + passlib | 4.0.1 |
| Rate limiting | slowapi | 0.1.9 |
| Email | Resend (via httpx) | — |
| PDF | ReportLab | 4.5.0 |
| Excel | openpyxl | 3.1.5 |
| IA / Chat | Google Generative AI | 2.2.0 |
| Validación | Pydantic | 2.13.4 |
| Servidor | Uvicorn | 0.46.0 |

---

## Infraestructura

| Componente | Servicio |
|---|---|
| Backend API | Render |
| Base de datos | Neon (PostgreSQL serverless) |
| Frontend | Vercel |
| Email transaccional | Resend |

**Configuración de conexión a Neon:**
- `pool_pre_ping=True` — verifica conexión antes de usarla
- `pool_recycle=300` — renueva conexiones cada 5 minutos
- `sslmode=require` — Neon siempre requiere SSL

---

## Variables de Entorno

```env
# Base de datos
DATABASE_URL=postgresql://usuario:password@host/db

# JWT
SECRET_KEY=clave-secreta-larga
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Entorno
ENVIRONMENT=development   # o production

# Email (Resend)
RESEND_API_KEY=re_xxxxxxxxxxxx
FROM_EMAIL=noreply@tudominio.com

# Frontend
FRONTEND_URL=https://pisst-frontend.vercel.app

# Google reCAPTCHA
RECAPTCHA_SECRET_KEY=xxxxxxxxxxxx
```

> En `ENVIRONMENT=development` el reCAPTCHA se omite automáticamente.

---

## Estructura del Proyecto

```
PISST/
├── main.py                         # Punto de entrada, CORS, rate limiting global
├── requirements.txt
├── .env
└── app/
    ├── core/
    │   ├── database.py             # Engine SQLAlchemy, get_db()
    │   ├── security.py             # bcrypt, JWT encode/decode
    │   └── deps.py                 # get_current_user(), require_role()
    ├── models/
    │   ├── user.py                 # User, RoleEnum
    │   ├── empresa.py
    │   ├── area.py
    │   ├── cargo.py
    │   ├── incidente.py            # Incidente, enums de tipo/severidad/estado
    │   ├── investigacion.py
    │   ├── lesion.py
    │   ├── testigo.py
    │   ├── accion_correctiva.py
    │   ├── capacitacion.py         # Capacitacion, Sesion, Asistencia, Evaluacion, Pregunta, RespuestaEmpleado
    │   ├── riesgo.py
    │   ├── auditoria.py
    │   └── chat_historial.py
    ├── schemas/
    │   ├── usuario_schema.py
    │   ├── capacitacion.py
    │   ├── incidente.py
    │   ├── riesgo.py
    │   └── auditoria.py
    ├── routers/
    │   ├── auth_router.py          # /auth/*
    │   ├── usuario_router.py       # /usuarios/*
    │   ├── incidente_router.py     # /incidentes/*
    │   ├── capacitacion_router.py  # /capacitaciones/*
    │   ├── metricas_router.py      # /metricas/*
    │   ├── riesgo_router.py        # /riesgos/*
    │   ├── auditoria_router.py     # /auditorias/*
    │   └── chat_router.py          # /chat/*
    └── services/
        ├── email_service.py        # Resend: bienvenida + reset password
        ├── usuario_service.py
        ├── incidente_service.py
        ├── capacitacion_service.py # + generar_certificado()
        ├── metricas_service.py     # KPIs, dashboard, + generar_reporte_pdf/excel()
        ├── riesgo_service.py
        ├── auditoria_service.py
        ├── furat_service.py        # Genera FURAT en PDF
        └── chat_historial.py
```

---

## Roles y Permisos

El sistema tiene 3 roles definidos en `RoleEnum`:

| Rol | Descripción | Acceso |
|---|---|---|
| `sst` | Encargado de Seguridad y Salud en el Trabajo | Acceso total al sistema |
| `gerencia` | Gerente / directivo | Dashboard ejecutivo, reportes, métricas, lectura general |
| `empleado` | Trabajador de la empresa | Reportar incidentes, ver capacitaciones, responder evaluaciones |

**Implementación:** `require_role("sst")` o `require_role("sst", "gerencia")` en cada endpoint como `Depends`.

---

## Módulos Implementados

### 1. Autenticación (`/auth`)
- Login con JWT + reCAPTCHA + rate limiting (5 intentos/min por IP)
- Registro de usuarios (protegido — solo `sst`)
- Recuperación de contraseña vía Resend (token de 30 min)
- Reset de contraseña con validación de longitud mínima

### 2. Gestión de Usuarios (`/usuarios`)
- CRUD completo (solo `sst`)
- Al crear usuario: genera contraseña temporal aleatoria → envía correo de bienvenida con Resend
- El tenant está implícito: siempre se usa `empresa_id` del usuario autenticado
- Soft delete: campo `activo = False`

### 3. Gestión de Incidentes (`/incidentes`)
- Tipos: `accidente`, `incidente`, `cuasi_accidente`, `condicion_insegura`
- Severidad: `sin_lesion`, `leve`, `moderada`, `grave`, `mortal`
- Estados: `borrador → en_revision → abierto → en_investigacion → cerrado`
- No permite cerrar sin investigación documentada
- Genera **FURAT en PDF** (`/incidentes/{id}/furat`)
- Filtros por estado y tipo
- Acciones correctivas con fecha límite y evidencia obligatoria para cerrar

### 4. Capacitaciones (`/capacitaciones`)
- Capacitación → Sesiones → Asistencia → Evaluación → Preguntas → Respuestas
- El empleado responde la evaluación y el sistema calcula el puntaje automáticamente
- Genera **certificado PDF** si el empleado aprobó
- `puntaje_minimo` configurable por evaluación (default 60%)
- Registro de asistencia: `presente`, `ausente`, `justificado`

### 5. Métricas y Dashboard (`/metricas`)
- KPIs de accidentalidad (Tasa de Accidentalidad, Índice de Frecuencia, Índice de Severidad)
- Dashboard ejecutivo para Gerencia
- Alertas para SST (incidentes sin investigación, acciones vencidas)
- Exporta **reporte ejecutivo en PDF y Excel**
- Períodos válidos: `mensual`, `trimestral`, `anual`

### 6. Evaluación de Riesgos (`/riesgos`)
- Identificación de peligros
- Evaluación de riesgo: `probabilidad × severidad`
- Matriz de riesgos: `Bajo / Medio / Alto / Crítico`
- Medidas de control con evidencia obligatoria para cerrar

### 7. Auditorías (`/auditorias`)
- Planificación → Ejecución → Completada
- Hallazgos → No Conformidades
- % de progreso basado en NC cerradas

### 8. Chat IA (`/chat`)
- Chat con historial usando Google Generative AI

---

## Endpoints Completos

### Auth — `/auth`

| Método | Endpoint | Rol | Descripción |
|---|---|---|---|
| POST | `/auth/login` | Público | Login → JWT. Rate limit 5/min |
| POST | `/auth/register` | `sst` | Crea usuario con contraseña explícita |
| POST | `/auth/forgot-password` | Público | Genera token y envía correo |
| POST | `/auth/reset-password` | Público | Valida token y actualiza contraseña |

### Usuarios — `/usuarios`

| Método | Endpoint | Rol | Descripción |
|---|---|---|---|
| GET | `/usuarios/` | `sst` | Lista usuarios de la empresa |
| GET | `/usuarios/{id}` | `sst` | Detalle de un usuario |
| POST | `/usuarios/` | `sst` | Crea usuario + envía correo bienvenida |
| PATCH | `/usuarios/{id}` | `sst` | Actualiza nombre, área, cargo, activo |

### Incidentes — `/incidentes`

| Método | Endpoint | Rol | Descripción |
|---|---|---|---|
| GET | `/incidentes/` | Todos | Lista con filtros opcionales |
| POST | `/incidentes/` | Todos | Reporta un incidente |
| GET | `/incidentes/{id}` | Todos | Detalle completo |
| PATCH | `/incidentes/{id}/estado` | `sst` | Cambia estado del incidente |
| GET | `/incidentes/{id}/progreso` | Todos | % de acciones completadas |
| POST | `/incidentes/{id}/investigacion` | `sst` | Crea investigación de causas |
| POST | `/incidentes/{id}/acciones` | `sst` | Crea acción correctiva |
| PATCH | `/incidentes/acciones/{id}` | `sst` | Actualiza acción correctiva |
| GET | `/incidentes/{id}/furat` | `sst` | Descarga FURAT en PDF |

### Capacitaciones — `/capacitaciones`

| Método | Endpoint | Rol | Descripción |
|---|---|---|---|
| GET | `/capacitaciones/` | Todos | Lista capacitaciones |
| POST | `/capacitaciones/` | `sst` | Crea capacitación |
| GET | `/capacitaciones/cobertura` | `sst`, `gerencia` | % de cobertura del plan |
| POST | `/capacitaciones/sesiones` | `sst` | Programa sesión |
| GET | `/capacitaciones/{id}/sesiones` | Todos | Lista sesiones |
| POST | `/capacitaciones/asistencia` | `sst` | Registra asistencia |
| GET | `/capacitaciones/sesiones/{id}/asistencia` | `sst` | Asistencia de una sesión |
| GET | `/capacitaciones/empleados/{id}/historial` | `sst` | Historial del empleado |
| POST | `/capacitaciones/evaluaciones` | `sst` | Crea evaluación con preguntas |
| POST | `/capacitaciones/evaluaciones/responder` | Todos | Empleado responde evaluación |
| GET | `/capacitaciones/evaluaciones/{id}/certificado/{empleado_id}` | Todos | Descarga certificado PDF |

### Métricas — `/metricas`

| Método | Endpoint | Rol | Descripción |
|---|---|---|---|
| GET | `/metricas/kpis` | `sst`, `gerencia` | KPIs de accidentalidad |
| GET | `/metricas/dashboard-gerencia` | `sst`, `gerencia` | Resumen ejecutivo completo |
| GET | `/metricas/alertas` | `sst` | Alertas activas |
| GET | `/metricas/reporte-pdf?periodo=mensual` | `sst`, `gerencia` | Reporte PDF |
| GET | `/metricas/reporte-excel?periodo=mensual` | `sst`, `gerencia` | Reporte Excel |

> Períodos válidos: `mensual`, `trimestral`, `anual`

### Riesgos — `/riesgos`

| Método | Endpoint | Rol | Descripción |
|---|---|---|---|
| GET | `/riesgos/peligros` | Todos | Lista peligros (filtros: tipo, area_id) |
| POST | `/riesgos/peligros` | `sst` | Crea peligro |
| GET | `/riesgos/peligros/{id}` | Todos | Detalle del peligro |
| POST | `/riesgos/peligros/{id}/evaluar` | `sst` | Evalúa nivel de riesgo |
| GET | `/riesgos/matriz` | `sst`, `gerencia` | Matriz de riesgos |
| POST | `/riesgos/peligros/{id}/controles` | `sst` | Crea medida de control |
| PATCH | `/riesgos/controles/{id}` | `sst` | Actualiza medida de control |

### Auditorías — `/auditorias`

| Método | Endpoint | Rol | Descripción |
|---|---|---|---|
| GET | `/auditorias/` | `sst`, `gerencia` | Lista auditorías |
| POST | `/auditorias/` | `sst` | Planifica auditoría |
| PATCH | `/auditorias/{id}/estado` | `sst` | Cambia estado |
| GET | `/auditorias/{id}/progreso` | `sst`, `gerencia` | % NC cerradas |
| POST | `/auditorias/{id}/hallazgos` | `sst` | Registra hallazgo |
| GET | `/auditorias/{id}/hallazgos` | `sst`, `gerencia` | Lista hallazgos |
| POST | `/auditorias/hallazgos/{id}/nc` | `sst` | Crea no conformidad |
| PATCH | `/auditorias/nc/{id}` | `sst` | Actualiza no conformidad |

---

## Modelos de Base de Datos

### `users`
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID PK | auto uuid4 |
| nombre | String(200) | |
| email | String(255) | unique |
| password_hash | String(255) | bcrypt |
| role | Enum | sst / gerencia / empleado |
| empresa_id | UUID FK | → empresas |
| area_id | UUID FK | → areas, nullable |
| cargo_id | UUID FK | → cargos, nullable |
| activo | Boolean | default True |
| fecha_creacion | DateTime | |
| reset_token | String(255) | nullable |
| reset_token_expira | DateTime | nullable |

### `incidentes`
| Campo | Tipo | Notas |
|---|---|---|
| tipo | Enum | accidente / incidente / cuasi_accidente / condicion_insegura |
| severidad | Enum | sin_lesion / leve / moderada / grave / mortal |
| estado | Enum | borrador → en_revision → abierto → en_investigacion → cerrado |
| empresa_id | UUID FK | multi-tenant |
| trabajador_afectado_id | UUID FK | nullable |
| reportado_por_id | UUID FK | |

### `capacitaciones` → `sesiones_capacitacion` → `evaluaciones` → `preguntas` → `respuestas_empleado`

**`respuestas_empleado`** — una fila por respuesta dada:
| Campo | Tipo | Notas |
|---|---|---|
| respuesta_dada | String(1) | "a", "b", "c" o "d" |
| es_correcta | Boolean | por pregunta |
| puntaje_final | Integer | % total de la evaluación (mismo valor en todas las filas del mismo intento) |
| aprobado | Boolean | True si puntaje >= puntaje_minimo |
| fecha_respuesta | DateTime | |

> El `puntaje_final` y `aprobado` se calculan en `responder_evaluacion()` y se actualizan con un bulk update en todas las filas del intento. El certificado consulta por `aprobado == True`.

---

## Flujo de Autenticación

```
1. POST /auth/login
   └── Valida reCAPTCHA (omitido en development)
   └── Busca usuario activo por email
   └── verify_password(plain, hash) — bcrypt
   └── create_access_token({sub: user.id, role: user.role})
   └── Retorna JWT

2. Endpoints protegidos
   └── Header: Authorization: Bearer <token>
   └── HTTPBearer extrae el token
   └── decode_token() → payload
   └── Busca User activo por payload["sub"]
   └── require_role() verifica user.role.value in allowed_roles

3. POST /auth/forgot-password
   └── Genera secrets.token_urlsafe(32)
   └── Guarda reset_token + reset_token_expira (30 min) en el User
   └── Envía correo con enlace via Resend
   └── SIEMPRE retorna mensaje genérico (no revela si el email existe)

4. POST /auth/reset-password
   └── Valida longitud mínima (6 chars)
   └── Busca User por reset_token
   └── Verifica reset_token_expira > now()
   └── Actualiza password_hash, limpia reset_token y reset_token_expira
```

---

## Bugs Encontrados y Corregidos

> Revisión completa realizada el 16/05/2026

### Bug #1 — CRÍTICO | `capacitacion_service.py`
**Certificado PDF completamente inoperativo**

`responder_evaluacion()` creaba una fila por pregunta pero nunca persistía `puntaje_final` ni `aprobado` en esas filas (quedaban en defaults 0/False). `generar_certificado()` filtraba por `aprobado == True` → siempre retornaba 404.

**Fix:** Al final de `responder_evaluacion()`, bulk update de todas las filas del intento:
```python
db.query(RespuestaEmpleado).filter(
    RespuestaEmpleado.evaluacion_id == datos.evaluacion_id,
    RespuestaEmpleado.empleado_id == empleado_id
).update({"puntaje_final": puntaje, "aprobado": aprobado})
db.commit()
```

---

### Bug #2 — CRÍTICO | `auth_router.py`
**`/auth/register` público — cualquier anónimo podía crear usuarios con cualquier rol**

El endpoint no tenía autenticación. Cualquier persona sin cuenta podía crear un usuario `sst` o `gerencia`.

**Fix:** Agregado `current_user: User = Depends(require_role("sst"))` + conversión con `RoleEnum(datos.role)` envuelto en try/except.

---

### Bug #3 — ALTO | `usuario_service.py`
**Usuario bloqueado si el correo de bienvenida fallaba**

El usuario se guardaba en BD (`db.commit()`) antes de enviar el correo. Si Resend fallaba, el usuario existía en el sistema con una contraseña temporal desconocida y sin forma de entrar.

**Fix:** Capturar el retorno de `enviar_correo_bienvenida()` y loguear si falla — sin exponer la contraseña en el log.
```python
enviado = enviar_correo_bienvenida(...)
if not enviado:
    print(f"⚠️ Correo no enviado a {nuevo_usuario.email} — administrador debe resetear contraseña")
```

---

### Bug #4 — ALTO | `auth_router.py`
**Anti-enumeración rota en `forgot-password`**

Si el correo existía pero Resend fallaba, se lanzaba un `HTTPException(500)` — lo que implícitamente revelaba que ese email SÍ estaba registrado (si no existiera, habría retornado 200 antes).

**Fix:** Siempre retornar `mensaje_generico`, loguear el error internamente.

---

### Bug #5 — ALTO | `metricas_service.py`
**División por cero el 1° de enero**

```python
# Antes: solo protegía si total_trabajadores == 0
horas_trabajadas = total_trabajadores * 8 * dias_transcurridos if total_trabajadores > 0 else 1
# Si total_trabajadores > 0 pero dias_transcurridos == 0 → horas_trabajadas = 0 → ZeroDivisionError
```

**Fix:**
```python
horas_trabajadas = total_trabajadores * 8 * dias_transcurridos
horas_trabajadas = horas_trabajadas if horas_trabajadas > 0 else 1
```

---

### Bug #6 — ALTO | `metricas_router.py`
**`periodo` sin validar en el header `Content-Disposition`**

El parámetro llegaba directo al nombre del archivo sin validación. Permitía manipular el header HTTP.

**Fix:** Definir lista permitida y validar al inicio de ambos endpoints:
```python
PERIODOS_VALIDOS = ["mensual", "trimestral", "anual"]
if periodo not in PERIODOS_VALIDOS:
    raise HTTPException(status_code=400, detail="Período inválido.")
```

---

### Bug #7 — MEDIO | `usuario_service.py`
**Contraseña temporal impresa en los logs de producción**

Al capturar el error del correo, el mensaje original incluía la contraseña temporal en texto plano, visible en los logs de Render.

**Fix:** Eliminar la contraseña del mensaje del log.

---

### Bug #8 — SINTAXIS | `usuario_service.py`
**`IndentationError` — `print` fuera del bloque `if`**

```python
# Mal
if not enviado:
print(...)   # 4 espacios en lugar de 8

# Correcto
if not enviado:
    print(...)
```

El app no arrancaba con este error.

---

## Deuda Técnica Pendiente

Estos problemas **no rompen producción** pero deben corregirse en la próxima iteración:

### 1. `metricas_service.py` línea 17 — Comparación enum con string
```python
# Actual (funciona pero frágil)
User.role == "empleado"

# Correcto
from app.models.user import RoleEnum   # ya importado en el archivo
User.role == RoleEnum.empleado
```

### 2. `usuario_schema.py` — `RolEnum` duplicado
Existe `RolEnum` en el schema Y `RoleEnum` en el modelo. Si en el futuro se agrega un nuevo rol en uno y se olvida el otro, habrá bugs silenciosos. Consolidar en uno solo usando `RoleEnum` del modelo.

### 3. `usuario_router.py` línea 8 — Import innecesario
```python
from app.core.deps import get_current_user, require_role
# get_current_user nunca se usa directamente en este router — eliminar
```

---

## Decisiones de Diseño

### Multi-tenancy por `empresa_id`
Todas las consultas filtran por `current_user.empresa_id`. Nunca se exponen datos de otras empresas. El `empresa_id` viene del token JWT, no del request — el cliente no puede manipularlo.

### Contraseña temporal en creación de usuario
Al crear un usuario desde `/usuarios/`, el SST no define la contraseña — el sistema genera una aleatoria de 10 caracteres alfanuméricos y la envía por correo. El usuario debe cambiarla en su primer login (pendiente de implementar el forzado en frontend).

### Dos endpoints de creación de usuario
- `/auth/register` — el SST define la contraseña explícitamente. No envía correo.
- `/usuarios/` POST — el sistema genera contraseña temporal y envía correo.

Ambos requieren autenticación `sst`. Son dos flujos distintos para dos necesidades distintas.

### `RespuestaEmpleado` — una fila por pregunta
El modelo guarda una fila por cada respuesta individual. El `puntaje_final` y `aprobado` se repiten en todas las filas del mismo intento (redundante pero necesario para que `generar_certificado` pueda encontrar el registro con un solo query).

### Tokens de reset de contraseña en columnas del User
Los campos `reset_token` y `reset_token_expira` están directamente en el modelo `User` en lugar de una tabla separada. Es suficiente para el volumen esperado y simplifica las consultas.

### `slowapi` rate limiting
El limiter global se define en `main.py` y se adjunta a `app.state.limiter`. El router `auth_router.py` define su propio `limiter` local para el decorator `@limiter.limit("5/minute")` del login — funciona correctamente porque el exception handler en `main.py` captura `RateLimitExceeded` de cualquier limiter.

### Mensaje genérico en forgot-password
`/auth/forgot-password` siempre retorna el mismo mensaje sin importar si el email existe, si el correo se envió correctamente, o si falló. Esto previene que un atacante pueda enumerar qué emails están registrados en el sistema.
