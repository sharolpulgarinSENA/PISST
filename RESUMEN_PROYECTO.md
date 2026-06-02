# PISST — Resumen General del Proyecto
## Plataforma Integral de Seguridad y Salud en el Trabajo

**Versión:** 1.0 | **Fecha:** 2026-05-31 | **Estado:** Producción

---

## Tabla de Contenidos

1. [¿Qué es PISST?](#1-qué-es-pisst)
2. [Arquitectura del Backend](#2-arquitectura-del-backend)
3. [Módulos y Funcionalidades](#3-módulos-y-funcionalidades)
4. [Cronología de Desarrollo](#4-cronología-de-desarrollo)
5. [Cobertura de Tests y Calidad](#5-cobertura-de-tests-y-calidad)
6. [Lecciones Aprendidas y Decisiones Técnicas](#6-lecciones-aprendidas-y-decisiones-técnicas)
7. [Próximos Pasos y Recomendaciones](#7-próximos-pasos-y-recomendaciones)

---

## 1. ¿Qué es PISST?

PISST es una plataforma web para digitalizar la gestión del **Sistema de Gestión de Seguridad y Salud en el Trabajo (SG-SST)** en empresas colombianas, en cumplimiento del **Decreto 1072 de 2015** y la **Resolución 0312 de 2019**.

### Problema que resuelve

Las empresas gestionan su SG-SST en papel o en hojas de cálculo dispersas, lo que genera:
- Tiempos de respuesta lentos ante incidentes laborales
- Dificultad para hacer seguimiento de acciones correctivas
- Falta de trazabilidad en auditorías y capacitaciones
- Incumplimiento normativo por falta de registros formales

PISST centraliza todo esto en una sola plataforma con roles diferenciados, alertas inteligentes y generación automática de documentos oficiales (FURAT, certificados, reportes ejecutivos).

### Usuarios del sistema

| Rol | Responsabilidad |
|-----|----------------|
| `admin` | Crea empresas y sus usuarios SST y Gerencia |
| `sst` | Gestiona incidentes, riesgos, capacitaciones, auditorías y reportes |
| `gerencia` | Consulta dashboards, KPIs e informes ejecutivos |
| `empleado` | Reporta incidentes, participa en capacitaciones, usa el chat SASBOT |

---

## 2. Arquitectura del Backend

### 2.1 Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Lenguaje | Python 3.12 |
| Framework | FastAPI 0.136.x |
| ORM | SQLAlchemy 2.0 |
| Validación | Pydantic v2 |
| Base de datos | PostgreSQL 16 (Neon cloud) |
| Autenticación | JWT (python-jose) + bcrypt |
| Migraciones | Alembic |
| Rate limiting | SlowAPI |
| PDF | ReportLab |
| Excel | openpyxl |
| IA | Google Gemini |
| Correo | Resend |
| Hosting | Render (backend) + Vercel (frontend) |

### 2.2 Arquitectura en capas

El backend sigue una **arquitectura en capas estricta** que separa responsabilidades:

```
HTTP Request
     │
┌────────────┐
│  Routers   │  → Parseo de request, validación Pydantic, control de roles,
│            │    serialización de respuesta. Sin lógica de negocio.
└─────┬──────┘
      │
┌────────────┐
│  Services  │  → Toda la lógica de dominio: reglas de negocio,
│            │    validaciones complejas, integración con externos.
└─────┬──────┘
      │
┌────────────┐
│   Models   │  → Definición de tablas, relaciones, constraints e índices.
│ (SQLAlchemy)│   Nunca contienen lógica de negocio.
└─────┬──────┘
      │
┌────────────┐
│ PostgreSQL │  → Base de datos relacional en Neon (cloud serverless).
└────────────┘
```

Adicionalmente:
- **`app/schemas/`** — DTOs Pydantic: validan entrada y serializan salida
- **`app/core/`** — Infraestructura transversal: BD, JWT, dependencias de autenticación

### 2.3 Estructura de carpetas

```
PISST/
├── main.py                  # Punto de entrada: app FastAPI, middlewares, routers
├── app/
│   ├── core/
│   │   ├── database.py      # Conexión SQLAlchemy, get_db
│   │   ├── security.py      # JWT, hashing de contraseñas, validación de fortaleza
│   │   └── deps.py          # get_current_user, require_role — dependencias de auth
│   ├── models/              # 13 modelos SQLAlchemy (tablas de BD)
│   ├── schemas/             # DTOs Pydantic por módulo
│   ├── routers/             # 11 routers FastAPI (endpoints HTTP)
│   └── services/            # 12 servicios con lógica de negocio
├── tests/                   # 12 archivos de tests, 176 tests
├── alembic/                 # Migraciones de BD
└── DOCUMENTACION_TECNICA.md
```

### 2.4 Modelo de datos — entidades principales

```
Empresa
  ├── Users (empleados, SST, gerencia)
  │     ├── Area (pertenece a)
  │     └── Cargo (tiene)
  ├── Incidentes
  │     ├── Lesion (1:1)
  │     ├── Testigos (1:N)
  │     ├── Investigacion (1:1)
  │     └── AccionesCorrectivas (1:N)
  ├── Peligros
  │     ├── EvaluacionesRiesgo (1:N)
  │     └── MedidasControl (1:N)
  ├── Capacitaciones
  │     ├── Sesiones (1:N)
  │     │     ├── Asistencias (1:N)
  │     │     └── Evaluaciones (1:1)
  │     │           ├── Preguntas (1:N)
  │     │           └── RespuestasEmpleado (1:N)
  ├── Auditorias
  │     └── Hallazgos (1:N)
  │           └── NoConformidades (1:N)
  └── AuditLogs (trazabilidad de acciones críticas)
```

### 2.5 Seguridad

| Mecanismo | Implementación |
|-----------|---------------|
| Autenticación | JWT access token (30 min) + refresh token (7 días) |
| Sesión única | `session_token` en BD invalidado en logout o nuevo login |
| Bloqueo de cuenta | 5 intentos fallidos → bloqueo 5 minutos |
| Multi-tenancy | Toda query filtra por `empresa_id` del JWT |
| Roles | `require_role()` en cada endpoint protegido |
| Contraseñas | Validación de fortaleza (8+ chars, mayúscula, minúscula, número, símbolo) |
| Primer login | `debe_cambiar_password=True` fuerza cambio antes de usar la app |
| Admin | Header `X-Admin-Key` adicional para endpoints de administración |
| reCAPTCHA | Validado en login antes de consultar la BD |
| Rate limiting | SlowAPI por token de usuario |

---

## 3. Módulos y Funcionalidades

### 3.1 Autenticación (`/auth/*`)

| Endpoint | Función |
|----------|---------|
| `POST /auth/login` | Login con email/password + reCAPTCHA. Devuelve JWT + refresh token |
| `POST /auth/refresh` | Renueva access token usando refresh token |
| `POST /auth/logout` | Invalida refresh token y session token en BD |
| `POST /auth/cambiar-password` | Cambia contraseña validando sesión activa |
| `POST /auth/forgot-password` | Genera token de reset y envía correo |
| `POST /auth/reset-password` | Aplica nueva contraseña con token válido |

### 3.2 Usuarios (`/usuarios/*`)

| Endpoint | Función |
|----------|---------|
| `GET /usuarios/` | Lista usuarios. Acepta `?activo=true\|false` (sin parámetro: todos). Incluye `area_nombre` y `cargo_nombre` |
| `GET /usuarios/{id}` | Detalle de un usuario |
| `POST /usuarios/` | Crea empleado con área y cargo. Genera contraseña temporal y envía correo |
| `PATCH /usuarios/{id}` | Actualiza nombre, área, cargo o estado activo |

### 3.3 Incidentes y FURAT (`/incidentes/*`)

Ciclo de vida: `borrador → en_revision → abierto → en_investigacion → cerrado`

| Endpoint | Función |
|----------|---------|
| `GET /incidentes/` | Lista incidentes con filtros por estado y tipo |
| `POST /incidentes/` | Crea incidente con lesión y testigos opcionales |
| `PATCH /incidentes/{id}/estado` | Cambia estado (no permite cerrar sin investigación) |
| `POST /incidentes/{id}/investigacion` | Registra causas inmediatas, básicas y lecciones |
| `POST /incidentes/{id}/acciones` | Crea acción correctiva con responsable y fecha límite |
| `PATCH /incidentes/acciones/{id}` | Actualiza acción (requiere evidencia para completar) |
| `GET /incidentes/{id}/progreso` | % de acciones correctivas completadas |
| `GET /incidentes/{id}/furat` | Genera y descarga el PDF del formulario oficial FURAT |

### 3.4 Riesgos (`/riesgos/*`)

| Endpoint | Función |
|----------|---------|
| `GET /riesgos/peligros` | Lista peligros activos con filtros por tipo y área |
| `POST /riesgos/peligros` | Crea peligro con tipo, actividad y trabajadores expuestos |
| `POST /riesgos/peligros/{id}/evaluaciones` | Evalúa riesgo: probabilidad × severidad → nivel automático |
| `GET /riesgos/matriz` | Matriz de calor agrupada por nivel (bajo/medio/alto/crítico) |
| `POST /riesgos/peligros/{id}/medidas` | Crea medida de control con jerarquía EPP/administrativa/ingeniería |
| `PATCH /riesgos/medidas/{id}` | Actualiza medida (requiere evidencia para completar) |

### 3.5 Capacitaciones (`/capacitaciones/*`)

| Endpoint | Función |
|----------|---------|
| `GET /capacitaciones/` | Lista programas activos de la empresa |
| `POST /capacitaciones/` | Crea programa con título, objetivos y áreas asociadas |
| `POST /capacitaciones/{id}/sesiones` | Programa una sesión con fecha y lugar |
| `POST /capacitaciones/asistencia` | Registra asistencia por empleado (upsert) |
| `POST /capacitaciones/evaluaciones` | Crea evaluación con preguntas de opción múltiple |
| `POST /capacitaciones/evaluaciones/{id}/responder` | Empleado responde — calificación automática |
| `GET /capacitaciones/evaluaciones/{id}/certificado` | Descarga certificado PDF si el empleado aprobó |
| `GET /capacitaciones/cobertura` | % del plan anual de capacitaciones con sesiones |

### 3.6 Auditorías (`/auditorias/*`)

Ciclo de vida: `planificada → en_ejecucion → completada`

| Endpoint | Función |
|----------|---------|
| `POST /auditorias/` | Planifica auditoría con fecha, objetivos y auditor |
| `PATCH /auditorias/{id}/estado` | Cambia estado (registra fecha de ejecución automáticamente) |
| `POST /auditorias/{id}/hallazgos` | Registra hallazgo clasificado (conformidad/NC menor/NC mayor) |
| `POST /auditorias/hallazgos/{id}/no-conformidades` | Crea NC con responsable y fecha límite |
| `PATCH /auditorias/no-conformidades/{id}` | Cierra NC con evidencia de la acción tomada |
| `GET /auditorias/{id}/progreso` | % de no conformidades cerradas |

### 3.7 Métricas (`/metricas/*`)

| Endpoint | Función |
|----------|---------|
| `GET /metricas/kpis` | Tasa de accidentalidad, índice de frecuencia, índice de severidad |
| `GET /metricas/dashboard` | Dashboard gerencia: KPIs + incidentes activos + cumplimiento SG-SST |
| `GET /metricas/alertas` | Alertas activas: incidentes sin investigar, acciones vencidas/próximas |
| `GET /metricas/reporte-pdf` | Reporte ejecutivo en PDF por período (mensual/trimestral/anual) |
| `GET /metricas/reporte-excel` | Mismo reporte exportado a .xlsx |

### 3.8 Chat IA — SASBOT (`/chat/*`)

| Endpoint | Función |
|----------|---------|
| `POST /chat/mensaje` | Envía mensaje al asistente contextualizado con área y cargo del empleado |
| `POST /chat/reporte-rapido` | Empleado reporta incidente directamente desde el chat |
| `GET /chat/historial` | Historial paginado de conversaciones del usuario |

### 3.9 Administración (`/admin/*`)

Todos requieren header `X-Admin-Key`.

| Endpoint | Función |
|----------|---------|
| `POST /admin/empresas` | Registra nueva empresa (NIT único) |
| `GET /admin/empresas` | Lista todas las empresas del sistema |
| `POST /admin/crear-sst` | Crea el SST de una empresa (máximo 1 activo) |
| `POST /admin/crear-gerencia` | Crea el Gerencia de una empresa (máximo 1 activo) |
| `POST /admin/limpiar-tokens` | Limpia refresh y session tokens caducados |

---

## 4. Cronología de Desarrollo

### Sprint 4 — Fundamentos de producción

**Objetivo:** Llevar el proyecto a un estado apto para producción.

- Corrección de aislamiento multi-tenant en `/auth/register`
- Refresh tokens (access 30 min + refresh 7 días)
- Cambio de contraseña obligatorio en primer login (`debe_cambiar_password`)
- Health check con verificación real de BD
- Paginación en todos los endpoints de listado
- Tabla `audit_logs` para trazabilidad
- Corrección de bugs: Enum vs string en queries SQL, `datetime.utcnow()` deprecado
- Migración a Pydantic v2 y SQLAlchemy 2.0
- 3 índices compuestos en BD para rendimiento
- **11 tests automatizados, CI/CD con GitHub Actions**

### Revisión técnica — Seguridad y roles

**Objetivo:** Fortalecer la seguridad y afinar el control de acceso.

- Logout real que invalida tokens en BD
- Emails enmascarados en logs (`b*****@empresa.com`)
- CVEs resueltos en starlette, urllib3, idna
- SST restringido a crear solo empleados
- Máximo 1 SST y 1 Gerencia activos por empresa
- Handler global de errores (formato consistente en toda la API)
- Dependabot activo para alertas de CVEs
- `POST /admin/limpiar-tokens` para mantenimiento

### Sprint 5 — Arquitectura de servicios y cobertura base

**Objetivo:** Separar lógica de negocio en servicios y establecer la base de tests.

- **Extracción de `auth_service.py`**: toda la lógica de auth movida del router al servicio. Router queda solo con schemas y delegación.
- **Fix de seguridad crítico**: `/cambiar-password` no validaba `session_token` — un JWT revocado podía usarse para cambiar la contraseña. Corregido validando `session_id` contra la BD.
- **+83 tests**: auth_service, incidente_service, riesgo_service, capacitacion_service
- **Cobertura: 64% → 74%**

### Sprint 6 — Cobertura de auditorías y usuarios + Feature Sharon

**Objetivo:** Cubrir servicios restantes y atender solicitud del frontend.

- Tests de `auditoria_service` (21% → 100%): auditorías, hallazgos, no conformidades, progreso
- Tests de `usuario_service` (36% → 99%): crear con área/cargo, validaciones, correo, update
- **Feature `/usuarios/`** solicitada por Sharon:
  - `GET /usuarios/?activo=true|false` filtra por estado; sin parámetro devuelve todos
  - Respuesta incluye `area_nombre` y `cargo_nombre` listos para mostrar en el frontend
- **+34 tests | Cobertura: 74% → 79%**

### Sprint 7 — Cobertura de admin y FURAT

**Objetivo:** Cubrir el router de administración y el generador del FURAT.

- Tests de `admin_router` (47% → 97%): todos los endpoints con sus casos de error, clave incorrecta, duplicados, correo fallido
- Tests de `furat_service` (17% → 100%): PDF válido con distintos escenarios (con/sin lesión, con/sin investigación, con/sin trabajador)
- **+22 tests | Cobertura: 79% → 84%**

### Sprint 8 — Cobertura de métricas

**Objetivo:** Cubrir el servicio más complejo — KPIs, alertas y generación de reportes.

- Tests de `metricas_service` (16% → 100%):
  - KPIs: tasa de accidentalidad, índice de frecuencia, índice de severidad, días perdidos
  - Dashboard: cumplimiento, incidentes activos, acciones vencidas
  - Alertas: incidente sin investigación, acción vencida, acción próxima — y casos negativos
  - PDF y Excel: validación de estructura y firma de archivo
- **+20 tests | Cobertura: 84% → 90%**

---

## 5. Cobertura de Tests y Calidad

### 5.1 Estado actual

| Métrica | Valor |
|---------|-------|
| Tests totales | 176 |
| Tests pasando | 176 (100%) |
| Cobertura global | 90% |
| Servicios a 100% | auth, incidente, riesgo, auditoria, furat, metricas, audit |

### 5.2 Tipos de tests

**Tests de servicio** (la mayoría): prueban las funciones del servicio directamente con una sesión de BD SQLite. Son rápidos, aislados y fáciles de mantener.

```python
# Ejemplo: test unitario de servicio
def test_cambiar_password_session_invalida(db, empresa):
    user = make_user(db, empresa, session_token=secrets.token_hex(32))
    with pytest.raises(HTTPException) as exc:
        auth_service.cambiar_password(str(user.id), "token-incorrecto", ...)
    assert exc.value.status_code == 401
```

**Tests de endpoint HTTP**: usan `TestClient` de FastAPI para probar el flujo completo incluyendo autenticación, schemas y serialización.

```python
# Ejemplo: test HTTP de admin
def test_crear_sst_duplicado(client):
    empresa_id = nueva_empresa(client)
    with patch("app.routers.admin_router.enviar_correo_bienvenida", return_value=True):
        client.post("/admin/crear-sst", json={...}, headers=h())
        resp = client.post("/admin/crear-sst", json={...}, headers=h())
    assert resp.status_code == 400
```

### 5.3 Archivos de tests

| Archivo | Módulo | Tests |
|---------|--------|-------|
| `test_auth.py` | Endpoints HTTP de auth | 5 |
| `test_auth_service.py` | Lógica de autenticación | 25 |
| `test_incidente_service.py` | Incidentes, investigaciones, acciones | 18 |
| `test_riesgo_service.py` | Peligros, evaluaciones, medidas | 18 |
| `test_capacitacion_service.py` | Capacitaciones, sesiones, asistencia, evaluaciones | 22 |
| `test_auditoria_service.py` | Auditorías, hallazgos, no conformidades | 18 |
| `test_usuario_service.py` | Usuarios — CRUD, área, cargo, filtros | 26 |
| `test_admin_router.py` | Endpoints HTTP de administración | 16 |
| `test_furat_service.py` | Generación PDF FURAT | 6 |
| `test_metricas_service.py` | KPIs, dashboard, alertas, PDF, Excel | 20 |
| `test_metricas.py` | Endpoints HTTP de métricas | 2 |
| `test_usuarios.py` | Endpoints HTTP de usuarios | 6 |

### 5.4 Cómo correr los tests

```bash
# Todos los tests
.\venv\Scripts\python.exe -m pytest

# Con cobertura
.\venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing -q

# Un archivo específico
.\venv\Scripts\python.exe -m pytest tests/test_auth_service.py -v
```

Los tests usan **SQLite en memoria** — no requieren conexión a Neon ni variables de entorno.

### 5.5 Herramientas de calidad de código

Configuradas como **pre-commit hooks** — se ejecutan automáticamente antes de cada commit:

| Herramienta | Función |
|-------------|---------|
| `black` | Formateo automático del código Python |
| `isort` | Ordenamiento automático de imports |
| `flake8` | Linting: detecta imports sin usar, errores de estilo |

Ningún commit llega al repositorio sin pasar los tres.

---

## 6. Lecciones Aprendidas y Decisiones Técnicas

### 6.1 Separación estricta de capas — la decisión más importante

**Decisión:** toda la lógica de negocio vive en `app/services/`, los routers solo orquestan HTTP.

**Por qué importa:** al extraer `auth_service.py` en el Sprint 5, se descubrió un bug de seguridad que habría sido muy difícil de detectar en un router monolítico. La separación también hizo posible testear la lógica directamente sin levantar el servidor HTTP.

**Regla aplicada:** si una función tiene más de una línea de lógica, va al servicio.

### 6.2 Transacciones atómicas — el patrón de audit_service

**Situación:** `audit_service.registrar_auditoria()` no llama a `db.commit()`. Esto es intencional.

**Explicación:** el log de auditoría se agrega a la sesión activa y el `commit()` lo hace el servicio que llama. Así el log y la operación principal se persisten en la **misma transacción** — si la operación falla, el log también hace rollback.

**Lección:** siempre entender el contexto de transacciones antes de concluir que falta un commit.

### 6.3 UUID explícito para compatibilidad SQLite/PostgreSQL

**Problema:** SQLAlchemy con `UUID(as_uuid=True)` en PostgreSQL acepta strings en queries, pero SQLite los rechaza con `AttributeError: 'str' object has no attribute 'hex'`.

**Solución:** convertir explícitamente el `user_id` string a `UUID(user_id)` en el servicio antes de la query. Esto además hace el código semánticamente correcto.

**Lección:** los tests con SQLite son más estrictos que PostgreSQL en tipado — lo que es un beneficio, no un problema.

### 6.4 Validación de session_token en cambiar-password

**Problema:** `/cambiar-password` no usaba `get_current_user` (intencional — para usuarios con `debe_cambiar_password=True`). Pero al saltarse esa dependencia, se perdía la validación de `session_token`.

**Consecuencia sin corrección:** un JWT revocado podía usarse para cambiar la contraseña — account takeover potencial.

**Solución:** extraer `session_id` del JWT en el router y pasarlo al servicio, que lo valida contra la BD.

**Lección:** cuando se hace un bypass de dependencias de seguridad, hay que auditar qué se está salteando y compensar explícitamente.

### 6.5 Propiedades ORM para campos derivados

**Necesidad:** el frontend necesitaba `area_nombre` y `cargo_nombre` en la respuesta de usuarios.

**Decisión:** agregar `@property` al modelo `User`. Pydantic con `from_attributes=True` los lee automáticamente. Consistente con el patrón que ya usaba el modelo `Cargo`.

### 6.6 Mockear servicios externos en tests

**Patrón establecido:** los tests nunca llaman a servicios externos reales (correo, reCAPTCHA, Gemini). Se mockean con `unittest.mock.patch`.

El mock de correo fallido (`return_value=False`) verifica que el sistema no explota cuando el correo falla — el usuario se crea igual y solo se loguea un warning.

---

## 7. Próximos Pasos y Recomendaciones

### 7.1 Cobertura pendiente

| Módulo | Cobertura | Recomendación |
|--------|-----------|---------------|
| `email_service` | 32% | Mock de la librería Resend |
| `deps.py` | 38% | Tests HTTP con JWT válidos |
| `ai_service` | 44% | Mock de la respuesta de Gemini |

### 7.2 Mejoras técnicas recomendadas

- **Paginación con metadatos:** devolver `total`, `pagina_actual`, `total_paginas` en endpoints de listado
- **Refresh token rotation:** al usar el refresh token, generar uno nuevo e invalidar el anterior
- **Rate limiting por endpoint:** más restrictivo en `/auth/login` que en el resto
- **Soft delete consistente:** estandarizar campo `activo` en todos los modelos

### 7.3 Escalabilidad

- **Caché de métricas:** los KPIs se calculan en tiempo real. Para volúmenes altos, cachear por empresa 5-10 minutos con Redis
- **Workers async:** las generaciones de PDF/Excel son síncronas. Para archivos grandes, moverlas a background con FastAPI BackgroundTasks
- **Índices adicionales:** agregar índices en `fecha_creacion` de incidentes y auditorías para consultas por rango de fechas

### 7.4 Para el equipo de frontend

- `GET /usuarios/` devuelve `area_nombre` y `cargo_nombre` — no necesitan resolver IDs adicionales
- `?activo=true|false` filtra usuarios; sin parámetro devuelve todos
- Todos los errores tienen formato uniforme: `{ "detail": "...", "status_code": N }`
- Los reportes PDF/Excel se descargan como streams — usar `response.blob()` en el frontend
- Documentación interactiva en `/docs` cuando `ENVIRONMENT=development`

### 7.5 Mantenimiento

- **Dependabot** abre PRs automáticos semanales para CVEs
- **Pre-commit hooks** garantizan código formateado en cada commit
- **GitHub Actions** corre en cada push — si los tests fallan, el CI lo indica
- Antes de cada deploy: `.\venv\Scripts\python.exe -m pytest` para confirmar los 176 tests

---

*Documento preparado el 2026-05-31*
*Proyecto PISST — SENA*
*Backend desarrollado por Barner Acosta*
