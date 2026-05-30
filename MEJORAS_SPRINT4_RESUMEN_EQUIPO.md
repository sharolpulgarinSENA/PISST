# Resumen de Mejoras — Sprint 4 & Revisión Técnica
> Fecha: 2026-05-29 | Rama: `barner-acosta` → `Dev` → `main`  
> Para compartir con el equipo de desarrollo.

---

## ¿Qué se hizo?

Se realizó una revisión técnica completa del backend de PISST y se aplicaron **35 mejoras** organizadas en 5 categorías.

---

## 1. Seguridad

| Mejora | Detalle |
|---|---|
| **Aislamiento multi-tenant** | `/auth/register` ya no acepta `empresa_id` del body — lo toma del JWT. Un SST no puede crear usuarios en otra empresa. |
| **Validación de fortaleza de contraseña** | `cambiar-password`, `reset-password` y `register` exigen mínimo 8 caracteres, mayúscula, minúscula, número y símbolo. |
| **Restricción de `/auth/register`** | Solo el rol `admin` puede usarlo. Los SST deben usar `POST /usuarios/`. |
| **Guard contra `None` en reset token** | Evita error 500 si `reset_token_expira` es `None` en BD. |
| **Validación de `SECRET_KEY` al arranque** | El servidor no arranca si `SECRET_KEY` no está en `.env`. |
| **Validación de variables de entorno** | Si faltan `DATABASE_URL`, `SECRET_KEY`, `GEMINI_API_KEY` o `RESEND_API_KEY`, el servidor falla rápido con mensaje claro. |
| **CORS por entorno** | `localhost` solo aparece en los origins permitidos si `ENVIRONMENT=development`. En producción solo los dominios reales. |

---

## 2. Nuevas Funcionalidades

| Funcionalidad | Detalle |
|---|---|
| **Refresh tokens** | Login devuelve `access_token` (30 min) y `refresh_token` (7 días). Nuevo endpoint `POST /auth/refresh`. |
| **Cambio de contraseña obligatorio** | Usuarios nuevos tienen `debe_cambiar_password=True`. Al usar cualquier endpoint protegido reciben `403 "debe_cambiar_password"` hasta que cambien su contraseña. Endpoint: `POST /auth/cambiar-password`. |
| **Health check con BD** | `GET /` ahora verifica que la base de datos esté accesible y devuelve `"db": "connected"`. |
| **Auditoría de acciones críticas** | Nueva tabla `audit_logs` en BD. Se registra automáticamente: crear usuario, cambiar estado de incidente, completar acción correctiva. |
| **Paginación en listados** | `GET /incidentes/`, `/usuarios/`, `/riesgos/peligros`, `/auditorias/` aceptan `?skip=0&limit=50`. |
| **Validación de parámetro `periodo`** | Reportes PDF y Excel solo aceptan `mensual`, `trimestral` o `anual`. Cualquier otro valor devuelve `422`. |

---

## 3. Correcciones de Bugs

| Bug | Corrección |
|---|---|
| **Comparaciones Enum con strings** | Queries en `metricas_service.py` usaban `"accidente"` en lugar de `TipoIncidenteEnum.accidente`. Corregido. |
| **Usuarios inactivos en listados** | `get_all_users()` ahora filtra `activo == True`. Los usuarios desactivados ya no aparecen. |
| **`datetime.utcnow()` deprecado** | Reemplazado por `datetime.now(timezone.utc).replace(tzinfo=None)` en todos los archivos (servicios, routers y modelos). |
| **Paquetes Google AI duplicados** | `google-generativeai` (legacy) eliminado. Solo queda `google-genai==2.2.0`. |
| **Encoding UTF-16 en `requirements.txt`** | Convertido a UTF-8 para que pip lo lea correctamente. |
| **Advertencias de `passlib/bcrypt`** | Silenciadas con `warnings.filterwarnings`. El hashing sigue funcionando normalmente. |

---

## 4. Calidad de Código

