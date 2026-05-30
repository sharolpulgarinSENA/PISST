# Cambios de Roles y Permisos — Backend PISST
> Fecha: 2026-05-29 | Rama: `barner-acosta` → `Dev` → `main`  
> Para el equipo de frontend y backend.

---

## ¿Qué cambió?

Se redefinieron las reglas de creación de usuarios para cumplir con el modelo de negocio correcto.

---

## Nueva Matriz de Permisos

| Rol | Puede crear | Restricción |
|---|---|---|
| **Admin** | Empresas | Sin límite |
| **Admin** | Usuario SST | Solo 1 por empresa |
| **Admin** | Usuario Gerencia | Solo 1 por empresa |
| **SST** | Empleados | Solo rol `empleado`, con área y cargo |
| **SST** | ~~SST, Gerencia, Admin~~ | ❌ Bloqueado |
| **Gerencia** | Ninguno | Solo consulta |

---

## Cambios en los Endpoints

### `POST /usuarios/` — Ahora restringido a rol `empleado`

El SST ya **no puede** crear usuarios con rol `sst`, `gerencia` o `admin`.

**Si intenta crear un usuario con otro rol:**
```json
HTTP 403
{
  "detail": "El SST solo puede crear usuarios con rol empleado"
}
```

**Lo que sí puede hacer el SST:**
```json
POST /usuarios/
Authorization: Bearer <token_sst>

{
  "nombre": "Juan Pérez",
  "email": "juan@empresa.com",
  "role": "empleado",
  "area_nombre": "Producción",
  "cargo_nombre": "Operario de Máquina"
}
```

---

### `POST /admin/crear-sst` — Solo 1 SST por empresa

Si la empresa ya tiene un SST activo y se intenta crear otro:
```json
HTTP 400
{
  "detail": "Esta empresa ya tiene un usuario SST activo"
}
```

---

### `POST /admin/crear-gerencia` — Solo 1 Gerencia por empresa

Si la empresa ya tiene un Gerencia activo y se intenta crear otro:
```json
HTTP 400
{
  "detail": "Esta empresa ya tiene un usuario Gerencia activo"
}
```

---

## Flujo correcto de onboarding de una empresa nueva

```
1. Admin crea la empresa
   POST /admin/empresas

2. Admin crea el SST de la empresa (solo 1)
   POST /admin/crear-sst

3. Admin crea el Gerencia de la empresa (solo 1)
   POST /admin/crear-gerencia

4. SST crea los empleados (ilimitados, solo rol empleado)
   POST /usuarios/
```

---

## Cambio adicional — `GET /cargos/` devuelve área

El endpoint de cargos ahora incluye `area_id` y `area_nombre` en la respuesta para que el frontend pueda filtrar cargos por área seleccionada.

**Antes:**
```json
[
  { "id": "uuid", "nombre": "Operario" }
]
```

**Ahora:**
```json
[
  {
    "id": "uuid",
    "nombre": "Operario",
    "area_id": "uuid-del-area",
    "area_nombre": "Producción"
  }
]
```

---

## Resumen de errores nuevos que el frontend debe manejar

| Código | Mensaje | Cuándo ocurre |
|---|---|---|
| `403` | `"El SST solo puede crear usuarios con rol empleado"` | SST intenta crear SST/gerencia/admin |
| `400` | `"Esta empresa ya tiene un usuario SST activo"` | Admin intenta crear segundo SST |
| `400` | `"Esta empresa ya tiene un usuario Gerencia activo"` | Admin intenta crear segunda gerencia |

---

*Generado el 2026-05-29 — Cambios en `main` y `Dev`.*
