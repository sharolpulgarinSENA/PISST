# PISST — Documentación Técnica del Proyecto

> **Plataforma Integral de Seguridad y Salud en el Trabajo**  
> API REST multi-tenant para gestión del SG-SST en empresas colombianas.

---

## 1. Resumen Ejecutivo

PISST es una **API REST asincrónica** construida con FastAPI que cubre el ciclo completo del Sistema de Gestión de Seguridad y Salud en el Trabajo (SG-SST) según la normativa colombiana (Decreto 1072, Resolución 0312, Ley 1562). Permite gestionar:

- Incidentes y accidentes laborales
- Capacitaciones y evaluaciones con certificados PDF
- Matriz de riesgos y medidas de control
- Auditorías internas y no conformidades
- Métricas, KPIs y reportes ejecutivos PDF/Excel
- Chatbot IA (SASBOT) especializado en SST

---

## 2. Stack Tecnológico

| Componente | Tecnología | Versión | Propósito |
|---|---|---|---|
| **Backend Framework** | FastAPI | 0.136.1 | API REST asincrónica |
| **ORM** | SQLAlchemy | 2.0.49 | Mapeo objeto-relacional |
| **Base de datos** | PostgreSQL (Neon serverless) | — | BD relacional en la nube |
| **Driver DB** | psycopg2-binary | 2.9.12 | Conexión a PostgreSQL |
| **Migraciones** | Alembic | 1.18.4 | Control de versiones de esquema |
| **Autenticación** | JWT (python-jose) | 3.5.0 | Tokens de acceso |
| **Hashing** | bcrypt + passlib | 4.0.1 / 1.7.4 | Almacenamiento seguro de contraseñas |
| **Rate Limiting** | slowapi | 0.1.9 | Protección contra abuso |
| **Email** | Resend | 2.30.1 | Correos transaccionales |
| **IA / Chatbot** | Google Generative AI (Gemini) | 2.2.0 | SASBOT |
| **PDF** | ReportLab | 4.5.0 | FURAT, reportes, certificados |
| **Excel** | openpyxl | 3.1.5 | Reportes en hoja de cálculo |
| **Validación** | Pydantic | 2.13.4 | Schemas y validación de datos |
| **Servidor ASGI** | Uvicorn | 0.46.0 | Servidor de producción |
| **Variables de entorno** | python-dotenv | 1.2.2 | Gestión de configuración |

---

## 3. Arquitectura del Proyecto

```
PISST/
├── main.py                    # Punto de entrada: FastAPI, CORS, rate limiting
├── requirements.txt           # Dependencias del proyecto
├── .env                       # Variables de entorno (NO subir a git)
├── alembic.ini                # Configuración de migraciones
├── render.yaml                # Deployment en Render
├── seed.py                    # Script de datos demo
│
├── migrations/
│   ├── env.py
│   └── versions/              # Historial de migraciones por sprint
│
└── app/
    ├── core/
    │   ├── database.py        # Engine SQLAlchemy, get_db()
    │   ├── security.py        # Hashing bcrypt, JWT encode/decode
    │   └── deps.py            # get_current_user(), require_role()
    │
    ├── models/                # Modelos ORM (SQLAlchemy)
    │   ├── user.py
    │   ├── empresa.py
    │   ├── area.py
    │   ├── cargo.py
    │   ├── incidente.py
    │   ├── investigacion.py
    │   ├── lesion.py
    │   ├── testigo.py
    │   ├── accion_correctiva.py
    │   ├── capacitacion.py
    │   ├── riesgo.py
    │   ├── auditoria.py
    │   └── chat_historial.py
    │
    ├── schemas/               # Validación y serialización (Pydantic)
    │   ├── usuario_schema.py
    │   ├── incidente.py
    │   ├── capacitacion.py
    │   ├── riesgo.py
    │   ├── auditoria.py
    │   ├── area_schema.py
    │   └── cargo_schema.py
    │
    ├── routers/               # Endpoints agrupados por módulo
    │   ├── auth_router.py
    │   ├── usuario_router.py
    │   ├── incidente_router.py
    │   ├── capacitacion_router.py
    │   ├── metricas_router.py
    │   ├── riesgo_router.py
    │   ├── auditoria_router.py
    │   ├── chat_router.py
    │   ├── admin_router.py
    │   ├── area_router.py
    │   └── cargo_router.py
    │
    └── services/              # Lógica de negocio
        ├── usuario_service.py
        ├── incidente_service.py
        ├── capacitacion_service.py
        ├── metricas_service.py
        ├── riesgo_service.py
        ├── auditoria_service.py
        ├── ai_service.py
        ├── email_service.py
        └── furat_service.py
```

