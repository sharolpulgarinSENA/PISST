# Cambios de Calidad y Seguridad — Sesión de Revisión Técnica
> Fecha: 2026-05-29 | Rama: `barner-acosta` → `Dev` → `main`  
> Para el equipo de desarrollo.

---

## 1. Nuevo endpoint — `POST /auth/logout`

Antes no existía un logout real. El usuario cerraba sesión solo en el frontend pero el `refresh_token` seguía válido en la BD — si alguien lo robaba, podía usarlo.

**Ahora:** Al hacer logout, el refresh token y la sesión quedan inutilizables en BD.

**Request:**
```json
POST /auth/logout

{ "refresh_token": "el-refresh-token-del-usuario" }
```

**Response (200):**
```json
{ "mensaje": "Sesión cerrada exitosamente" }
```

**Flujo recomendado en frontend:**
```
Usuario presiona "Cerrar sesión"
        ↓
POST /auth/logout
        ↓
Eliminar access_token y refresh_token del storage local
        ↓
Redirigir al login
```

---

## 2. Error de cuenta bloqueada mejorado

Cuando una cuenta se bloquea por intentos fallidos, el error ahora incluye la hora exacta de desbloqueo.

**Antes:**
```json
HTTP 429
{ "detail": "Cuenta bloqueada por demasiados intentos fallidos. Intenta de nuevo en 5 minuto(s)." }
```

**Ahora:**
```json
HTTP 429
{ "detail": "Cuenta bloqueada. Intenta de nuevo en 5 minuto(s) (a las 14:35)." }
```

El frontend puede mostrar la hora directamente al usuario sin calcularla.

---

## 3. Emails enmascarados en logs del servidor

Los logs ya no muestran emails completos para proteger datos personales.

```
ANTES:  WARNING — Correo no enviado a barner.acosta@gmail.com
AHORA:  WARNING — Correo no enviado a b*************@gmail.com
```

Aplica en todos los warnings de correo del sistema.

---

## 4. Validación de tipo en `POST /chat/reporte-rapido`

El campo `tipo` ahora usa `Literal` de Python — si el frontend envía un valor inválido, recibe `422` inmediatamente en lugar de llegar al servicio.

**Valores válidos:** `accidente`, `condicion_insegura`, `cuasi_accidente`, `casi_accidente`

---

## 5. Restricciones de roles en creación de usuarios

Se redefinió quién puede crear qué tipo de usuario.

| Rol | Puede crear | Restricción |
|---|---|---|
| **Admin** | SST | Solo 1 activo por empresa |
| **Admin** | Gerencia | Solo 1 activo por empresa |
| **SST** | Empleados | Solo rol `empleado` |
| **SST** | ~~SST, Gerencia~~ | ❌ Bloqueado con `403` |

**Si el SST intenta crear un usuario con otro rol:**
```json
HTTP 403
{ "detail": "El SST solo puede crear usuarios con rol empleado" }
```

**Si el Admin intenta crear un segundo SST en la misma empresa:**
```json
HTTP 400
{ "detail": "Esta empresa ya tiene un usuario SST activo" }
```

---

## 6. `GET /cargos/` ahora devuelve área

El endpoint de cargos ahora incluye `area_id` y `area_nombre` para que el frontend filtre cargos por área.

**Antes:**
```json
[{ "id": "uuid", "nombre": "Operario" }]
```

**Ahora:**
```json
[{
  "id": "uuid",
  "nombre": "Operario",
  "area_id": "uuid-del-area",
  "area_nombre": "Producción"
}]
```

---

## 7. Herramientas de calidad de código

### isort agregado al pre-commit
Los imports ahora se ordenan automáticamente antes de cada commit:
1. Librerías estándar de Python
2. Librerías de terceros
3. Módulos del proyecto

### Dependabot activado
GitHub creará PRs automáticos cada semana con actualizaciones de dependencias. Si los tests pasan ✅ → hacer merge. Si fallan ❌ → revisar manualmente antes de hacer merge.

---

## 8. CVEs de seguridad resueltos

Se ejecutó `pip-audit` y se encontraron 3 vulnerabilidades reales que fueron corregidas:

| Paquete | Versión anterior | Versión nueva | CVE |
|---|---|---|---|
| `starlette` | 1.0.0 | 1.0.1 | PYSEC-2026-161 |
| `urllib3` | 2.6.3 | 2.7.0 | PYSEC-2026-141/142 |
| `idna` | 3.13 | 3.15 | CVE-2026-45409 |

Además, Dependabot actualizó automáticamente:
- `requests` 2.33.1 → 2.34.2
- `reportlab` 4.5.0 → 4.5.1
- `starlette` 1.0.1 → 1.2.0
- `fastapi` 0.136.1 → 0.136.3
- `greenlet` 3.5.0 → 3.5.1

---

## Resumen de endpoints nuevos

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/auth/logout` | Invalida refresh token y cierra sesión |

## Resumen de errores nuevos que el frontend debe manejar

| Código | `detail` | Cuándo ocurre |
|---|---|---|
| `403` | `"El SST solo puede crear usuarios con rol empleado"` | SST intenta crear SST/gerencia |
| `400` | `"Esta empresa ya tiene un usuario SST activo"` | Admin intenta crear segundo SST |
| `400` | `"Esta empresa ya tiene un usuario Gerencia activo"` | Admin intenta crear segunda gerencia |
| `429` | `"Cuenta bloqueada. Intenta de nuevo en X minuto(s) (a las HH:MM)."` | Cuenta bloqueada por intentos |
| `422` | Detalle de validación | Tipo inválido en reporte-rapido del chat |

---

*Generado el 2026-05-29 — Cambios en `main` y `Dev`.*
