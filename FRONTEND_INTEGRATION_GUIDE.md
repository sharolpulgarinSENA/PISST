# Guía de Integración Frontend — PISST Backend Sprint 4
> Fecha: 2026-05-28 | Rama backend: `barner-acosta`  
> Este documento describe **todos los cambios del backend** que el frontend debe implementar o tener en cuenta.

---

## CAMBIOS CRÍTICOS — El frontend DEBE implementar esto

### 1. Login — nuevo campo `refresh_token` en la respuesta

**Endpoint:** `POST /auth/login`

La respuesta ahora incluye un `refresh_token` adicional:

```json
{
  "access_token": "eyJ...",
  "refresh_token": "14bc1e7106c3a0bbe56a17bdc39c705e0b49b7a0f...",
  "token_type": "bearer",
  "role": "sst",
  "nombre": "Juan Pérez"
}
```

**Qué debe hacer el frontend:**
- Guardar el `refresh_token` junto al `access_token` (localStorage, cookie segura, etc.)
- El `access_token` expira en **30 minutos**
- El `refresh_token` expira en **7 días**

---

### 2. Renovar el access token automáticamente

**Endpoint nuevo:** `POST /auth/refresh`

Cuando el servidor responda `401` por token expirado, el frontend debe llamar este endpoint automáticamente antes de redirigir al login.

**Request:**
```json
{ "refresh_token": "el-refresh-token-guardado" }
```

**Response exitosa (200):**
```json
{ "access_token": "eyJ...", "token_type": "bearer" }
```

**Flujo recomendado (interceptor de axios o fetch):**
```
Petición falla con 401
        ↓
¿Hay refresh_token guardado?
        ↓ Sí
POST /auth/refresh
        ↓ 200 OK
Guardar nuevo access_token
Reintentar petición original
        ↓ Si /auth/refresh responde 401
Redirigir al login (refresh expirado)
```

---

### 3. Cambio de contraseña obligatorio en primer login — FLUJO NUEVO

**Comportamiento:** Cuando el SST crea un empleado, ese empleado tiene una contraseña temporal. Al intentar acceder a cualquier endpoint protegido con su token, el servidor responderá:

```json
HTTP 403
{ "detail": "debe_cambiar_password" }
```

**Importante:** Esto puede ocurrir en CUALQUIER endpoint protegido, no solo en el login.

**Qué debe hacer el frontend:**
- En el interceptor global de respuestas HTTP, detectar `status === 403 && detail === "debe_cambiar_password"`
- Redirigir inmediatamente al formulario de cambio de contraseña
- No mostrar el error genérico de "Acceso denegado"

**Endpoint para cambiar contraseña:** `POST /auth/cambiar-password`

> ⚠️ Este endpoint NO requiere que el usuario haya cambiado su contraseña para funcionar. Es el único endpoint al que puede acceder un usuario con `debe_cambiar_password=True` además del login.

**Request:**
```json
{
  "password_actual": "contraseñaTemporal123",
  "nueva_password": "miNuevaContraseña456"
}
```

**Headers:** `Authorization: Bearer <access_token>`

**Response exitosa (200):**
```json
{ "mensaje": "Contraseña cambiada exitosamente" }
```

**Errores:**
- `400` — contraseña actual incorrecta
- `401` — token inválido o expirado

**Flujo completo del primer login:**
```
Empleado recibe contraseña temporal por correo
        ↓
Login → 200 OK (funciona normal)
        ↓
Intenta acceder a cualquier pantalla
        ↓
403 "debe_cambiar_password"
        ↓
Frontend redirige a /cambiar-password
        ↓
POST /auth/cambiar-password → 200 OK
        ↓
Login nuevamente con nueva contraseña
        ↓
Acceso normal ✅
```

---

## CAMBIOS IMPORTANTES — El frontend debe ajustarse

### 4. Paginación en endpoints de listado

Los siguientes endpoints ahora tienen un límite máximo de **50 registros por defecto**. Si el frontend esperaba recibir todos los registros de una sola vez, debe implementar paginación.