**Patrón arquitectónico:** Router → Service → Model (ORM). Los routers solo validan y delegan; la lógica de negocio vive en services.

---

## 4. Infraestructura y Despliegue

| Componente | Servicio | Notas |
|---|---|---|
| **API Backend** | Render | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Base de datos** | Neon (PostgreSQL serverless) | SSL requerido (`sslmode=require`) |
| **Frontend** | Vercel | React/Vue en `pisst-frontend.vercel.app` |
| **Email** | Resend | Bienvenida + recuperación de contraseña |
| **IA** | Google Generative AI (Gemini 2.5 Flash) | SASBOT |

**Configuración del pool de conexiones Neon:**
- `pool_pre_ping=True` — verifica conexión antes de usarla
- `pool_recycle=300` — renueva conexiones cada 5 minutos
- `sslmode=require` — SSL obligatorio en la URL de conexión

---

## 5. Modelos de Base de Datos

### 5.1 Usuarios y Empresas

**`users`**
| Campo | Tipo | Notas |
|---|---|---|
| id | UUID PK | Auto uuid4 |
| nombre | String(200) | |
| email | String(255) | Único |
| password_hash | String(255) | bcrypt |
| role | Enum | `admin`, `sst`, `gerencia`, `empleado` |
| empresa_id | UUID FK | → empresas |
| area_id | UUID FK | → areas, nullable |
| cargo_id | UUID FK | → cargos, nullable |
| activo | Boolean | Soft delete |
| intentos_fallidos | Integer | Para bloqueo de cuenta |
| bloqueado_hasta | DateTime | Bloqueo temporal (5 min) |
| session_token | String(64) | Sesión única activa |
| reset_token | String(255) | Recuperación de contraseña |
| reset_token_expira | DateTime | Expiración 30 min |

**`empresas`** — Raíz del multi-tenant. Cada empresa tiene su `id` que filtra todos los datos.

**`areas`** — Áreas de la empresa (Producción, Administración, etc.)

**`cargos`** — Puestos de trabajo, vinculados a un área y empresa.

---

### 5.2 Gestión de Incidentes

**`incidentes`** — Núcleo del módulo. Estados: `borrador → en_revision → abierto → en_investigacion → cerrado`

**`lesiones`** — Lesión asociada al incidente (tipo, parte afectada, días de incapacidad).

**`testigos`** — Testigos del incidente con relato.

**`investigaciones`** — Análisis de causas (método 5 por qué). Requerida antes de cerrar.

**`acciones_correctivas`** — Tareas de mejora con responsable, fecha límite y estado de avance.

---

### 5.3 Capacitaciones

Jerarquía: `Capacitacion → SesionCapacitacion → Evaluacion → Pregunta → RespuestaEmpleado`

**Nota clave:** El campo `puntaje_final` se repite en todas las filas de `respuestas_empleado` del mismo intento. Se calcula una sola vez al finalizar y se actualiza en bulk. Esto permite que `generar_certificado()` pueda consultar eficientemente si el empleado aprobó.

---

### 5.4 Evaluación de Riesgos

**`peligros`** — Tipos: físico, químico, biológico, ergonómico, psicosocial, mecánico, eléctrico, locativo, fenómeno natural.

