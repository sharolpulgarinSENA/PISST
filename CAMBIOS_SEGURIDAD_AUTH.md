# Cambios de Seguridad — Autenticación y Logs
> Fecha: 2026-05-29 | Rama: `barner-acosta` → `Dev` → `main`

---

## 1. Nuevo endpoint — `POST /auth/logout`

El frontend ahora debe llamar este endpoint cuando el usuario cierra sesión.
Al hacerlo, el `refresh_token` queda **inutilizable** — aunque alguien lo haya robado, ya no puede usarlo.

**Request:**
```json
POST /auth/logout

{
  "refresh_token": "el-refresh-token-del-usuario"
}
```

**Response (200):**
```json
{ "mensaje": "Sesión cerrada exitosamente" }
```

**Qué hace internamente:**
- Borra el `refresh_token` de la BD
- Borra el `session_token` de la BD
- Cualquier intento posterior de usar ese refresh token devolverá `401`

**Flujo recomendado en el frontend:**
```
Usuario presiona "Cerrar sesión"
        ↓
POST /auth/logout  (con el refresh_token guardado)
        ↓
Eliminar access_token y refresh_token del almacenamiento local
        ↓
Redirigir al login
```

---

## 2. Mensaje de cuenta bloqueada mejorado

Cuando una cuenta se bloquea por demasiados intentos fallidos, el error ahora incluye la **hora exacta** de desbloqueo además de los minutos.

**Antes:**
```json
HTTP 429
{
  "detail": "Cuenta bloqueada por demasiados intentos fallidos. Intenta de nuevo en 5 minuto(s)."
}
```

**Ahora:**
```json
HTTP 429
{
  "detail": "Cuenta bloqueada. Intenta de nuevo en 5 minuto(s) (a las 14:35)."
}
```

**Para el frontend:** puedes mostrar la hora directa al usuario en lugar de calcularla tú mismo.

---

## 3. Emails enmascarados en logs del servidor

Los logs del servidor ya no muestran emails completos. Ahora aparecen enmascarados para proteger datos personales.

**Antes (en logs):**
```
WARNING — Correo no enviado a barner.acosta@gmail.com
```

**Ahora:**
```
WARNING — Correo no enviado a b*************@gmail.com
```

Esto aplica en todos los warnings de correo: bienvenida, reset de contraseña y cambio de contraseña.

---

## Resumen de endpoints nuevos

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| `POST` | `/auth/logout` | No requerida | Invalida el refresh token y cierra la sesión |

## Errores que cambiaron

| Código | Antes | Ahora |
|---|---|---|
| `429` | `"...en X minuto(s)"` | `"...en X minuto(s) (a las HH:MM)"` |

---

*Generado el 2026-05-29 — Cambios en `main` y `Dev`.*
