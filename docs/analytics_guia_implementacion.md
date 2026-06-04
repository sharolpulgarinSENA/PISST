# Guía de Implementación — Analítica Integrada en PISST
## Camino B: Módulo analítico dentro del proyecto existente

**Versión:** 1.0 | **Fecha:** 2026-06-04 | **Estado:** Pendiente de implementación

---

## Tabla de Contenidos

1. [Qué vamos a construir](#1-qué-vamos-a-construir)
2. [Archivos a crear y modificar](#2-archivos-a-crear-y-modificar)
3. [Dependencias nuevas](#3-dependencias-nuevas)
4. [Endpoints a implementar](#4-endpoints-a-implementar)
5. [Arquitectura de datos — flujo](#5-arquitectura-de-datos--flujo)
6. [Seguridad](#6-seguridad)
7. [Diseño del servicio](#7-diseño-del-servicio)
8. [Notebooks de prototipado](#8-notebooks-de-prototipado)
9. [Tests](#9-tests)
10. [Orden de implementación](#10-orden-de-implementación)
11. [Qué NO vamos a hacer](#11-qué-no-vamos-a-hacer)
12. [Resultado final esperado](#12-resultado-final-esperado)

---

## 1. Qué vamos a construir

Un módulo de analítica que vive **dentro** del proyecto PISST, completamente de solo lectura, que usa los datos ya existentes en Neon PostgreSQL para generar KPIs avanzados, patrones y alertas usando **Pandas** y **NumPy**.

### Principios de diseño

| Principio | Cómo se aplica |
|-----------|---------------|
| **Aislado** | No toca ningún servicio o router existente |
| **Solo lectura** | Nunca hace `db.add()`, `db.commit()` ni `db.delete()` |
| **No invasivo** | Si falla, el backend principal sigue funcionando |
| **Seguro** | Reutiliza JWT y RBAC exactamente igual que el resto del proyecto |
| **Multi-tenant** | Toda query filtra por `empresa_id` del usuario autenticado |

---

## 2. Archivos a crear y modificar

### Archivos nuevos

```
PISST/
├── app/
│   ├── services/
│   │   └── analytics_service.py       ← lógica con Pandas/NumPy
│   └── routers/
│       └── analytics_router.py        ← endpoints /analytics/*
├── notebooks/
│   ├── 01_exploracion_incidentes.ipynb
│   ├── 02_exploracion_riesgos.ipynb
│   └── 03_exploracion_capacitaciones.ipynb
└── tests/
    └── test_analytics_service.py      ← tests del servicio
```

### Archivos existentes a modificar

| Archivo | Cambio |
|---------|--------|
| `main.py` | Registrar `analytics_router` |
| `requirements.txt` | Agregar `pandas>=2.0.0` y `numpy>=1.24.0` |

---

## 3. Dependencias nuevas

Agregar al `requirements.txt`:

```
pandas>=2.0.0
numpy>=1.24.0
```

> `openpyxl` y `jupyter` ya están instalados en el proyecto — no hace falta agregarlos.

Instalar en el entorno:

```bash
.\venv\Scripts\pip install pandas numpy
```

---

## 4. Endpoints a implementar

Todos viven bajo el prefijo `/analytics` y requieren autenticación JWT.

| Endpoint | Rol requerido | Qué devuelve |
|----------|--------------|--------------|
| `GET /analytics/incidentes` | sst, gerencia | Distribución por tipo, severidad y área. Tasa mensual. Top 3 áreas con más incidentes |
| `GET /analytics/riesgos` | sst, gerencia | Distribución de peligros por nivel (bajo/medio/alto/crítico). % con medidas de control activas |
| `GET /analytics/capacitaciones` | sst, gerencia | Tasa de aprobación global. % asistencia promedio. Alertas de empleados con asistencia < 80% |
| `GET /analytics/cumplimiento` | sst, gerencia | Score general SG-SST (0–100). Desglose por módulo. Tendencia últimos 3 meses |

### Ejemplo de respuesta esperada — `GET /analytics/incidentes`

```json
{
  "total_incidentes": 24,
  "por_tipo": {
    "accidente": 8,
    "incidente": 10,
    "cuasi_accidente": 4,
    "condicion_insegura": 2
  },
  "por_severidad": {
    "leve": 12,
    "moderada": 7,
    "grave": 3,
    "mortal": 0,
    "sin_lesion": 2
  },
  "tasa_mensual_promedio": 3.2,
  "top_areas": ["Producción", "Bodega", "Mantenimiento"],
  "tendencia": "estable"
}
```

### Ejemplo de respuesta esperada — `GET /analytics/capacitaciones`

```json
{
  "total_evaluaciones": 45,
  "tasa_aprobacion_pct": 78.5,
  "asistencia_promedio_pct": 84.2,
  "alertas_asistencia": [
    { "empleado_id": "uuid", "nombre": "Juan P.", "asistencia_pct": 65.0 }
  ],
  "capacitaciones_sin_sesion_realizada": 3
}
```

---

## 5. Arquitectura de datos — flujo

```
Neon PostgreSQL (tablas existentes)
         │
         │  SQLAlchemy — solo .query() — nunca escribe
         ▼
analytics_service.py
         │
         │  pandas.DataFrame  →  numpy  →  métricas calculadas
         ▼
   dict con resultados estructurados
         │
         │  Pydantic response_model (validación automática)
         ▼
analytics_router.py  →  Frontend / Dashboard Gerencia
```

### Tablas que se consultan (solo lectura)

| Tabla | Módulo analítico |
|-------|-----------------|
| `incidentes` | Análisis de incidentes |
| `lesiones` | Días de incapacidad, severidad |
| `peligros` | Análisis de riesgos |
| `evaluaciones_riesgo` | Niveles de riesgo |
| `medidas_control` | % controles aplicados |
| `capacitaciones` | Tasa de cobertura |
| `asistencias` | Alertas de asistencia |
| `respuestas_empleado` | Tasa de aprobación |
| `auditorias` | Cumplimiento |
| `no_conformidades` | Score SG-SST |

---

## 6. Seguridad

No se implementa nada nuevo. Se reutiliza exactamente lo que ya existe en el proyecto.

### Control de acceso

```python
# analytics_router.py — igual que cualquier otro router
from app.core.deps import require_role

@router.get("/incidentes")
def analytics_incidentes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst", "gerencia")),
):
    return analytics_service.analizar_incidentes(db, current_user.empresa_id)
```

### Multi-tenancy

```python
# analytics_service.py — toda query filtra por empresa_id
incidentes = db.query(Incidente).filter(
    Incidente.empresa_id == empresa_id  # ← nunca se omite
).all()
```

### Qué NO puede hacer el servicio analítico

- ❌ `db.add(...)` — no crea registros
- ❌ `db.commit()` — no confirma transacciones
- ❌ `db.delete(...)` — no elimina datos
- ❌ Exponer PII (emails, nombres) sin anonimizar en alertas masivas

---

## 7. Diseño del servicio

### Estructura de `analytics_service.py`

```python
# app/services/analytics_service.py
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from uuid import UUID


def analizar_incidentes(db: Session, empresa_id: UUID) -> dict:
    """
    Analiza patrones de incidentes usando Pandas/NumPy.
    Solo lectura. Filtra por empresa_id.
    """
    # 1. Query — obtener datos de la BD
    # 2. Convertir a DataFrame con pandas
    # 3. Calcular distribuciones con numpy
    # 4. Retornar dict estructurado
    pass


def analizar_riesgos(db: Session, empresa_id: UUID) -> dict:
    """
    Analiza distribución de peligros por nivel de riesgo.
    Calcula % con medidas de control activas.
    """
    pass


def analizar_capacitaciones(db: Session, empresa_id: UUID) -> dict:
    """
    Calcula tasa de aprobación global y asistencia promedio.
    Genera alertas para empleados con asistencia < 80%.
    """
    pass


def calcular_cumplimiento(db: Session, empresa_id: UUID) -> dict:
    """
    Score general SG-SST (0-100) basado en:
    - % incidentes investigados
    - % peligros con medidas de control
    - % capacitaciones realizadas
    - % no conformidades cerradas
    """
    pass
```

### Patrón de uso de Pandas dentro de cada función

```python
# Ejemplo real dentro de analizar_incidentes:

# 1. Obtener registros de la BD
registros = db.query(Incidente).filter(
    Incidente.empresa_id == empresa_id
).all()

# 2. Convertir a DataFrame
if not registros:
    return {"total_incidentes": 0, "por_tipo": {}, "por_severidad": {}}

df = pd.DataFrame([{
    "tipo": r.tipo.value,
    "severidad": r.severidad.value,
    "fecha": r.fecha,
} for r in registros])

# 3. Calcular distribuciones con NumPy/Pandas
por_tipo = df["tipo"].value_counts().to_dict()
por_severidad = df["severidad"].value_counts().to_dict()
tasa_mensual = round(len(df) / max(df["fecha"].dt.month.nunique(), 1), 1)
```

---

## 8. Notebooks de prototipado

Los notebooks se crean **antes** del código de producción. Su propósito es:

1. Explorar los datos reales de la BD
2. Validar la lógica de negocio antes de llevarla al servicio
3. Generar visualizaciones para la sustentación académica

### `notebooks/01_exploracion_incidentes.ipynb`

**Contenido:**
- Conexión a Neon PostgreSQL con `DATABASE_URL` del `.env`
- Carga de incidentes como DataFrame
- `.shape`, `.info()`, `.describe()` — auditoría estructural
- Distribución por tipo y severidad (gráficos)
- Identificación de patrones temporales
- Validación de la lógica que irá al servicio

### `notebooks/02_exploracion_riesgos.ipynb`

**Contenido:**
- Carga de peligros y evaluaciones de riesgo
- Distribución de niveles (bajo/medio/alto/crítico) — gráfico de torta
- % de peligros con medidas de control implementadas
- Análisis de efectividad: riesgo antes vs. después de medidas

### `notebooks/03_exploracion_capacitaciones.ipynb`

**Contenido:**
- Carga de capacitaciones, asistencias y evaluaciones
- Tasa de aprobación por capacitación
- Distribución de asistencia con NumPy
- Identificación de empleados en riesgo (asistencia < 80%)
- Alerta automática con lógica `np.where`

### Estructura de cada notebook

```
1. Configuración e imports
2. Conexión a la BD
3. Carga de datos (Ingesta)
4. Inspección estructural (.shape, .info, .dtypes)
5. Análisis descriptivo (.describe)
6. Transformaciones y cálculos
7. Exportación de hallazgos (CSV/Excel en data/processed/)
8. Conclusiones para el servicio
```

---

## 9. Tests

### Archivo: `tests/test_analytics_service.py`

**Casos a cubrir:**

| Test | Qué verifica |
|------|-------------|
| `test_analytics_incidentes_sin_datos` | Devuelve ceros sin explotar cuando no hay incidentes |
| `test_analytics_incidentes_con_datos` | Calcula distribuciones correctas |
| `test_analytics_multitenant` | Empresa A no ve datos de empresa B |
| `test_analytics_riesgos_distribucion` | Los niveles suman el total de peligros |
| `test_analytics_capacitaciones_aprobacion` | Tasa de aprobación es correcta |
| `test_analytics_alerta_asistencia` | Detecta empleados < 80% |
| `test_analytics_cumplimiento_vacio` | Score 0 cuando no hay datos |
| `test_analytics_cumplimiento_completo` | Score 100 cuando todo está en orden |

**Patrón:** igual que todos los otros tests del proyecto — usa SQLite en memoria, fixtures `db` y `empresa`.

---

## 10. Orden de implementación

| Paso | Qué | Tiempo estimado |
|------|-----|----------------|
| **1** | Instalar `pandas` y `numpy`, actualizar `requirements.txt` | 5 min |
| **2** | Crear carpeta `notebooks/` y los 3 notebooks de exploración | 1–2 h |
| **3** | Implementar `analytics_service.py` con las 4 funciones | 2–3 h |
| **4** | Implementar `analytics_router.py` con los 4 endpoints | 30 min |
| **5** | Registrar router en `main.py` | 5 min |
| **6** | Escribir `test_analytics_service.py` | 1 h |
| **7** | Actualizar `DOCUMENTACION_TECNICA.md` | 15 min |

**Total estimado: 5–7 horas**

---

## 11. Qué NO vamos a hacer

| ❌ No se hace | Por qué |
|---------------|---------|
| Segundo repositorio o despliegue | Innecesario para el alcance académico |
| ETL o réplica de BD | Los datos ya están en Neon |
| API Gateway o reverse proxy | Agrega complejidad sin beneficio en este contexto |
| Escritura en tablas transaccionales | El módulo es estrictamente de lectura |
| Cambios a servicios o routers existentes | El módulo es completamente aislado |
| Feature flags de infraestructura | Overkill para este alcance |

---

## 12. Resultado final esperado

Al terminar la implementación el proyecto tendrá:

- **4 endpoints nuevos** `/analytics/*` documentados en Swagger (`/docs`)
- **`analytics_service.py`** que demuestra uso real de Pandas y NumPy sobre datos de producción
- **3 notebooks** de análisis exploratorio listos para la sustentación
- **Tests** cubriendo los casos principales del servicio analítico
- **Todo dentro del proyecto** sin romper nada existente

### Verificación rápida (Swagger)

```
GET /analytics/incidentes     → distribución y patrones
GET /analytics/riesgos        → niveles y controles
GET /analytics/capacitaciones → aprobación y asistencia
GET /analytics/cumplimiento   → score SG-SST 0-100
```

---

## Referencias

- Especificación técnica: `docs/analítica_datos_especificación.md`
- Documentación del proyecto: `DOCUMENTACION_TECNICA.md`
- Servicios existentes como referencia de patrón: `app/services/metricas_service.py`
- Dependencias del router: `app/core/deps.py` — `require_role`, `get_current_user`

---

*Guía preparada el 2026-06-04*
*Proyecto PISST — SENA*
