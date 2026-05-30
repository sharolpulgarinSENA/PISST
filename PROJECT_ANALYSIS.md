# PISST — Análisis: Errores, Configuraciones Faltantes y Recomendaciones

> Análisis basado en revisión del código fuente al 2026-05-27.  
> Severidades: 🔴 Crítico · 🟠 Alto · 🟡 Medio · 🔵 Bajo

---

## 1. Errores y Bugs Encontrados

### 🔴 BUG-01 — `/auth/register` no valida que la empresa exista ni que el SST pertenezca a ella

**Archivo:** [app/routers/auth_router.py](app/routers/auth_router.py#L148)  
**Línea:** 165

```python
# Actual — empresa_id viene como string libre del request body
nuevo_usuario = User(
    empresa_id=datos.empresa_id   # ninguna validación
)
```

Un SST autenticado puede crear usuarios en **cualquier empresa** con solo conocer el UUID. Además, `empresa_id` es `str` en el schema, no `UUID`, lo que omite validación de formato.

**Fix:**
```python
# En RegisterRequest: cambiar empresa_id: str  →  empresa_id: UUID
# En el endpoint: ignorar datos.empresa_id y usar current_user.empresa_id
nuevo_usuario = User(empresa_id=current_user.empresa_id, ...)
```

---

### 🔴 BUG-02 — Comparaciones de Enum con string literal en queries SQL

**Archivo:** [app/services/metricas_service.py](app/services/metricas_service.py#L22)  
**Líneas:** 22, 83, 116

```python
# Línea 22 — INCORRECTO
Incidente.tipo == "accidente"          # frágil: compara columna Enum con str

# Línea 83 — INCORRECTO
AccionCorrectiva.estado != "completada"

# Línea 116 — INCORRECTO (también en get_alertas)
Incidente.estado == "abierto"
```

En SQLAlchemy 2.x con columnas `Enum`, comparar contra strings puede fallar silenciosamente o generar queries incorrectas dependiendo del backend.

**Fix:**
```python
from app.models.incidente import TipoIncidenteEnum, EstadoIncidenteEnum
from app.models.accion_correctiva import EstadoAccionEnum

Incidente.tipo == TipoIncidenteEnum.accidente
AccionCorrectiva.estado != EstadoAccionEnum.completada
Incidente.estado == EstadoIncidenteEnum.abierto
```

---

### 🔴 BUG-03 — `reset_token_expira` puede ser `None` y causar TypeError

**Archivo:** [app/routers/auth_router.py](app/routers/auth_router.py#L241)  
**Línea:** 241

```python
if user.reset_token_expira < datetime.utcnow():   # TypeError si es None
```

Si un usuario tiene `reset_token` pero `reset_token_expira` es `None` (e.g., dato corrupto), la comparación lanza `TypeError` y devuelve un 500 en lugar de un 400.

**Fix:**
```python
if not user.reset_token_expira or user.reset_token_expira < datetime.utcnow():
    raise HTTPException(status_code=400, detail="Token expirado")
```

---

### 🟠 BUG-04 — `get_all_users()` incluye usuarios inactivos (soft delete ignorado)

**Archivo:** [app/services/usuario_service.py](app/services/usuario_service.py#L22)  
**Línea:** 22

```python
def get_all_users(db: Session, empresa_id: UUID):
    return db.query(User).filter(User.empresa_id == empresa_id).all()
    # Falta: User.activo == True
```

Usuarios desactivados siguen apareciendo en el listado del SST.

**Fix:**
```python
return db.query(User).filter(
    User.empresa_id == empresa_id,
    User.activo == True
).all()
```

---

### 🟠 BUG-05 — `datetime.utcnow()` deprecado en Python 3.12+

**Archivos:** [app/core/security.py](app/core/security.py#L44), [app/routers/auth_router.py](app/routers/auth_router.py#L99), [app/services/metricas_service.py](app/services/metricas_service.py#L20)

`datetime.utcnow()` fue deprecado en Python 3.12 y genera `DeprecationWarning`. En Python 3.14 será removido.

**Fix:**
```python
from datetime import datetime, timezone

# Antes
datetime.utcnow()

# Después
datetime.now(timezone.utc).replace(tzinfo=None)  # para mantener naive datetime
# o idealmente: datetime.now(timezone.utc) y usar timezone-aware en toda la app
```

---

### 🟠 BUG-06 — `SECRET_KEY` puede ser `None` sin validación al arranque

**Archivo:** [app/core/security.py](app/core/security.py#L14)

```python
SECRET_KEY = os.getenv("SECRET_KEY")   # None si no está en .env
```

Si `SECRET_KEY` no está definida, `jwt.encode()` lanzará un error críptico en tiempo de ejecución, no al arrancar el servidor.

**Fix:** Validar al inicio de la aplicación:
```python
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY no está configurada en .env")
```

---

### 🟠 BUG-07 — Paquetes Google AI duplicados y potencialmente conflictivos

**Archivo:** [requirements.txt](requirements.txt#L24)

```
google-genai==2.2.0
google-generativeai==0.8.6    # API antigua, en proceso de deprecación
```

Ambos paquetes coexisten. `google-generativeai` es la versión legacy; la nueva es `google-genai`. Pueden surgir conflictos de versiones de `protobuf` o comportamiento inesperado.

**Fix:** Usar solo `google-genai==2.2.0` y actualizar `ai_service.py` para usar la nueva API si ya está siendo usado.

---

### 🟡 BUG-08 — Sin paginación en endpoints de listado

**Archivos:** `incidente_router.py`, `usuario_router.py`, `riesgo_router.py`, `auditoria_router.py`

Todos los `GET /` retornan la colección completa. Con crecimiento de datos puede causar timeouts, respuestas muy pesadas y agotamiento de memoria.

**Fix:** Agregar paginación con `offset` y `limit`:
```python
@router.get("/")
def listar(skip: int = 0, limit: int = 50, ...):
    return db.query(Model).filter(...).offset(skip).limit(limit).all()
```

---

### 🟡 BUG-09 — `passlib 1.7.4` con advertencias de deprecación por bcrypt 4.x

**Archivo:** [requirements.txt](requirements.txt)

`passlib` no ha tenido una release en 2+ años y tiene problemas de compatibilidad con `bcrypt>=4.0`. Genera `AttributeError: module 'bcrypt' has no attribute '__about__'` en algunos entornos.

**Fix temporal:**
```
bcrypt==4.0.1   # ya fijado, correcto
passlib==1.7.4  # con warning; funciona pero genera ruido en logs
```

**Fix definitivo:** Migrar a `pwdlib` o usar `bcrypt` directamente sin passlib.

---

### 🔵 BUG-10 — Import inconsistente en `main.py`

**Archivo:** [main.py](main.py#L9)  

Los primeros 9 routers se importan como módulos (`from app.routers import auth_router`) mientras que `area_router` y `cargo_router` se importan como objetos (`from app.routers.area_router import router as area_router`). No es un bug funcional pero rompe la consistencia del patrón.

---

## 2. Configuraciones Faltantes

### 🔴 CONFIG-01 — No existe `.env.example`

No hay un archivo `.env.example` en el repositorio. Cualquier developer nuevo o deployment en un servidor nuevo no sabe qué variables configurar.

**Solución:** Crear `.env.example`:
```env
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
SECRET_KEY=genera-con-python-c-import-secrets-print-secrets-token-hex-32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
GEMINI_API_KEY=
RECAPTCHA_SECRET_KEY=
RESEND_API_KEY=
FROM_EMAIL=noreply@tudominio.com
FRONTEND_URL=http://localhost:5173
ENVIRONMENT=development
ADMIN_SECRET_KEY=
```

---

### 🔴 CONFIG-02 — `.env` puede estar en el repositorio git (sin `.gitignore` verificado)

Si `.env` contiene credenciales reales y está commiteado, las claves de API y la URL de la base de datos están expuestas en el historial de git.

**Verificar:**
```bash
git log --all --full-history -- .env
cat .gitignore | grep .env
```

**Solución:** Asegurarse que `.gitignore` contenga:
```
.env
*.env
```

---

### 🟠 CONFIG-03 — Sin validación de variables de entorno al arranque

No hay un check de startup que valide que todas las variables requeridas estén presentes.

**Solución:** Agregar en `main.py`:
```python
REQUIRED_ENV = ["DATABASE_URL", "SECRET_KEY", "GEMINI_API_KEY", "RESEND_API_KEY"]

@app.on_event("startup")
def check_env():
    missing = [v for v in REQUIRED_ENV if not os.getenv(v)]
    if missing:
        raise RuntimeError(f"Variables de entorno faltantes: {missing}")
```

---

### 🟠 CONFIG-04 — Sin health check de base de datos

El endpoint `GET /` responde `{"status": "ok"}` sin verificar que la BD esté accesible.

**Solución:**
```python
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
```

---

### 🟠 CONFIG-05 — Sin configuración de logging estructurado

No hay logging configurado. Los `print()` de advertencia (como `"⚠️ Correo no enviado"`) no se registran en ningún sistema de observabilidad.

**Solución:**
```python
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Reemplazar todos los print() por:
logger.warning(f"Correo no enviado a {email}")
logger.error(f"Error en operación: {e}")
```

---

### 🟡 CONFIG-06 — Sin configuración de CORS para producción específica

**Archivo:** [main.py](main.py#L38)

```python
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://pisst-frontend.vercel.app",
    os.getenv("FRONTEND_URL", ""),   # vacío si no está configurado
]
```

En producción, si `FRONTEND_URL` no está seteado, se agrega una string vacía al listado de origins (aunque el filtro `if o` lo excluye, es frágil).

---

### 🟡 CONFIG-07 — Sin `Dockerfile` para desarrollo local consistente

No hay `Dockerfile` ni `docker-compose.yml`. El setup local depende de que PostgreSQL esté instalado o de conectar a Neon directamente.

**Solución:** Un `docker-compose.yml` mínimo con PostgreSQL local para desarrollo:
```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: pisst_dev
      POSTGRES_USER: pisst
      POSTGRES_PASSWORD: dev
    ports:
      - "5432:5432"
```

---

### 🔵 CONFIG-08 — Sin índices de base de datos explícitos en modelos críticos

Las consultas frecuentes sobre `empresa_id`, `email`, `estado` e `incidente_id` no tienen índices declarados en los modelos SQLAlchemy. Neon los creará implícitamente para PK y FK en algunos casos, pero no siempre.

**Solución:** Agregar en los modelos de mayor tráfico:
```python
__table_args__ = (
    Index('ix_incidentes_empresa_estado', 'empresa_id', 'estado'),
)
```

---

## 3. Recomendaciones

### 🔴 REC-01 — Forzar cambio de contraseña en primer login

Cuando el SST crea un usuario con contraseña temporal, el empleado debería ser forzado a cambiarla en su primer login. Actualmente puede operar indefinidamente con la contraseña temporal.

**Implementación:**
1. Agregar campo `debe_cambiar_password: Boolean` en el modelo `User`.
2. Al crear usuario, establecerlo en `True`.
3. En `get_current_user()`, si `user.debe_cambiar_password == True`, retornar error 403 con código especial que el frontend interprete y redirija al formulario de cambio.

---

### 🟠 REC-02 — Separar `/auth/register` de `/usuarios/` o unificarlos

Existen dos formas de crear usuarios:
- `POST /auth/register` — contraseña explícita, `empresa_id` desde el request body (sin aislamiento multi-tenant)
- `POST /usuarios/` — contraseña temporal generada, `empresa_id` desde el JWT (correcto)

El endpoint `/auth/register` tiene el BUG-01 (falta de aislamiento de empresa) y además expone la contraseña en el request. Debería eliminarse o restringirse solo a uso interno/admin.

---

### 🟠 REC-03 — Agregar refresh tokens

El JWT expira en 30 minutos y no hay mecanismo de renovación. El usuario debe hacer login nuevamente cada 30 minutos, lo que es una mala experiencia.

**Implementación:**
- JWT de acceso: 30 min
- Refresh token: 7 días, guardado en BD
- `POST /auth/refresh` valida el refresh token y emite un nuevo access token

---

### 🟠 REC-04 — Rate limiting por usuario, no solo por IP

**Archivo:** [main.py](main.py#L34)

```python
limiter = Limiter(key_func=get_remote_address)
```

Detrás de un proxy o NAT corporativo, todos los usuarios comparten la misma IP. Un único usuario haciendo muchos requests podría bloquear a todos.

**Solución:** Rate limiting por user_id cuando el usuario está autenticado:
```python
def get_rate_limit_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth:
        # Extraer user_id del JWT sin validar para usar como key
        return auth[-20:]  # sufijo del token como discriminador
    return get_remote_address(request)
```

---

### 🟡 REC-05 — Agregar tests automatizados

No existe directorio `tests/`. No hay cobertura de tests unitarios ni de integración. Esto hace que cada cambio sea un riesgo potencial de regresión.

**Mínimo recomendado:**
```
tests/
├── conftest.py           # fixtures: DB de test, cliente HTTP, usuarios
├── test_auth.py          # login, bloqueo, forgot-password
├── test_incidentes.py    # CRUD, ciclo de vida, FURAT
├── test_metricas.py      # KPIs, división por cero
└── test_usuarios.py      # crear, listar, actualizar
```

Stack sugerido: `pytest` + `httpx` (cliente async) + SQLite en memoria para tests.

---

### 🟡 REC-06 — Validar el parámetro `periodo` en reportes

**Revisar:** `metricas_router.py` endpoints de reporte

El parámetro `?periodo=mensual` debería validarse contra una lista de valores permitidos (`mensual`, `trimestral`, `anual`) antes de llegar al servicio. Si no está validado, una entrada arbitraria puede llegar a la generación de PDF/Excel.

**Fix:**
```python
from typing import Literal

@router.get("/reporte-pdf")
def reporte_pdf(
    periodo: Literal["mensual", "trimestral", "anual"] = "mensual",
    ...
):
```

---

### 🟡 REC-07 — Agregar auditoría de acciones sensibles

No hay registro de quién hizo qué. Operaciones críticas como cerrar un incidente, cambiar un estado de auditoría, o crear un usuario no dejan rastro más allá de los campos `fecha_creacion`/`fecha_actualizacion`.

**Implementación mínima:** Tabla `audit_log` con:
- `user_id`, `accion`, `entidad`, `entidad_id`, `datos_anteriores (JSON)`, `timestamp`

---

### 🔵 REC-08 — Consistencia en imports de routers en `main.py`

**Archivo:** [main.py](main.py#L9)

Estandarizar el patrón de importación para todos los routers:
```python
# Patrón consistente (elegir uno):
from app.routers.area_router import router as area_router
from app.routers.auth_router import router as auth_router
# ...
```

---

### 🔵 REC-09 — Eliminar `print()` de debug en producción

Se usan `print()` para logging de advertencias. En Render/producción estos van a stdout pero no son observables ni filtrables.

**Archivos afectados:** `usuario_service.py`, `auth_router.py`, otros.

Reemplazar con el módulo `logging` (ver CONFIG-05).

---

### 🔵 REC-10 — Documentar convención para nuevas migraciones

El directorio `migrations/versions/` tiene archivos nombrados por sprint. Establecer una convención explícita en un `CONTRIBUTING.md` o en este mismo documento:

```bash
# Convención recomendada:
alembic revision --autogenerate -m "sprint_X_descripcion_corta"
# Ejemplo:
alembic revision --autogenerate -m "sprint_4_agregar_indice_empresa_id"
```

---

## Resumen por Prioridad

| Prioridad | Items |
|---|---|
| 🔴 Crítico (resolver antes de producción) | BUG-01, BUG-02, BUG-03, CONFIG-01, CONFIG-02 |
| 🟠 Alto (resolver en el próximo sprint) | BUG-04, BUG-05, BUG-06, BUG-07, CONFIG-03, CONFIG-04, CONFIG-05, REC-01, REC-02, REC-03 |
| 🟡 Medio (backlog prioritario) | BUG-08, BUG-09, CONFIG-06, CONFIG-07, REC-04, REC-05, REC-06, REC-07 |
| 🔵 Bajo (mejoras de calidad) | BUG-10, CONFIG-08, REC-08, REC-09, REC-10 |

---

*Generado automáticamente el 2026-05-27*