**`evaluaciones_riesgo`** — Probabilidad (1-5) × Severidad (1-5) → Nivel: bajo/medio/alto/crítico.

**`medidas_control`** — 5 tipos según jerarquía: eliminación → sustitución → ingeniería → administrativo → EPP.

---

### 5.5 Auditorías Internas

**`auditorias`** → **`hallazgos`** → **`no_conformidades`**

Hallazgos clasificados en: conformidad, NC menor, NC mayor, observación.

---

### 5.6 Chat IA

**`chat_historial`** — Mensajes y respuestas de SASBOT por usuario, con timestamp.

---

## 6. Autenticación y Autorización

### Flujo de Login

```
POST /auth/login
1. Valida reCAPTCHA (bypass en ENVIRONMENT=development)
2. Busca usuario activo por email
3. Verifica bloqueo por intentos fallidos (5 intentos → 5 min de bloqueo)
4. Verifica contraseña con bcrypt
5. Genera nuevo session_token (invalida sesión anterior — sesión única)
6. Crea JWT: { sub: user.id, role: user.role, sid: session_token }
7. Retorna access_token + role + nombre
```

### Verificación en Endpoints Protegidos

```
Header: Authorization: Bearer <token>
→ HTTPBearer extrae token
→ decode_token() valida firma y expiración
→ Busca User activo en BD
→ Verifica session_token (sesión única)
→ require_role() verifica que user.role.value esté en los roles permitidos
```

### Roles

| Rol | Descripción | Acceso |
|---|---|---|
| `admin` | Superadministrador | Crear empresas (header `X-Admin-Key`) |
| `sst` | Encargado SST | Todo: incidentes, capacitaciones, riesgos, auditorías, usuarios, métricas |
| `gerencia` | Gerente/Directivo | Dashboard, métricas, reportes (solo lectura) |
| `empleado` | Trabajador | Reportar incidentes, capacitaciones, chat IA |

---

## 7. Endpoints Completos

### Autenticación (`/auth`)

| Método | Endpoint | Protegido | Descripción |
|---|---|---|---|
| POST | `/auth/login` | No | Login, retorna JWT. Rate limit: 20/min |
| POST | `/auth/register` | `sst` | Crea usuario con contraseña explícita |
| POST | `/auth/forgot-password` | No | Envía enlace de recuperación (30 min) |
| POST | `/auth/reset-password` | No | Actualiza contraseña con token |

### Usuarios (`/usuarios`)

| Método | Endpoint | Rol | Descripción |
|---|---|---|---|
| GET | `/usuarios/` | `sst` | Lista usuarios de la empresa |
| GET | `/usuarios/{id}` | `sst` | Detalle de usuario |
| POST | `/usuarios/` | `sst` | Crea usuario + envía correo bienvenida con contraseña temporal |
| PATCH | `/usuarios/{id}` | `sst` | Actualiza nombre, área, cargo, activo |

### Incidentes (`/incidentes`)

| Método | Endpoint | Rol | Descripción |
|---|---|---|---|
| GET | `/incidentes/` | Todos | Lista con filtros |
| POST | `/incidentes/` | Todos | Reportar incidente |
| GET | `/incidentes/{id}` | Todos | Detalle completo |
| PATCH | `/incidentes/{id}/estado` | `sst` | Cambiar estado del ciclo de vida |
| GET | `/incidentes/{id}/progreso` | Todos | % acciones completadas |
| POST | `/incidentes/{id}/investigacion` | `sst` | Crear investigación de causas |
| POST | `/incidentes/{id}/acciones` | `sst` | Crear acción correctiva |
| PATCH | `/incidentes/acciones/{id}` | `sst` | Actualizar acción correctiva |
| GET | `/incidentes/{id}/furat` | `sst` | Descargar FURAT en PDF |

### Capacitaciones (`/capacitaciones`)

