# Cambios en el módulo de Capacitaciones — PISST Backend

## Resumen de cambios

Se implementaron 3 funcionalidades nuevas en el módulo `/capacitaciones`:

1. **Suspender/activar y editar capacitaciones** — `PATCH /capacitaciones/{id}`
2. **Reprogramar sesiones** — `PATCH /capacitaciones/sesiones/{id}`
3. **Áreas dirigidas (muchos a muchos)** — al crear y listar capacitaciones

---

## 1. Suspender / Activar / Editar capacitación

### Endpoint
```
PATCH /capacitaciones/{capacitacion_id}
Authorization: Bearer <token_sst>
```

### Body (todos los campos son opcionales)
```json
{
  "activo": false,
  "titulo": "Nuevo título",
  "objetivos": "Nuevos objetivos",
  "duracion_horas": 3
}
```

### Ejemplos de uso

**Suspender una capacitación:**
```json
{
  "activo": false
}
```

**Activar una capacitación:**
```json
{
  "activo": true
}
```

**Cambiar título y duración:**
```json
{
  "titulo": "Capacitación en EPP actualizada",
  "duracion_horas": 4
}
```

### Respuesta exitosa (200 OK)
```json
{
  "id": "uuid-de-la-capacitacion",
  "titulo": "Capacitación en EPP actualizada",
  "objetivos": "...",
  "duracion_horas": 4,
  "activo": false,
  "empresa_id": "uuid-empresa",
  "areas": []
}
```

### Permisos
- Solo el rol `sst` puede usar este endpoint.
- Gerencia y empleados reciben `403 Forbidden`.

---

## 2. Reprogramar sesión

### Endpoint
```
PATCH /capacitaciones/sesiones/{sesion_id}
Authorization: Bearer <token_sst>
```

### Body (todos los campos son opcionales)
```json
{
  "fecha": "2026-06-15T09:00:00",
  "lugar": "Sala de conferencias B"
}
```

### Ejemplos de uso

**Solo cambiar la fecha:**
```json
{
  "fecha": "2026-07-01T14:00:00"
}
```

**Solo cambiar el lugar:**
```json
{
  "lugar": "Auditorio principal"
}
```

**Cambiar fecha y lugar:**
```json
{
  "fecha": "2026-07-01T14:00:00",
  "lugar": "Auditorio principal"
}
```

### Respuesta exitosa (200 OK)
```json
{
  "id": "uuid-de-la-sesion",
  "fecha": "2026-07-01T14:00:00",
  "lugar": "Auditorio principal",
  "activa": true,
  "capacitacion_id": "uuid-capacitacion"
}
```

### Permisos
- Solo el rol `sst` puede usar este endpoint.

---

## 3. Áreas dirigidas (relación muchos a muchos)

### Al crear una capacitación

El campo `area_ids` es opcional. Si no se envía, la capacitación se crea sin áreas asignadas.

```
POST /capacitaciones/
Authorization: Bearer <token_sst>
```

### Body
```json
{
  "titulo": "Capacitación en manejo de extintores",
  "objetivos": "Aprender a usar extintores correctamente",
  "duracion_horas": 2,
  "facilitador_id": "uuid-del-facilitador",
  "area_ids": [
    "uuid-area-bodega",
    "uuid-area-produccion"
  ]
}
```

> **Nota:** Los UUIDs de las áreas se obtienen del endpoint `GET /areas/`

### Al listar capacitaciones

La respuesta ahora incluye el campo `areas` con la lista de áreas asignadas:

```
GET /capacitaciones/
Authorization: Bearer <token>
```

### Respuesta
```json
[
  {
    "id": "uuid-capacitacion",
    "titulo": "Capacitación en manejo de extintores",
    "objetivos": "Aprender a usar extintores correctamente",
    "duracion_horas": 2,
    "activo": true,
    "empresa_id": "uuid-empresa",
    "areas": [
      {
        "id": "uuid-area-bodega",
        "nombre": "Bodega"
      },
      {
        "id": "uuid-area-produccion",
        "nombre": "Producción"
      }
    ]
  }
]
```

---

## Tabla resumen de endpoints

| Método | Endpoint | Descripción | Rol requerido |
|--------|----------|-------------|---------------|
| `GET` | `/capacitaciones/` | Listar capacitaciones (incluye áreas) | Todos |
| `POST` | `/capacitaciones/` | Crear capacitación (con `area_ids`) | SST |
| `PATCH` | `/capacitaciones/{id}` | Editar/suspender/activar capacitación | SST |
| `POST` | `/capacitaciones/sesiones` | Crear sesión | SST |
| `PATCH` | `/capacitaciones/sesiones/{id}` | Reprogramar sesión | SST |
| `GET` | `/capacitaciones/{id}/sesiones` | Listar sesiones | Todos |
| `POST` | `/capacitaciones/asistencia` | Registrar asistencia | SST |
| `GET` | `/capacitaciones/sesiones/{id}/asistencia` | Ver asistencia por sesión | SST |
| `GET` | `/capacitaciones/empleados/{id}/historial` | Historial de empleado | SST |
| `POST` | `/capacitaciones/evaluaciones` | Crear evaluación | SST |
| `POST` | `/capacitaciones/evaluaciones/responder` | Responder evaluación | Todos |
| `GET` | `/capacitaciones/evaluaciones/{id}/certificado/{empleado_id}` | Descargar certificado PDF | Todos |
| `GET` | `/capacitaciones/cobertura` | % cobertura del plan anual | SST, Gerencia |

---

## Consideraciones importantes para el frontend

### 1. Formato de fecha
Las fechas deben enviarse en formato ISO 8601:
```
"2026-06-15T09:00:00"
```

### 2. Capacitaciones inactivas
El `GET /capacitaciones/` solo retorna capacitaciones con `activo: true`. Si necesitas mostrar las inactivas (para reactivarlas), deberás manejar esto en el estado local del frontend o solicitar un endpoint adicional.

### 3. Obtener UUIDs de áreas
Para el campo `area_ids` al crear una capacitación, primero debes obtener las áreas disponibles:
```
GET /areas/
Authorization: Bearer <token_sst>
```

### 4. Autenticación
Todos los endpoints requieren el header:
```
Authorization: Bearer <access_token>
```
El token se obtiene del `POST /auth/login`.

### 5. Errores comunes

| Código | Mensaje | Causa |
|--------|---------|-------|
| `401` | Unauthorized | Token no enviado o expirado |
| `403` | Forbidden | Rol sin permisos para ese endpoint |
| `404` | Capacitación no encontrada | UUID incorrecto o no pertenece a la empresa |
| `422` | Unprocessable Entity | Body con formato incorrecto |

---

## Base URL

| Entorno | URL |
|---------|-----|
| Local | `http://localhost:8000` |
| Producción | `https://pisst.onrender.com` |