| Endpoint | Parámetros nuevos |
|---|---|
| `GET /incidentes/` | `?skip=0&limit=50` |
| `GET /usuarios/` | `?skip=0&limit=50` |
| `GET /riesgos/peligros` | `?skip=0&limit=50` |
| `GET /auditorias/` | `?skip=0&limit=50` |

**Ejemplo:**
```
GET /incidentes/?skip=0&limit=10   → primera página
GET /incidentes/?skip=10&limit=10  → segunda página
GET /incidentes/?skip=20&limit=10  → tercera página
```

**Sin parámetros** → devuelve máximo 50 registros (comportamiento seguro por defecto).

---

### 5. Endpoint `/auth/register` — solo para admin

`POST /auth/register` ahora solo acepta tokens con rol `admin`.

**Si el frontend tiene algún flujo que use este endpoint con un token SST, debe cambiarlo a `POST /usuarios/`.**

| Endpoint | Quién puede usarlo | Diferencia |
|---|---|---|
| `POST /usuarios/` | SST | Genera contraseña temporal automáticamente |
| `POST /auth/register` | Solo admin | Requiere contraseña explícita en el body |

---

### 6. Validación del parámetro `periodo` en reportes

**Endpoints:**
- `GET /metricas/reporte-pdf?periodo=mensual`
- `GET /metricas/reporte-excel?periodo=mensual`

**Valores válidos únicamente:** `mensual`, `trimestral`, `anual`

Si se envía otro valor, el servidor responde `422 Unprocessable Entity`. El frontend debe restringir este campo a un selector con solo esas 3 opciones.

---

## CAMBIOS MENORES — Informativos

### 7. Health check mejorado

`GET /` ahora incluye el estado de la base de datos:

```json
{ "status": "ok", "db": "connected", "proyecto": "PISST", "version": "1.0.0" }
```

Si la BD no está disponible: `503 Service Unavailable`.

---

### 8. Mensajes de error más claros al arranque

Si el servidor arranca sin las variables de entorno requeridas (`SECRET_KEY`, `DATABASE_URL`, etc.), lanza un error inmediato en lugar de fallar silenciosamente. Esto no afecta al frontend pero facilita el debugging en deploy.

---

## Resumen de endpoints nuevos

| Método | Endpoint | Auth requerida | Descripción |
|---|---|---|---|
| `POST` | `/auth/refresh` | No | Renovar access token con refresh token |
| `POST` | `/auth/cambiar-password` | Sí (Bearer) | Cambiar contraseña (primer login o voluntario) |

## Resumen de endpoints que cambiaron

| Endpoint | Qué cambió |
|---|---|
| `POST /auth/login` | Respuesta incluye `refresh_token` |
| `POST /auth/register` | Solo accesible por rol `admin` |
| `GET /incidentes/` | Soporta `?skip=&limit=`, máximo 50 por defecto |
| `GET /usuarios/` | Soporta `?skip=&limit=`, máximo 50 por defecto |
| `GET /riesgos/peligros` | Soporta `?skip=&limit=`, máximo 50 por defecto |
| `GET /auditorias/` | Soporta `?skip=&limit=`, máximo 50 por defecto |
| `GET /metricas/reporte-pdf` | Parámetro `periodo` validado: solo `mensual`, `trimestral`, `anual` |
| `GET /metricas/reporte-excel` | Parámetro `periodo` validado: solo `mensual`, `trimestral`, `anual` |
| `GET /` | Incluye campo `db: "connected"` en la respuesta |

## Códigos de error nuevos que el frontend debe manejar

| Código | `detail` | Cuándo ocurre | Acción recomendada |
|---|---|---|---|
| `403` | `"debe_cambiar_password"` | Usuario con contraseña temporal intenta acceder | Redirigir a formulario de cambio de contraseña |
| `401` | `"Token inválido o expirado"` | Access token vencido | Llamar a `/auth/refresh` automáticamente |
| `422` | Detalle de validación | Parámetro `periodo` con valor inválido | Usar solo valores permitidos en el selector |
| `503` | `"Base de datos no disponible"` | BD caída | Mostrar pantalla de mantenimiento |

---

*Generado el 2026-05-28 — Para dudas contactar al desarrollador backend (rama `barner-acosta`)*