| Método | Endpoint | Rol | Descripción |
|---|---|---|---|
| GET | `/capacitaciones/` | Todos | Lista capacitaciones |
| POST | `/capacitaciones/` | `sst` | Crear capacitación |
| GET | `/capacitaciones/cobertura` | `sst`, `gerencia` | % cobertura del plan |
| POST | `/capacitaciones/sesiones` | `sst` | Programar sesión |
| GET | `/capacitaciones/{id}/sesiones` | Todos | Sesiones de una capacitación |
| POST | `/capacitaciones/asistencia` | `sst` | Registrar asistencia |
| GET | `/capacitaciones/sesiones/{id}/asistencia` | `sst` | Asistencia de sesión |
| GET | `/capacitaciones/empleados/{id}/historial` | `sst` | Historial del empleado |
| POST | `/capacitaciones/evaluaciones` | `sst` | Crear evaluación con preguntas |
| POST | `/capacitaciones/evaluaciones/responder` | Todos | Empleado responde evaluación |
| GET | `/capacitaciones/evaluaciones/{id}/certificado/{empleado_id}` | Todos | Certificado PDF |

### Métricas (`/metricas`)

| Método | Endpoint | Rol | Descripción |
|---|---|---|---|
| GET | `/metricas/kpis` | `sst`, `gerencia` | KPIs de accidentalidad |
| GET | `/metricas/dashboard-gerencia` | `sst`, `gerencia` | Dashboard ejecutivo |
| GET | `/metricas/alertas` | `sst` | Alertas activas (incidentes sin investigación, acciones vencidas) |
| GET | `/metricas/reporte-pdf?periodo=mensual` | `sst`, `gerencia` | Reporte PDF |
| GET | `/metricas/reporte-excel?periodo=mensual` | `sst`, `gerencia` | Reporte Excel |

### Riesgos (`/riesgos`)

| Método | Endpoint | Rol | Descripción |
|---|---|---|---|
| GET | `/riesgos/peligros` | Todos | Lista peligros (filtros: tipo, area_id) |
| POST | `/riesgos/peligros` | `sst` | Crear peligro |
| GET | `/riesgos/peligros/{id}` | Todos | Detalle con evaluaciones y controles |
| POST | `/riesgos/peligros/{id}/evaluar` | `sst` | Evaluar nivel de riesgo |
| GET | `/riesgos/matriz` | `sst`, `gerencia` | Matriz de riesgos |
| POST | `/riesgos/peligros/{id}/controles` | `sst` | Crear medida de control |
| PATCH | `/riesgos/controles/{id}` | `sst` | Actualizar medida de control |

### Auditorías (`/auditorias`)

| Método | Endpoint | Rol | Descripción |
|---|---|---|---|
| GET | `/auditorias/` | `sst`, `gerencia` | Lista auditorías |
| POST | `/auditorias/` | `sst` | Planificar auditoría |
| PATCH | `/auditorias/{id}/estado` | `sst` | Cambiar estado |
| GET | `/auditorias/{id}/progreso` | `sst`, `gerencia` | % NC cerradas |
| POST | `/auditorias/{id}/hallazgos` | `sst` | Registrar hallazgo |
| GET | `/auditorias/{id}/hallazgos` | `sst`, `gerencia` | Lista hallazgos |
| POST | `/auditorias/hallazgos/{id}/nc` | `sst` | Crear no conformidad |
| PATCH | `/auditorias/nc/{id}` | `sst` | Actualizar NC |

### Chat IA (`/chat`)

| Método | Endpoint | Rol | Descripción |
|---|---|---|---|
| POST | `/chat/mensaje` | Todos | Enviar mensaje a SASBOT |
| GET | `/chat/historial` | Todos | Historial de conversaciones |
| POST | `/chat/reporte-rapido` | Todos | Reportar incidente de emergencia vía IA |

### Áreas y Cargos (`/areas`, `/cargos`)

