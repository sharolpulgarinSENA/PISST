# Sustentación Técnica — Backend PISST
## Plataforma Integral de Seguridad y Salud en el Trabajo

**Proyecto:** PISST | **Fecha:** 2026-07-01 | **Autor:** Barner Acosta
**Stack:** FastAPI · SQLAlchemy 2.0 · PostgreSQL (Neon) · Python 3.12

---

## Tabla de Contenidos

1. [Estructura General del Backend](#1-estructura-general-del-backend)
2. [Tecnologías y Decisiones Técnicas](#2-tecnologías-y-decisiones-técnicas)
3. [Módulos Funcionales del Sistema](#3-módulos-funcionales-del-sistema)
4. [Seguridad del Backend](#4-seguridad-del-backend)
5. [Base de Datos](#5-base-de-datos)
6. [Calidad del Código y Pruebas](#6-calidad-del-código-y-pruebas)
7. [Cambios Recientes Importantes](#7-cambios-recientes-importantes)
8. [Analítica e Inteligencia Artificial](#8-analítica-e-inteligencia-artificial)
9. [Riesgos, Mejoras Futuras y Conclusiones](#9-riesgos-mejoras-futuras-y-conclusiones)
10. [Preguntas Probables del Profesor](#10-preguntas-probables-del-profesor)
11. [Guion de Exposición de 10 Minutos](#11-guion-de-exposición-de-10-minutos)

---

## 1. Estructura General del Backend

### 1.1 Arquitectura en capas

El backend aplica una **arquitectura en capas estricta** donde cada capa tiene una responsabilidad única y no puede saltarse la anterior:

```
HTTP Request (desde el frontend)
         │
┌────────▼────────┐
│    Routers      │  Capa HTTP: recibe la petición, valida con Pydantic,
│ app/routers/    │  controla autenticación/roles, serializa la respuesta.
│                 │  No contiene lógica de negocio.
└────────┬────────┘
         │ llama a →
┌────────▼────────┐
│    Services     │  Capa de negocio: toda la lógica del dominio vive aquí.
│ app/services/   │  Reglas de negocio, validaciones complejas, generación
│                 │  de PDFs, integración con servicios externos (IA, correo).
└────────┬────────┘
         │ consulta →
┌────────▼────────┐
│    Models       │  Capa de datos: definición de tablas con SQLAlchemy ORM,
│ app/models/     │  relaciones entre entidades, constraints e índices.
│                 │  Nunca contienen lógica de negocio.
└────────┬────────┘
         │
┌────────▼────────┐
│  PostgreSQL     │  Base de datos relacional en Neon (cloud serverless).
│  (Neon)         │  Gestionada con migraciones Alembic.
└─────────────────┘
```

**Adicionalmente:**
- `app/schemas/` — DTOs Pydantic: validan la entrada y serializan la salida. Son el contrato de la API.
- `app/core/` — Infraestructura transversal: conexión a BD (`database.py`), JWT y hashing (`security.py`), dependencias de autenticación (`deps.py`).

### 1.2 Estructura de carpetas

```
PISST/
├── main.py                  # Punto de entrada: app FastAPI, middlewares, routers, health check
├── app/
│   ├── core/
│   │   ├── database.py      # Engine SQLAlchemy, sesión de BD, get_db
│   │   ├── security.py      # JWT (crear/decodificar), bcrypt, validación de contraseña
│   │   └── deps.py          # get_current_user, require_role, require_api_key
│   ├── models/              # 17 modelos SQLAlchemy (tablas de BD)
│   ├── schemas/             # DTOs Pydantic por módulo (entrada y salida)
│   ├── routers/             # 13 routers FastAPI (endpoints HTTP)
│   └── services/            # Servicios con toda la lógica de negocio
├── tests/                   # 26 archivos de tests, 440 tests
├── alembic/                 # 21 migraciones Alembic en cadena lineal
├── notebooks/               # 3 Jupyter Notebooks para analítica de datos
├── requirements.txt
├── .pre-commit-config.yaml  # Hooks: black, isort, flake8
└── .github/workflows/       # CI/CD con GitHub Actions
```

### 1.3 Flujo completo de una petición HTTP

Ejemplo concreto: `GET /incidentes/` (listar incidentes del SST)

```
1. Frontend envía:
   GET https://api.pisst.online/incidentes/
   Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5c...

2. CORSMiddleware (main.py)
   └─ Verifica que el origen (app.pisst.online) está en la lista permitida.
      Si no está → responde 400 antes de procesar.

3. Router recibe la petición (app/routers/incidente_router.py)
   └─ Depende de: require_role("sst", "gerencia") → llama a deps.py

4. deps.py: get_current_user()
   ├─ Extrae el JWT del header Authorization
   ├─ Decodifica con SECRET_KEY (HS256) → obtiene user_id, role, sid
   ├─ Consulta BD: User donde id=user_id AND activo=True
   ├─ Verifica session_token (sesión única: si se logueó desde otro dispositivo → 401)
   └─ Verifica debe_cambiar_password (si es true → 403)

5. require_role("sst", "gerencia")
   └─ Compara current_user.role con los roles permitidos. Si no coincide → 403.

6. Router delega al servicio:
   result = incidente_service.get_all_incidentes(db, empresa_id, estado, tipo)

7. Service (app/services/incidente_service.py)
   └─ Construye la query SQLAlchemy filtrando siempre por empresa_id (multi-tenancy)
      query = db.query(Incidente)
                .options(joinedload(Incidente.reportado_por))
                .filter(Incidente.empresa_id == empresa_id)
                .order_by(Incidente.fecha_creacion.desc())
                .offset(skip).limit(limit).all()

8. Router serializa la respuesta con response_model=List[IncidenteResponse]
   └─ Pydantic convierte los objetos SQLAlchemy a JSON. El campo password_hash
      NUNCA aparece en la respuesta porque no está en el schema.

9. JSONResponse → frontend recibe la lista de incidentes
```

---

## 2. Tecnologías y Decisiones Técnicas

### 2.1 Stack y justificación

| Tecnología | Versión | Por qué se eligió |
|---|---|---|
| **Python 3.12** | 3.12 | Lenguaje del SENA, tipado moderno, ecosistema maduro |
| **FastAPI** | 0.136.x | Async nativo, validación automática Pydantic, documentación Swagger auto-generada, alto rendimiento |
| **SQLAlchemy 2.0** | 2.0.50 | ORM maduro, relaciones claras, migración con Alembic, compatible con PostgreSQL y SQLite (tests) |
| **Pydantic v2** | 2.13.x | Validación estricta de entrada, serialización de salida, generación automática de schemas OpenAPI |
| **PostgreSQL / Neon** | 16 | BD relacional robusta, soporte UUID nativo, cloud serverless sin costo fijo |
| **Alembic** | 1.18.x | Migraciones versionadas, cadena lineal de 21 migraciones, rollback seguro |
| **python-jose + bcrypt** | — | JWT estándar de industria; bcrypt con factor de costo para hashing de contraseñas |
| **ReportLab** | 4.5.x | Generación programática de PDFs (FURAT, reportes ejecutivos, certificados) |
| **openpyxl** | 3.1.5 | Generación de reportes Excel con formato profesional |
| **Google Gemini AI** | 2.2.0 | Motor del asistente SASBOT, soporte de vision para análisis de archivos |
| **Resend** | 2.30.x | Correos transaccionales (bienvenida, reset de contraseña) con dominio propio |
| **SlowAPI** | 0.1.9 | Rate limiting por IP y token para proteger el login y el chat IA |
| **Cloudinary** | 1.44.2 | Almacenamiento de fotos de perfil en la nube |

### 2.2 Patrones de diseño aplicados

| Patrón | Dónde se aplica | Beneficio |
|---|---|---|
| **Repository / Service Layer** | `app/services/` | Desacopla la lógica de negocio del HTTP. Permite testear servicios sin levantar el servidor. |
| **Dependency Injection** | `Depends()` de FastAPI | `get_current_user`, `get_db`, `require_role` se inyectan automáticamente. No hay estado global compartido. |
| **DTO (Data Transfer Object)** | `app/schemas/` | Schemas Pydantic distintos para entrada (`Create`) y salida (`Response`). Nunca expone campos internos. |
| **Multi-tenancy por filtro** | Toda query en services | Cada consulta filtra por `empresa_id` del JWT. Un usuario nunca puede ver datos de otra empresa. |
| **Factory Method** | `require_role(*roles)` | Retorna una dependencia dinámica según los roles requeridos por el endpoint. |
| **Observer / Event** | `notificacion_service` | Los routers llaman al servicio de notificaciones al crear eventos. Feed desacoplado del dominio. |

### 2.3 Buenas prácticas aplicadas

- **Sin lógica en routers**: si una función tiene más de 2 líneas de lógica, va al servicio.
- **`response_model` en todos los endpoints**: Pydantic garantiza que nunca se filtren campos internos como `password_hash`.
- **Transacciones atómicas**: `audit_service.registrar_auditoria()` no hace `commit()`. El commit lo hace el servicio principal, garantizando que el log y la operación se persisten juntos o ninguno.
- **Logging estructurado**: no hay ningún `print()` en el código. Todo usa `logging.INFO/WARNING/ERROR`.
- **Pre-commit hooks**: ningún commit llega al repositorio sin pasar `black` (formato), `isort` (imports) y `flake8` (lint).

---

## 3. Módulos Funcionales del Sistema

### 3.1 Mapa de módulos

```
┌─────────────────────────────────────────────────────────┐
│                    PISST BACKEND                        │
├──────────────┬──────────────┬──────────────┬────────────┤
│  AUTH        │  USUARIOS    │  INCIDENTES  │  RIESGOS   │
│  /auth/*     │  /usuarios/* │  /incidentes/│  /riesgos/ │
├──────────────┼──────────────┼──────────────┼────────────┤
│ CAPACITAC.   │  AUDITORÍAS  │  MÉTRICAS    │  ANALYTICS │
│ /capacitac/  │  /auditorias/│  /metricas/  │ /analytics/│
├──────────────┼──────────────┼──────────────┼────────────┤
│  CHAT IA     │ NOTIFICAC.   │  ADMIN       │ ÁREAS/CARGOS│
│  /chat/*     │ /notificac/  │  /admin/*    │ /areas/    │
└──────────────┴──────────────┴──────────────┴────────────┘
```

### 3.2 Módulo de Autenticación (`/auth/*`)

Gestiona el ciclo de vida completo de la sesión del usuario.

| Endpoint | Rol requerido | Qué hace |
|---|---|---|
| `POST /auth/login` | Público | Valida reCAPTCHA + credenciales. Genera JWT (30 min) + refresh token (7 días). Controla 5 intentos → bloqueo 5 min. |
| `POST /auth/refresh` | Autenticado | Renueva el access token sin pedir login. Verifica empresa activa. |
| `POST /auth/logout` | Autenticado | Invalida refresh token y session_token en BD. |
| `POST /auth/cambiar-password` | Autenticado | Cambia contraseña. Valida contraseña actual. Uso especial: funciona cuando `debe_cambiar_password=True`. |
| `POST /auth/forgot-password` | Público | Genera token seguro (64 chars) y envía enlace por correo. |
| `POST /auth/reset-password` | Público | Aplica nueva contraseña con token de un solo uso. |

### 3.3 Módulo de Usuarios (`/usuarios/*`)

| Endpoint | Acceso | Qué hace |
|---|---|---|
| `GET /usuarios/` | sst | Lista usuarios. `?activo=true\|false` filtra; sin parámetro devuelve todos. Incluye `area_nombre` y `cargo_nombre`. |
| `POST /usuarios/` | sst | Crea empleado con área y cargo. Genera contraseña temporal. Envía correo de bienvenida. |
| `PATCH /usuarios/{id}` | sst | Actualiza nombre, área, cargo o estado activo. |
| `PATCH /usuarios/me` | Autenticado | El propio usuario edita su nombre y teléfono. |
| `PUT /usuarios/me/foto` | Autenticado | Sube foto de perfil (JPG/PNG/WEBP, máx 2 MB) a Cloudinary. |
| `GET /usuarios/me/actividad` | Autenticado | Historial paginado de acciones del usuario (retención 30 días). |

### 3.4 Módulo de Incidentes y FURAT (`/incidentes/*`)

Ciclo de vida: `borrador → en_revision → abierto → en_investigacion → cerrado`

```
Empleado reporta un incidente
    ↓
SST lo revisa (estado: en_revision)
    ↓
SST lo abre formalmente (estado: abierto)
    ↓
SST documenta la investigación de causas → estado: en_investigacion
    ↓
SST crea acciones correctivas con responsable y fecha límite
    ↓
Cuando todas las acciones tienen evidencia → SST cierra el incidente
    ↓
Sistema genera el FURAT (formulario oficial ministerio de trabajo)
```

**Regla de negocio crítica:** no se puede cerrar un incidente sin investigación documentada. El sistema lanza `HTTP 400` si se intenta.

### 3.5 Módulo de Riesgos (`/riesgos/*`)

Implementa la **metodología GTC-45** de identificación y evaluación de riesgos:

1. SST identifica un peligro (tipo: físico/químico/biológico/ergonómico/psicosocial/locativo)
2. Evalúa el riesgo: **probabilidad × severidad → nivel automático** (bajo/medio/alto/crítico)
3. Crea medidas de control siguiendo la jerarquía: eliminación → sustitución → ingeniería → administrativo → EPP
4. Puede hacer evaluación residual tras aplicar los controles

Endpoint `GET /riesgos/matriz` devuelve la **matriz de calor** agrupada por nivel para visualización en el dashboard.

### 3.6 Módulo de Capacitaciones (`/capacitaciones/*`)

| Funcionalidad | Detalle |
|---|---|
| Programas | Asociados a áreas específicas de la empresa |
| Sesiones | Programación de fecha y lugar, reprogramación, cancelación |
| Asistencia | Registro por empleado (presente/ausente/justificado) |
| Evaluaciones | Preguntas de opción múltiple con calificación automática |
| Certificados PDF | Generación automática al aprobar (mínimo 60%). Diseño profesional horizontal con bordes dorados. |
| Cobertura | Porcentaje del plan anual de capacitaciones ejecutado |

### 3.7 Módulo de Métricas (`/metricas/*`)

Calcula los **KPIs del SG-SST** en tiempo real:

| KPI | Fórmula |
|---|---|
| Tasa de accidentalidad | (accidentes / total trabajadores) × 100 |
| Índice de frecuencia | (accidentes × 240.000) / horas trabajadas |
| Índice de severidad | (días perdidos × 240.000) / horas trabajadas |

Genera reportes ejecutivos en **PDF y Excel** con diseño profesional: paleta corporativa navy/azul, tarjetas KPI con colores semánticos (verde=bueno, rojo=crítico), tablas con referencias normativas.

### 3.8 Módulo de Analytics (`/analytics/*`)

Módulo de **solo lectura** que usa agregaciones SQL puras para máximo rendimiento. Accesible para SST y Gerencia.

| Endpoint | Qué calcula |
|---|---|
| `/analytics/incidentes` | Distribución por tipo/severidad, tasa mensual, tendencia (aumento/baja/estable) |
| `/analytics/riesgos` | Distribución por nivel, % con medidas implementadas, peligros críticos sin control |
| `/analytics/capacitaciones` | Tasa de aprobación, asistencia promedio, alertas < 80% |
| `/analytics/cumplimiento` | Score SG-SST 0–100 desglosado en 4 componentes |

### 3.9 Chat IA — SASBOT (`/chat/*`)

Asistente contextual powered by **Google Gemini AI** (gemini-2.5-flash):
- Respuestas personalizadas según el **cargo y área** del empleado
- Detección de palabras clave de emergencia con respuesta especial
- `POST /chat/escalar`: envía el historial al coordinador SST por correo
- `POST /chat/archivo`: analiza PDFs e imágenes con Gemini vision

---

## 4. Seguridad del Backend

### 4.1 Flujo de autenticación JWT

```
Login exitoso
    ↓
Servidor genera:
  • access_token JWT:
    {
      "sub": "uuid-del-usuario",
      "role": "sst",
      "sid": "session-id-unico",
      "exp": timestamp-expiracion,
      "iat": timestamp-emision
    }
    Firmado con SECRET_KEY (HS256). Expira en 30 minutos.

  • refresh_token: cadena aleatoria hex (80 chars)
    Guardado en BD con fecha de expiración (7 días).
    Se usa para renovar el access_token sin hacer login.
```

### 4.2 Verificaciones en cada petición

Cada petición a un endpoint protegido pasa por `deps.py`:

```python
# app/core/deps.py — get_current_user()

def get_current_user(...) -> User:
    token = credentials.credentials
    try:
        payload = decode_token(token)          # 1. ¿Firma válida y no expirado?
        user_id = payload.get("sub")
        session_id = payload.get("sid")
    except JWTError:
        raise HTTPException(401, "Token inválido o expirado")

    user = db.query(User).filter(
        User.id == UUID(user_id),              # 2. ¿Existe el usuario?
        User.activo == True                    # 3. ¿Está activo?
    ).first()

    if not user:
        raise HTTPException(401, "Usuario no encontrado")

    if user.debe_cambiar_password:             # 4. ¿Debe cambiar contraseña?
        raise HTTPException(403, "debe_cambiar_password")

    if session_id and str(user.session_token) != session_id:   # 5. Sesión única
        raise HTTPException(401, "Sesión expirada")

    return user
```

### 4.3 Tabla de respuestas de seguridad

| Situación | Código | Mensaje |
|---|---|---|
| Token bien formado pero expirado | 401 | "Token inválido o expirado" |
| Token manipulado / firma inválida | 401 | "Token inválido o expirado" |
| Usuario desactivado | 401 | "Usuario no encontrado" |
| Sesión revocada (nuevo login desde otro dispositivo) | 401 | "Sesión expirada" |
| Rol insuficiente para el endpoint | 403 | "Acceso denegado. Roles permitidos: ..." |
| Primer login — debe cambiar contraseña | 403 | "debe_cambiar_password" |
| Sin header Authorization | 403 | (HTTPBearer rechaza automáticamente) |

### 4.4 `debe_cambiar_password` — por qué existe

Cuando el admin crea un SST o un Gerencia, o cuando el SST crea un empleado, la contraseña inicial es temporal (generada aleatoriamente). Si el usuario pudiera operar con esa contraseña temporal indefinidamente, sería un riesgo de seguridad porque:
1. Es una contraseña corta o simple que conoce el creador
2. Se envía por correo (potencialmente interceptable)

El campo `debe_cambiar_password=True` se activa en la creación y **bloquea todos los endpoints** con un `HTTP 403` hasta que el usuario cambie su contraseña. El endpoint `/auth/cambiar-password` está diseñado para ser el único que funciona en ese estado.

### 4.5 Mecanismos de protección implementados

| Mecanismo | Implementación |
|---|---|
| **Sesión única** | Cada login genera un `session_token` nuevo. El anterior queda inválido → no hay sesiones paralelas. |
| **Bloqueo por intentos** | 5 intentos fallidos → `intentos_fallidos` en BD → bloqueo 5 minutos. |
| **Rate limiting** | `/auth/login`: 5 peticiones/min. `/chat/mensaje`: 20 peticiones/min. **Activo en todos los entornos** (incluyendo producción). |
| **reCAPTCHA v2** | Validado antes de consultar la BD en `/auth/login`. |
| **Multi-tenancy** | Toda query filtra por `empresa_id` del JWT. Imposible acceder a datos de otra empresa. |
| **No enumeración de usuarios** | Login devuelve siempre el mismo mensaje de error, sin revelar si el email existe. |
| **Emails enmascarados en logs** | `barner.acosta@empresa.com` → `b*****@empresa.com` en todos los logs del servidor. |
| **CORS restrictivo** | Lista explícita de orígenes. `allow_origins=["*"]` nunca se usa en producción. |
| **Validación Pydantic en inputs** | Enums en todos los campos de tipo/estado/severidad. Valor inválido → 422 antes de tocar la BD. |
| **`response_model` en todos los endpoints** | Nunca se expone `password_hash` ni campos internos. |
| **Contraseñas con bcrypt** | Factor de costo alto. El hash NO es reversible. |
| **Tokens de reset seguros** | 64 chars hex, uso único, expiran en 24h. Tabla propia `reset_tokens`. |
| **CVEs en dependencias** | Verificado con `pip-audit` → 0 CVEs. Dependabot activo semanalmente. |

### 4.6 API Keys para procesos automáticos

Los cron jobs no pueden hacer login manual. Se autentican con `X-API-Key: sk_...`:
- Formato: `sk_` + 60 chars hex
- Uso actual: cron diario en Render que ejecuta `POST /auditorias/verificar-vencidas`
- Rotación recomendada cada 90 días

---

## 5. Base de Datos

### 5.1 Entidades y relaciones principales

```
Empresa
  ├── Users (empleados, SST, gerencia, admin)
  │     ├── Area (pertenece a una)
  │     └── Cargo (tiene uno)
  ├── Incidentes
  │     ├── Lesion (1:1 — tipo, parte afectada, días incapacidad)
  │     ├── Testigos (1:N — nombre y relato)
  │     ├── Investigacion (1:1 — causas inmediatas, básicas, lecciones)
  │     └── AccionesCorrectivas (1:N — responsable, fecha, evidencia)
  ├── Peligros (GTC-45)
  │     ├── EvaluacionesRiesgo (1:N — probabilidad × severidad)
  │     └── MedidasControl (1:N — jerarquía EPP/administrativa/ingeniería)
  ├── Capacitaciones
  │     ├── Sesiones (1:N)
  │     │     ├── Asistencias (1:N — por empleado)
  │     │     └── Evaluaciones (1:1)
  │     │           ├── Preguntas (1:N — opciones múltiples)
  │     │           └── RespuestasEmpleado (1:N — qué respondió cada uno)
  ├── Auditorias
  │     └── Hallazgos (1:N — conformidad/NC menor/NC mayor)
  │           └── NoConformidades (1:N — con responsable y fecha límite)
  ├── Notificaciones (feed de eventos por empresa y por empleado)
  ├── AuditLogs (trazabilidad de acciones críticas)
  └── ResetTokens (tokens de reset de contraseña, uso único)
```

### 5.2 Por qué UUID como clave primaria

En lugar de `id` autoincremental entero, el proyecto usa `UUID` en todas las entidades. Razones:

1. **Seguridad**: no se pueden adivinar ni enumerar registros. `GET /incidentes/1` permite iterar; `GET /incidentes/550e8400-e29b-41d4-a716-446655440000` no.
2. **Distribución**: en arquitecturas con múltiples instancias o bases de datos, los UUIDs son únicos globalmente sin coordinación central.
3. **Multi-tenancy**: `empresa_id` es un UUID que se incluye en el JWT. Cualquier intento de falsificarlo falla al no coincidir con la BD.

```python
# SQLAlchemy — clave UUID en todos los modelos
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
```

### 5.3 Cómo se hacen las consultas — Service Layer

```python
# app/services/incidente_service.py
def get_all_incidentes(db: Session, empresa_id: UUID, estado=None, ...):
    query = (
        db.query(Incidente)
          .options(joinedload(Incidente.reportado_por))  # eager loading: evita N+1
          .filter(Incidente.empresa_id == empresa_id)    # siempre filtrado por empresa
    )
    if estado:
        query = query.filter(Incidente.estado == estado)
    return query.order_by(Incidente.fecha_creacion.desc()).offset(skip).limit(limit).all()
```

**`joinedload`** evita el problema N+1: sin él, por cada incidente se haría una query extra para cargar el usuario que lo reportó. Con `joinedload`, se hace un solo JOIN.

### 5.4 Índices para rendimiento

```sql
-- Creados con Alembic:
ix_incidentes_empresa_estado   (empresa_id, estado)
ix_users_empresa_activo        (empresa_id, activo)
ix_acciones_incidente_estado   (incidente_id, estado)
```

Los índices compuestos aceleran las consultas más frecuentes: listar incidentes de una empresa por estado, y filtrar usuarios activos de una empresa.

### 5.5 Multi-tenancy — aislamiento entre empresas

El campo `empresa_id` está presente en todas las entidades del dominio. El valor viene del JWT del usuario autenticado, nunca de la URL o el body. Un usuario de la empresa A físicamente no puede ver datos de la empresa B porque:

1. Su JWT contiene solo su `empresa_id`
2. `deps.py` valida que su `empresa_id` en BD coincide con el del JWT
3. Todos los servicios filtran por ese `empresa_id`

---

## 6. Calidad del Código y Pruebas

### 6.1 Estado actual

| Métrica | Valor |
|---|---|
| Tests totales | **440** |
| Tests pasando | **440 (100%)** |
| Cobertura global | **93%** |
| Archivos de tests | 26 |
| CI/CD | GitHub Actions — corre en cada push |

### 6.2 Estrategia de testing

El proyecto usa **dos tipos de tests**:

#### Tests de servicio (mayoría)
Prueban la lógica de negocio directamente, sin HTTP. Usan una sesión de **SQLite en memoria** — no requieren conexión a Neon ni variables de entorno.

```python
# Ejemplo: test de servicio — app/services/auth_service.py
def test_cambiar_password_session_invalida(db, empresa):
    user = make_user(db, empresa, session_token=secrets.token_hex(32))
    with pytest.raises(HTTPException) as exc:
        auth_service.cambiar_password(str(user.id), "token-incorrecto", "nueva", "actual")
    assert exc.value.status_code == 401  # sesión inválida → 401
```

**Ventaja:** rápidos, aislados, sin dependencias externas. Un test de servicio corre en ~5ms.

#### Tests de endpoint HTTP
Usan `TestClient` de FastAPI para probar el flujo completo incluyendo JWT, schemas y serialización.

```python
# Ejemplo: test HTTP — app/routers/admin_router.py
def test_crear_sst_duplicado(client):
    empresa_id = nueva_empresa(client)
    with patch("app.routers.admin_router.enviar_correo_bienvenida", return_value=True):
        client.post("/admin/crear-sst", json={...}, headers=h())
        resp = client.post("/admin/crear-sst", json={...}, headers=h())
    assert resp.status_code == 400  # no puede haber 2 SST activos
```

### 6.3 Cobertura por módulo

| Módulo | Cobertura |
|---|---|
| `auth_service.py` | 100% |
| `incidente_service.py` | 100% |
| `riesgo_service.py` | 100% |
| `auditoria_service.py` | 100% |
| `furat_service.py` | 100% |
| `metricas_service.py` | 100% |
| `capacitacion_service.py` | 100% |
| `deps.py` | 100% |
| `email_service.py` | 95%+ |
| `ai_service.py` | 90%+ |
| **Global** | **93%** |

### 6.4 Casos críticos de seguridad probados

```python
# deps.py — todos los paths de error están cubiertos:
test_acceso_sin_token                     # → 403 (HTTPBearer rechaza)
test_acceso_token_malformado              # → 401
test_acceso_token_expirado                # → 401
test_acceso_sesion_invalida               # → 401 (otra sesión activa)
test_acceso_usuario_inactivo              # → 401
test_acceso_debe_cambiar_password         # → 403
test_acceso_rol_insuficiente              # → 403
```

### 6.5 Cómo las pruebas evitaron regresiones

| Bug descubierto por tests | Descripción | Fix |
|---|---|---|
| `cambiar-password` con sesión revocada | El endpoint no validaba `session_token`. Un JWT revocado podía cambiar la contraseña. | Test falló → se agregó validación de `session_id` en el servicio. |
| Enum vs string en queries SQL | SQLAlchemy comparaba `Incidente.estado == "cerrado"` pero el campo era `EstadoEnum`. Falla silenciosa. | Tests con SQLite revelaron el error → se corrigieron todos los Enum. |
| `datetime.utcnow()` deprecado | Generaba advertencias en producción. | Tests detectaron las advertencias → migrado a `datetime.now(timezone.utc)`. |
| `POST /capacitaciones/` devolvía `{}` | Faltaba `response_model` en el router. | Test verificó el response → se agregó el decorator. |
| Rate limiting desactivado en producción | `ENVIRONMENT=development` en Render anulaba el rate limit. | Test con 6 requests al login → CI detectó el bug → fix: límites hardcoded. |
| Excel test en columna incorrecta | Rediseño cambió columna A (margen) vs B (contenido). Test buscaba en columna A. | CI falló → fix: test actualizado para columna B. |

### 6.6 Infraestructura de tests (`tests/conftest.py`)

```python
# Fixtures disponibles en todos los tests:
@pytest.fixture
def db():      # Sesión SQLite en memoria, rollback automático al terminar cada test
@pytest.fixture
def client():  # TestClient de FastAPI con BD sobreescrita por SQLite
@pytest.fixture
def empresa(): # Empresa de prueba ya creada
@pytest.fixture
def usuario_sst():  # Usuario SST ya creado en BD

# Fixture autouse para rate limiting:
@pytest.fixture(autouse=True)
def resetear_rate_limiter():
    # Resetea el storage en memoria de SlowAPI antes de cada test
    # Sin esto, los tests de login agotarían el cupo de 5/min
```

---

## 7. Cambios Recientes Importantes

### 7.1 `GET /capacitaciones/` devuelve todas por defecto

**Solicitud del equipo frontend:** necesitaban todas las capacitaciones para filtrar localmente.

| Request | Antes | Ahora |
|---|---|---|
| `GET /capacitaciones/` | Solo activas | **Todas** |
| `GET /capacitaciones/?activo=true` | Solo activas | Solo activas |
| `GET /capacitaciones/?activo=false` | Solo inactivas | Solo inactivas |

**Impacto:** 0 regresiones. Tests actualizados y CI verde.

### 7.2 `GET /usuarios/` con `area_nombre` y `cargo_nombre`

El frontend necesitaba mostrar el nombre del área y cargo del empleado sin hacer peticiones adicionales. Se resolvió con **`@property` en el modelo SQLAlchemy**:

```python
# app/models/user.py
@property
def area_nombre(self) -> Optional[str]:
    return self.area.nombre if self.area else None

@property
def cargo_nombre(self) -> Optional[str]:
    return self.cargo.nombre if self.cargo else None
```

Pydantic con `from_attributes=True` lee las properties automáticamente. Cero queries adicionales.

### 7.3 `debe_cambiar_password=True` en todos los usuarios creados por admin

Se detectó que los usuarios creados por el admin podían operar sin cambiar su contraseña temporal. Corrección:

```python
# POST /admin/crear-sst y /admin/crear-gerencia
user = User(..., debe_cambiar_password=True)  # ← agregado explícitamente
```

Test que validó el fix:
```python
def test_sst_creado_debe_cambiar_password(client):
    resp = client.post("/admin/crear-sst", ...)
    assert resp.status_code == 200
    # Consultar BD y verificar el flag
    user = db.query(User).filter_by(email=email).first()
    assert user.debe_cambiar_password == True
```

### 7.4 Cobertura de `deps.py` llevada a 100%

`deps.py` es el guardián de toda la seguridad. Tenía 38% de cobertura porque no se testeaban los paths de error. Se creó `tests/test_deps.py` con 8 tests que cubren cada caso de fallo.

### 7.5 Fix FURAT sección 2 — "No registrado"

Cuando un empleado creaba su propio reporte de incidente, el formulario del frontend no enviaba `trabajador_afectado_id` → el campo quedaba `None` → el FURAT mostraba "No registrado" en datos del trabajador afectado.

```python
# app/services/incidente_service.py, línea 71
trabajador_afectado_id = datos.trabajador_afectado_id or reportado_por_id
# Si no se especifica trabajador afectado, se asume que es quien reporta.
```

### 7.6 Hardening de rate limiting (Sprint 16)

Se descubrió que la variable `ENVIRONMENT=development` en Render desactivaba el rate limiting en producción, dejando el endpoint de login sin protección contra fuerza bruta. **Fix:** límites hardcoded directamente en el decorator, sin condicional de entorno.

```python
# Antes (vulnerable):
@limiter.limit(os.getenv("LOGIN_RATE_LIMIT", "1000/minute"))  # ← producción usaba 1000/min

# Después (correcto):
@limiter.limit("5/minute")  # siempre, en todos los entornos
```

---

## 8. Analítica e Inteligencia Artificial

### 8.1 Módulo de Analytics (implementado)

El módulo `/analytics/*` está **completamente implementado y en producción**. Es un módulo de solo lectura que usa:
- **Agregaciones SQL puras** (`func.count`, `GROUP BY`, `JOIN`) para máximo rendimiento
- **Pandas** únicamente para el cálculo de tendencia mensual (requiere operaciones de período de fecha)
- **Principio de no invasión**: un error en analytics no afecta el backend principal

```python
# Ejemplo: cálculo de tendencia con Pandas
import pandas as pd

df = pd.DataFrame(datos_mensuales)
df["mes"] = pd.to_datetime(df["fecha"]).dt.to_period("M")
conteo_mensual = df.groupby("mes").size()
tendencia = "aumento" if conteo_mensual.iloc[-1] > conteo_mensual.iloc[-2] else "baja"
```

### 8.2 Jupyter Notebooks para sustentación de datos

Disponibles en `notebooks/`:

| Notebook | Qué analiza |
|---|---|
| `01_exploracion_incidentes.ipynb` | Distribución por tipo, severidad y tendencia mensual |
| `02_exploracion_riesgos.ipynb` | Peligros y controles por nivel de riesgo |
| `03_exploracion_capacitaciones.ipynb` | Asistencia, aprobación y alertas de capacitaciones |

Cada notebook se conecta a Neon vía `DATABASE_URL` y filtra por `EMPRESA_ID` (multi-tenant).

### 8.3 SASBOT — Asistente IA

Motor: **Google Gemini AI (gemini-2.5-flash)**. El contexto del sistema incluye:
- Cargo y área del empleado autenticado
- Marco normativo colombiano (Decreto 1072/2015, Resolución 0312/2019)
- Instrucciones de escalamiento ante emergencias

**Capacidades actuales:**
- Orientación en SST adaptada al rol del empleado
- Análisis de PDFs e imágenes con Gemini vision (`POST /chat/archivo`)
- Escalamiento al coordinador SST vía correo (`POST /chat/escalar`)
- Detección de palabras clave de emergencia

---

## 9. Riesgos, Mejoras Futuras y Conclusiones

### 9.1 Riesgos técnicos actuales

| Riesgo | Nivel | Mitigación actual |
|---|---|---|
| Métricas calculadas en tiempo real | Bajo | Para empresas pequeñas es suficiente. Para volúmenes altos, se puede cachear con Redis. |
| Generación PDF/Excel síncrona | Bajo | Para archivos grandes podría bloquear el servidor. Solución: FastAPI BackgroundTasks. |
| Neon cold start | Bajo | Las primeras peticiones tras inactividad pueden tardar 1-2s. Mitigation: health check pings. |
| Un único SST por empresa | Bajo-Medio | Limitación de negocio actual. Si la empresa requiere varios, habría que ajustar el modelo. |

### 9.2 Mejoras propuestas

**A corto plazo:**
- Paginación con metadatos (`total`, `pagina_actual`, `total_paginas`) en endpoints de listado
- Selector de "trabajador afectado" en el frontend para cuando SST reporta el incidente de otro empleado (backend ya soporta `trabajador_afectado_id`)

**A mediano plazo:**
- **Refresh token rotation**: al usar el refresh token, generar uno nuevo e invalidar el anterior (doble rotación)
- **Caché de métricas**: Redis con TTL de 5-10 minutos por empresa
- **Workers async**: mover generación de PDF/Excel a background tasks para no bloquear el servidor

**A largo plazo:**
- Soporte multi-idioma (español/inglés)
- Exportación de datos de la empresa (GDPR-ready)
- Integración con ARL para reporte automático de accidentes

### 9.3 Conclusión

El backend de PISST está en un **estado de madurez sólida**:

| Dimensión | Evaluación |
|---|---|
| **Funcionalidad** | 9 módulos operativos en producción. Cubre el ciclo completo del SG-SST. |
| **Calidad** | 440 tests, 93% cobertura, 0 CVEs. CI/CD activo en cada push. |
| **Seguridad** | JWT + refresh tokens, sesión única, rate limiting, multi-tenancy, CORS restrictivo, bcrypt. |
| **Escalabilidad** | Arquitectura en capas, índices optimizados. Listo para escalar horizontalmente. |
| **Mantenibilidad** | Pre-commit hooks, logging estructurado, Dependabot, migraciones Alembic en cadena lineal. |

---

## 10. Preguntas Probables del Profesor

### Bloque A — Arquitectura

**P1: ¿Por qué eligieron FastAPI en lugar de Django o Flask?**
> FastAPI ofrece validación automática con Pydantic, documentación Swagger auto-generada, soporte async nativo y es el framework Python más moderno para APIs REST. Django es más pesado y está orientado a renderizado de HTML. Flask es más minimalista pero requiere más configuración manual para validaciones y documentación.

**P2: ¿Qué es una arquitectura en capas y por qué la usaron?**
> Es un patrón donde cada capa tiene una responsabilidad única: routers manejan HTTP, services tienen la lógica de negocio, models definen las tablas. El beneficio principal es que podemos testear los services directamente sin levantar el servidor HTTP. También fue gracias a esta separación que descubrimos el bug de seguridad en `cambiar-password`: al extraer `auth_service.py`, quedó expuesto que el router no validaba la sesión activa.

**P3: ¿Qué son los DTOs y por qué los usan?**
> DTO significa Data Transfer Object. Son los schemas Pydantic que definen qué datos entran y salen de cada endpoint. Por ejemplo, `IncidenteCreate` tiene los campos que el frontend envía, y `IncidenteResponse` define lo que devolvemos. El beneficio es que nunca filtramos campos internos como `password_hash` — si no está en `IncidenteResponse`, Pydantic lo omite automáticamente.

---

### Bloque B — Seguridad

**P4: ¿Cómo funciona el JWT y qué pasa si alguien lo falsifica?**
> El JWT está firmado con `SECRET_KEY` usando el algoritmo HS256. Si alguien modifica el payload (por ejemplo, cambia su rol de "empleado" a "admin"), la firma ya no coincide. `decode_token()` lanza `JWTError` → el sistema responde 401. Para que la falsificación funcione, necesitarían conocer la `SECRET_KEY`, que es una cadena aleatoria de 64 caracteres nunca expuesta públicamente.

**P5: ¿Qué es la sesión única y por qué la implementaron?**
> Cuando un usuario hace login desde un segundo dispositivo, el servidor genera un nuevo `session_token` e invalida el anterior. Si el primer dispositivo intenta hacer una petición, su `session_id` (guardado en el JWT) ya no coincide con el `session_token` en BD → respuesta 401. Esto evita que múltiples sesiones activas simultáneas puedan comprometer la cuenta.

**P6: Explica `debe_cambiar_password`. ¿Por qué no simplemente dejar que el usuario entre?**
> Cuando el admin crea un usuario, genera una contraseña temporal que se envía por correo. Si el usuario entra sin cambiarla, esa contraseña temporal queda activa indefinidamente. Alguien que interceptó el correo podría acceder. El flag bloquea todos los endpoints con 403 hasta que el usuario cambie a una contraseña propia, fuerte y privada.

**P7: ¿Por qué el rate limiting estaba desactivado en producción y cómo lo corrigieron?**
> El código original leía el límite desde la variable de entorno `LOGIN_RATE_LIMIT` con default "1000/minute". En Render, `ENVIRONMENT=development` desactivaba la condición. El fix fue hardcodear `@limiter.limit("5/minute")` directamente en el decorator, sin condición de entorno. Los tests se actualizaron con un fixture `autouse` que resetea el storage de SlowAPI antes de cada test para no acumular peticiones entre tests.

**P8: ¿Qué es CORS y por qué lo configuraron así?**
> CORS (Cross-Origin Resource Sharing) es el mecanismo del navegador que bloquea peticiones desde orígenes no autorizados. En `main.py` tenemos una lista explícita: `app.pisst.online`, `pisst-frontend.vercel.app`. En desarrollo también se agrega `localhost`. Nunca usamos `allow_origins=["*"]` porque eso permitiría a cualquier sitio web hacer peticiones autenticadas al backend usando las cookies del usuario.

---

### Bloque C — Base de Datos

**P9: ¿Por qué usaron UUIDs en lugar de IDs enteros?**
> Tres razones: seguridad (no se pueden enumerar registros: `/incidentes/1`, `/incidentes/2`...), distribución (únicos globalmente sin coordinación) y multi-tenancy (el `empresa_id` UUID en el JWT no se puede adivinar ni suplantar).

**P10: ¿Qué es Alembic y para qué sirve?**
> Alembic es el sistema de migraciones de SQLAlchemy. Cada cambio al modelo de datos (agregar columna, crear tabla) genera un archivo de migración Python que describe cómo subir (`upgrade`) y bajar (`downgrade`) ese cambio. Tenemos 21 migraciones en cadena lineal. Cuando se despliega en Render, `alembic upgrade head` aplica las migraciones pendientes automáticamente sin perder datos.

**P11: ¿Qué es el problema N+1 y cómo lo resolvieron?**
> El problema N+1 ocurre cuando por cada elemento de una lista se hace una query extra para cargar datos relacionados. Por ejemplo: 50 incidentes → 50 queries adicionales para cargar quién los reportó = 51 queries total. Lo resolvemos con `joinedload`: SQLAlchemy hace un solo JOIN y carga todo en una sola query. Lo vemos en `get_all_incidentes` con `.options(joinedload(Incidente.reportado_por))`.

---

### Bloque D — Pruebas y Calidad

**P12: ¿Por qué usan SQLite para tests si en producción es PostgreSQL?**
> SQLite en memoria es mucho más rápido (no hay conexión de red), no requiere configurar credenciales y cada test empieza limpio. La desventaja es que SQLite es más permisivo que PostgreSQL — y eso es un **beneficio**: cuando un test pasa con SQLite pero falla en PostgreSQL, encontramos un bug de compatibilidad. Esto nos pasó con los UUID: `db.query(User).filter(User.id == "string")` funciona en PostgreSQL pero falla en SQLite, lo que nos forzó a convertir explícitamente a `UUID(user_id)`.

**P13: ¿Qué son los pre-commit hooks y cuál es su propósito?**
> Son scripts que se ejecutan automáticamente antes de cada `git commit`. Tenemos tres: `black` (formatea el código automáticamente), `isort` (ordena los imports) y `flake8` (detecta errores de estilo e imports sin usar). Si cualquiera falla, el commit se rechaza. Esto garantiza que **ningún código mal formateado o con imports sin usar llega al repositorio**, sin depender de que cada desarrollador recuerde formatearlo manualmente.

**P14: ¿Qué cobertura tienen y qué significa ese número?**
> Tenemos 93% de cobertura global. Eso significa que el 93% de las líneas de código del proyecto son ejecutadas por al menos un test. Los módulos más críticos (auth, incidente, riesgo, métricas, FURAT) están al 100%. El 7% restante son principalmente ramas de error de servicios externos (cuando Cloudinary falla, cuando Gemini no responde) que son difíciles de reproducir en tests.

**P15: ¿Cómo probaron que el rate limiting funciona realmente?**
> En `test_auth.py` tenemos un test que hace 6 peticiones seguidas a `/auth/login`. Las primeras 5 deben devolver 200 o 401 (credenciales incorrectas), la 6a debe devolver 429 (Too Many Requests). El problema es que SlowAPI usa un singleton en memoria compartido entre todos los tests — sin el fixture `resetear_rate_limiter` que hace `lim._storage.reset()`, el cupo se agotaría acumulando peticiones de otros tests y causaría fallos en CI.

---

## 11. Guion de Exposición de 10 Minutos

### Minuto 1 — Contexto y problema (presentación del problema)

> "El proyecto PISST digitaliza el Sistema de Gestión de Seguridad y Salud en el Trabajo para empresas colombianas. Las PYMES colombianas, que representan el 96% de las empresas del país, gestionan su SG-SST en papel o en hojas de cálculo dispersas. Esto genera tiempos de respuesta lentos ante accidentes, falta de trazabilidad y riesgo de incumplimiento del Decreto 1072 de 2015 y la Resolución 0312 de 2019.
>
> Mi parte del proyecto es el backend completo — la API que alimenta toda la plataforma."

### Minuto 2 — Arquitectura del sistema

> "El backend está construido con FastAPI y Python 3.12, siguiendo una arquitectura en capas estricta. [Mostrar diagrama de capas]
>
> Cada petición HTTP entra al router, que valida el JWT y los roles, luego delega al service donde vive toda la lógica de negocio, y este consulta la base de datos PostgreSQL en Neon a través de modelos SQLAlchemy.
>
> Esta separación es clave: nos permite testear la lógica de negocio directamente sin levantar el servidor."

### Minuto 3 — Módulos del sistema

> "El sistema tiene 9 módulos operativos en producción. [Mostrar tabla de módulos]
>
> Los más importantes son: autenticación, gestión de incidentes con generación automática del FURAT, riesgos con metodología GTC-45, capacitaciones con certificados PDF, auditorías internas, métricas con KPIs del SG-SST, analítica integrada, notificaciones y el asistente SASBOT con Google Gemini AI."

### Minuto 4 — Flujo de una petición real

> "Les voy a mostrar qué pasa exactamente cuando el SST lista los incidentes. [Mostrar diagrama de flujo]
>
> La petición llega al router, pasa por `deps.py` que extrae y valida el JWT, verifica que el usuario existe y está activo, que la sesión no fue revocada, y que tiene el rol correcto. Si algo falla, responde 401 o 403 antes de tocar la base de datos.
>
> Si todo está bien, llama al service que hace una única query con `joinedload` para evitar el problema N+1."

### Minuto 5 — Seguridad

> "La seguridad tiene múltiples capas. [Mostrar tabla de mecanismos]
>
> JWT con refresh tokens: el access token dura 30 minutos, el refresh 7 días. Sesión única: si el usuario hace login desde otro dispositivo, la sesión anterior queda inválida inmediatamente.
>
> `debe_cambiar_password`: todos los usuarios creados por el admin tienen contraseña temporal que bloquea el acceso hasta que la cambien.
>
> Rate limiting hardcodeado en 5 peticiones/minuto en el login para proteger contra fuerza bruta. Esto estaba mal implementado — se los explico en la siguiente parte."

### Minuto 6 — Bug crítico corregido

> "Descubrimos que el rate limiting estaba desactivado en producción porque la variable `ENVIRONMENT=development` en Render desactivaba la condición. El endpoint de login tenía efectivamente 1000 peticiones/minuto.
>
> Lo detectamos escribiendo tests que hacen 6 peticiones seguidas. El fix fue hardcodear el límite directamente en el decorator. Esta es una lección sobre por qué se usan tests: algunos bugs solo se descubren escribiendo pruebas."

### Minuto 7 — Base de datos y migraciones

> "La base de datos es PostgreSQL en Neon, cloud serverless. Usamos UUIDs en todas las entidades — no IDs enteros — por seguridad y multi-tenancy.
>
> El multi-tenancy garantiza que un usuario de empresa A nunca puede ver datos de empresa B. El `empresa_id` viene del JWT, no del request, y todas las queries lo filtran.
>
> Las migraciones con Alembic: tenemos 21 migraciones en cadena lineal. Cada cambio al modelo es versionado y reproducible."

### Minuto 8 — Pruebas y calidad

> "440 tests, 93% de cobertura global, CI/CD con GitHub Actions que corre en cada push.
>
> Los tests usan SQLite en memoria — sin conexión a Neon, sin variables de entorno. Son rápidos y aislados.
>
> Los tests no solo verifican que el código funciona — evitaron regresiones reales. Por ejemplo, cuando rediseñamos el Excel con una columna de margen, el test que buscaba datos en la columna A falló inmediatamente en CI, alertándonos del cambio. [Mostrar tabla de bugs detectados por tests]"

### Minuto 9 — Analítica e IA

> "El módulo de Analytics usa agregaciones SQL puras y Pandas para análisis de tendencias. Es estrictamente de solo lectura y no afecta el backend principal.
>
> El SASBOT usa Google Gemini AI con contexto SST personalizado por cargo y área del empleado. Puede analizar PDFs e imágenes, y escalar conversaciones al coordinador SST por correo.
>
> Los Jupyter Notebooks en la carpeta `notebooks/` conectan a la BD de producción para exploración de datos — útil para sustentaciones como esta."

### Minuto 10 — Estado y conclusiones

> "El backend está en producción en Render, con despliegue automático desde la rama `main`. URL: https://app.pisst.online
>
> Estado: 9 módulos operativos, 440 tests en verde, 0 CVEs en dependencias, rate limiting activo, CORS restrictivo, generación de FURAT y certificados PDF profesionales.
>
> Las mejoras inmediatas pendientes son: paginación con metadatos y el selector de trabajador afectado en el frontend para incidentes de terceros — el backend ya soporta el campo `trabajador_afectado_id`, solo falta el componente en el frontend.
>
> Abro el espacio para preguntas."

---

*Documento preparado el 2026-07-01 — Proyecto PISST, SENA*
*Backend desarrollado por Barner Acosta*