| Mejora | Detalle |
|---|---|
| **`response_model` en todos los routers** | `incidente_router`, `riesgo_router`, `auditoria_router`, `capacitacion_router` y `admin_router` usan Pydantic en todas las respuestas. Ya no se devuelven dicts arbitrarios. |
| **`PeligroDetailResponse`** | Nuevo schema que incluye evaluaciones y medidas de control anidadas para `GET /riesgos/peligros/{id}`. |
| **Schemas de admin con Pydantic** | `EmpresaResponse`, `EmpresaListItem` y `UsuarioAdminResponse` reemplazan los dicts manuales en `admin_router`. |
| **Migración a Pydantic v2** | Todos los schemas usan `model_config = ConfigDict(from_attributes=True)` en lugar de la clase `Config` de Pydantic v1. |
| **`declarative_base` actualizado** | Migrado de `sqlalchemy.ext.declarative` a `sqlalchemy.orm` (SQLAlchemy 2.0). |
| **Imports limpiados** | Eliminados todos los imports sin usar detectados por flake8. |
| **`manejar_intento_fallido` extraído** | La lógica de bloqueo de cuenta por intentos fallidos vive ahora en una función auxiliar reutilizable. |
| **Logging estructurado** | Todos los `print()` reemplazados por `logging.getLogger(__name__)` con niveles `INFO`, `WARNING` y `ERROR`. |
| **Imports consistentes en `main.py`** | Todos los routers se importan con el mismo patrón `from app.routers import X`. |

---

## 5. Infraestructura y Configuración

| Mejora | Detalle |
|---|---|
| **`.env.example`** | Creado con todas las variables requeridas y descripción de cada una. |
| **`docker-compose.yml`** | PostgreSQL local para desarrollo sin depender de Neon. |
| **Pre-commit hooks** | `black` (formateo) y `flake8` (linting) se ejecutan automáticamente antes de cada `git commit`. Si el código no cumple, el commit se bloquea. |
| **GitHub Actions CI** | Cada `git push` a `barner-acosta`, `Dev` o `main` ejecuta los 11 tests automáticamente en la nube. |
| **Índices en BD** | Tres índices compuestos creados: `ix_incidentes_empresa_estado`, `ix_users_empresa_activo`, `ix_acciones_incidente_estado`. |
| **Rate limiting por token** | El límite de requests se aplica por token de usuario en lugar de solo por IP (evita problemas con NAT corporativo). |

---

## 6. Migraciones Aplicadas en BD

| Migración | Qué agrega |
|---|---|
| `sprint_4_agregar_debe_cambiar_password` | Columna `debe_cambiar_password` en tabla `users` |
| `sprint_4_agregar_refresh_token` | Columnas `refresh_token` y `refresh_token_expira` en `users` |
| `sprint_4_tabla_audit_log` | Nueva tabla `audit_logs` |
| `sprint_4_agregar_indices_criticos` | 3 índices compuestos en BD |

---

## 7. Tests Automatizados

11 tests en verde que cubren:

| Archivo | Qué prueba |
|---|---|
| `test_auth.py` | Login correcto, contraseña incorrecta, email inexistente, bloqueo por intentos, refresh token inválido |
| `test_metricas.py` | KPIs sin datos, no división por cero |
| `test_usuarios.py` | Listar vacíos, solo activos, obtener por ID, ID inexistente |

Para correr los tests:
```bash
pytest tests/ -v
```

---

## Endpoints Nuevos

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/auth/refresh` | Renovar access token sin hacer login |
| `POST` | `/auth/cambiar-password` | Cambiar contraseña (obligatorio en primer login) |

---

## Pendiente para Sprint 5

Ver [SPRINT_5_BACKLOG.md](SPRINT_5_BACKLOG.md) para el detalle.  
Resumen: extraer lógica de `auth_router.py` a `auth_service.py`, más cobertura de tests, agregar `isort`.

---

*Generado el 2026-05-29 — Todos los cambios están en `main` y `Dev`.*