| Método | Endpoint | Rol | Descripción |
|---|---|---|---|
| GET | `/areas/` | `sst` | Lista áreas |
| POST | `/areas/` | `sst` | Crear área |
| GET | `/cargos/` | `sst` | Lista cargos |
| POST | `/cargos/` | `sst` | Crear cargo |

### Admin (`/admin`) — Requiere header `X-Admin-Key`

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/admin/empresas` | Crear nueva empresa |
| GET | `/admin/empresas` | Listar todas las empresas |

---

## 8. Características del Sistema

### Multi-Tenancy
Todo filtrado por `empresa_id` extraído del JWT (no del request). El cliente no puede manipular a qué empresa pertenecen sus datos.

### Seguridad
- Contraseñas: bcrypt con salt (nunca texto plano)
- JWT: HS256, 30 min de expiración (configurable)
- Sesión única: cada login invalida sesiones previas
- Rate limiting: 20 intentos/minuto en login
- Bloqueo de cuenta: 5 intentos fallidos → 5 minutos bloqueado
- reCAPTCHA: en login (bypass automático en `development`)
- CORS: configurado para localhost y dominios de producción
- SSL: obligatorio en Neon

### KPIs Calculados Automáticamente
- **Tasa de Accidentalidad** = (accidentes / trabajadores) × 100
- **Índice de Frecuencia** = (accidentes / horas trabajadas) × 1,000,000
- **Índice de Severidad** = (días perdidos / horas trabajadas) × 1,000,000

### SASBOT (Chat IA)
- Motor: Gemini 2.5 Flash
- Contexto: respuestas adaptadas según cargo y área del empleado
- Detecta emergencias automáticamente y activa modo urgencia
- Basado en normativa colombiana SST

---

## 9. Variables de Entorno

```env
# Base de datos (Neon PostgreSQL)
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require

# JWT
SECRET_KEY=<cadena aleatoria de 64+ caracteres>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google Gemini (SASBOT)
GEMINI_API_KEY=AIza...

# reCAPTCHA v2/v3
RECAPTCHA_SECRET_KEY=6Lc...

# Resend (correos)
RESEND_API_KEY=re_...
FROM_EMAIL=noreply@tudominio.com

# Frontend (para links en correos)
FRONTEND_URL=https://pisst-frontend.vercel.app

# Entorno
ENVIRONMENT=development   # o production

# Admin
ADMIN_SECRET_KEY=<clave-secreta-admin>
```

---

## 10. Comandos de Desarrollo

```bash
# Crear entorno virtual
python -m venv venv
venv\Scripts\activate          # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env           # (si existiera; por ahora copiar manualmente)

# Migraciones
alembic upgrade head            # Aplicar todas las migraciones
alembic revision --autogenerate -m "descripcion"  # Nueva migración

# Datos de prueba
python seed.py

# Servidor de desarrollo
uvicorn main:app --reload

# Documentación interactiva (solo en ENVIRONMENT=development)
# http://localhost:8000/docs
# http://localhost:8000/redoc
```

---

## 11. Decisiones de Diseño Relevantes

1. **Multi-tenancy plano:** `empresa_id` en todas las tablas principales. Simple y efectivo para el número de empresas esperado.
2. **Sesión única por usuario:** Cada login genera un nuevo `session_token` que invalida el anterior. Previene sesiones simultáneas.
3. **Contraseña temporal en creación de usuario:** La genera el sistema y se envía por correo. El SST nunca la define ni la ve.
4. **`puntaje_final` redundante en respuestas:** Una fila por pregunta respondida, pero todas llevan el puntaje total del intento. Facilita la búsqueda de certificados sin JOIN adicionales.
5. **Soft delete con `activo=False`:** Preserva el historial y permite recuperación de datos.
6. **Mensaje genérico en forgot-password:** Previene enumeración de emails registrados.
7. **Docs solo en `development`:** En producción, Swagger/ReDoc/OpenAPI están deshabilitados.
8. **Alembic para migraciones:** Permite cambios de esquema versionados y reversibles con Neon.

---

*Generado automáticamente el 2026-05-27*
