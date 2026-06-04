# Guía de Ciencia de Datos — PISST
## Módulo analítico con Pandas, NumPy y Matplotlib

**Versión:** 1.0 | **Fecha:** 2026-06-04 | **Estado:** Implementado y en producción

---

## Tabla de Contenidos

1. [Qué se implementó](#1-qué-se-implementó)
2. [Arquitectura del módulo](#2-arquitectura-del-módulo)
3. [Configuración del entorno desde cero](#3-configuración-del-entorno-desde-cero)
4. [Dependencias instaladas](#4-dependencias-instaladas)
5. [Archivos creados](#5-archivos-creados)
6. [Los 4 endpoints analíticos](#6-los-4-endpoints-analíticos)
7. [Cómo funciona analytics_service.py](#7-cómo-funciona-analytics_servicepy)
8. [Los 3 notebooks de exploración](#8-los-3-notebooks-de-exploración)
9. [Las gráficas generadas](#9-las-gráficas-generadas)
10. [Cómo correr los notebooks](#10-cómo-correr-los-notebooks)
11. [Tests del módulo](#11-tests-del-módulo)
12. [Qué ver en la sustentación](#12-qué-ver-en-la-sustentación)

---

## 1. Qué se implementó

Un módulo de **analítica integrada** dentro del proyecto PISST. Es completamente de solo lectura — toma los datos existentes en Neon PostgreSQL y los procesa con **Pandas** y **NumPy** para generar KPIs, distribuciones, alertas y un score general de cumplimiento SG-SST.

Además se crearon **3 notebooks de Jupyter** con **gráficas** usando **Matplotlib** y **Seaborn**, listos para mostrar en la sustentación académica.

### Lo que el módulo hace:

| Capacidad | Tecnología |
|-----------|-----------|
| Cargar datos de la BD | SQLAlchemy (ya existía en el proyecto) |
| Procesar y transformar datos | **Pandas** |
| Calcular métricas y alertas | **NumPy** |
| Exponer resultados como API | FastAPI (ya existía) |
| Visualizar con gráficas | **Matplotlib + Seaborn** |
| Exploración interactiva | **Jupyter Notebook** |

---

## 2. Arquitectura del módulo

```
Neon PostgreSQL (datos reales de producción)
         │
         │  SQLAlchemy — solo .query() — nunca escribe
         ▼
app/services/analytics_service.py
         │
         │  pandas.DataFrame  →  numpy  →  métricas
         ▼
   dict con resultados estructurados
         │
         │  FastAPI response (JSON)
         ▼
app/routers/analytics_router.py  →  Frontend / Swagger
```

**Principios:**
- **Solo lectura** — nunca hace `db.add()`, `db.commit()` ni `db.delete()`
- **Multi-tenant** — toda query filtra por `empresa_id` del usuario autenticado
- **No invasivo** — si falla analytics, el backend principal sigue funcionando
- **Seguro** — reutiliza el mismo JWT y RBAC del resto del proyecto

---

## 3. Configuración del entorno desde cero

Si un compañero quiere correr el proyecto en su máquina:

```bash
# 1. Clonar el repositorio
git clone https://github.com/sharolpulgarinSENA/PISST.git
cd PISST

# 2. Crear entorno virtual
python -m venv venv

# 3. Activar el entorno virtual
.\venv\Scripts\activate          # Windows
source venv/bin/activate         # Linux/Mac

# 4. Instalar todas las dependencias (incluye pandas, numpy, matplotlib, seaborn)
pip install -r requirements.txt

# 5. Instalar Jupyter (no está en requirements.txt — es solo para notebooks locales)
pip install jupyter

# 6. Copiar el archivo .env (pedírselo a Barner — no está en el repo)
# El archivo debe quedar en la raíz del proyecto: PISST/.env

# 7. Verificar que todo esté instalado
python -c "import pandas, numpy, matplotlib, seaborn; print('OK')"
```

---

## 4. Dependencias instaladas

Estas líneas se agregaron a `requirements.txt`:

```
matplotlib>=3.7.0
numpy>=1.24.0
pandas>=2.0.0
seaborn>=0.12.0
```

Versiones instaladas en producción:
- **pandas 3.0.3**
- **numpy 2.4.6**
- **matplotlib** (última compatible)
- **seaborn** (última compatible)

> Jupyter **no está en requirements.txt** porque es una herramienta de exploración local, no se instala en el servidor de producción (Render).

---

## 5. Archivos creados

### Archivos nuevos en el proyecto

```
PISST/
├── app/
│   ├── services/
│   │   └── analytics_service.py     ← lógica con Pandas/NumPy
│   └── routers/
│       └── analytics_router.py      ← 4 endpoints /analytics/*
├── notebooks/
│   ├── 01_exploracion_incidentes.ipynb
│   ├── 02_exploracion_riesgos.ipynb
│   └── 03_exploracion_capacitaciones.ipynb
├── data/
│   └── processed/                   ← CSVs y PNGs generados por los notebooks
└── tests/
    └── test_analytics_service.py    ← 12 tests del servicio
```

### Archivos modificados

| Archivo | Qué se cambió |
|---------|--------------|
| `main.py` | Se registró `analytics_router` |
| `requirements.txt` | Se agregaron pandas, numpy, matplotlib, seaborn |
| `DOCUMENTACION_TECNICA.md` | Se actualizó a v1.5 con el Sprint 10 |

---

## 6. Los 4 endpoints analíticos

Todos viven bajo `/analytics` y requieren autenticación JWT con rol `sst` o `gerencia`.

### GET /analytics/incidentes

Analiza los incidentes de la empresa.

**Respuesta:**
```json
{
  "total_incidentes": 6,
  "por_tipo": {
    "accidente": 3,
    "incidente": 2,
    "cuasi_accidente": 1
  },
  "por_severidad": {
    "leve": 3,
    "moderada": 2,
    "grave": 1
  },
  "tasa_mensual_promedio": 2.0,
  "top_areas": [],
  "tendencia": "estable"
}
```

### GET /analytics/riesgos

Analiza peligros y medidas de control.

**Respuesta:**
```json
{
  "total_peligros": 2,
  "por_nivel": {"alto": 2},
  "por_tipo": {"mecanico": 2},
  "pct_con_control_implementado": 50.0,
  "criticos_sin_control": 0
}
```

### GET /analytics/capacitaciones

Analiza asistencia y evaluaciones.

**Respuesta:**
```json
{
  "total_evaluaciones": 0,
  "tasa_aprobacion_pct": 0.0,
  "asistencia_promedio_pct": 50.0,
  "alertas_asistencia": [
    {"empleado_id": "uuid", "asistencia_pct": 0.0}
  ],
  "capacitaciones_sin_sesion_realizada": 2
}
```

### GET /analytics/cumplimiento

Calcula el score SG-SST de 0 a 100.

**Respuesta:**
```json
{
  "score_total": 25.0,
  "desglose": {
    "incidentes_investigados": 0.0,
    "peligros_con_control": 0.0,
    "capacitaciones_realizadas": 100.0,
    "no_conformidades_cerradas": 0.0
  }
}
```

**Cómo se calcula el score:** promedio simple de los 4 componentes (25 puntos cada uno).

---

## 7. Cómo funciona analytics_service.py

El servicio tiene 4 funciones. Todas siguen el mismo patrón:

```python
def analizar_incidentes(db: Session, empresa_id: UUID) -> dict:

    # 1. Query a la BD — solo lectura
    registros = db.query(Incidente).filter(
        Incidente.empresa_id == empresa_id  # ← multi-tenancy siempre
    ).all()

    # 2. Caso vacío — retorna ceros sin explotar
    if not registros:
        return {"total_incidentes": 0, ...}

    # 3. Convertir a DataFrame de Pandas
    df = pd.DataFrame([
        {"tipo": r.tipo.value, "severidad": r.severidad.value, "fecha": r.fecha}
        for r in registros
    ])

    # 4. Calcular con Pandas y NumPy
    por_tipo = df["tipo"].value_counts().to_dict()
    tasa_mensual = round(len(df) / max(df["fecha"].dt.to_period("M").nunique(), 1), 1)

    # 5. Retornar dict estructurado
    return {"total_incidentes": len(df), "por_tipo": por_tipo, ...}
```

**Por qué Pandas y no SQL directo:**
- Las distribuciones con `value_counts()` son más limpias que `GROUP BY` en SQL
- El cálculo de tendencias y alertas se expresa mejor en Python que en SQL
- El DataFrame permite agregar más análisis sin cambiar la query

---

## 8. Los 3 notebooks de exploración

Los notebooks están en `notebooks/` y se conectan a Neon directamente.

### Estructura de cada notebook

Todos siguen la misma estructura de 8 secciones:

| Sección | Qué hace |
|---------|---------|
| 1. Configuración e imports | Importa pandas, numpy, matplotlib, seaborn; carga el .env |
| 2. Conexión a la BD | Crea el engine con SQLAlchemy y verifica con un COUNT |
| 3. Carga de datos | Ejecuta el SQL y carga el resultado en un DataFrame |
| 4. Inspección estructural | `.shape`, `.info()`, valores nulos |
| 5. Análisis descriptivo | `value_counts()`, `.describe()` |
| 5b. Visualizaciones | **3 gráficas con Matplotlib y Seaborn** |
| 6. Transformaciones | Lógica exacta que va al servicio |
| 7. Exportación | Guarda CSV y PNG en `data/processed/` |
| 8. Conclusiones | Notas para el servicio |

### 01_exploracion_incidentes.ipynb

- Conecta a la tabla `incidentes` + join con `users` y `areas` para el área del trabajador
- **Gráfica 1:** Barras horizontales — distribución por tipo de incidente
- **Gráfica 2:** Barras verticales con color por severidad (rojo=mortal, verde=sin lesión)
- **Gráfica 3:** Línea de tendencia mensual con área sombreada

### 02_exploracion_riesgos.ipynb

- Conecta a `peligros`, `evaluaciones_riesgo` y `medidas_control`
- **Gráfica 1:** Torta — niveles de riesgo (rojo=crítico, naranja=alto, amarillo=medio, verde=bajo)
- **Gráfica 2:** Barras horizontales — tipos de peligro
- **Gráfica 3:** Barras con color — estado de medidas de control

### 03_exploracion_capacitaciones.ipynb

- Conecta a `asistencias`, `sesiones_capacitacion`, `capacitaciones`, `respuestas_empleado`
- **Gráfica 1:** Torta — distribución presente/ausente/justificado
- **Gráfica 2:** Barras horizontales por empleado con **línea de alerta al 80%** (rojo = bajo umbral, verde = OK)
- **Gráfica 3:** Barras — asistencias por estado de sesión

---

## 9. Las gráficas generadas

Cada vez que se ejecuta un notebook, las gráficas se guardan automáticamente en `data/processed/`:

| Archivo | Notebook que lo genera |
|---------|----------------------|
| `incidentes_graficas.png` | 01_exploracion_incidentes.ipynb |
| `riesgos_graficas.png` | 02_exploracion_riesgos.ipynb |
| `capacitaciones_graficas.png` | 03_exploracion_capacitaciones.ipynb |
| `incidentes_explorados.csv` | 01_exploracion_incidentes.ipynb |
| `riesgos_explorados.csv` | 02_exploracion_riesgos.ipynb |
| `controles_explorados.csv` | 02_exploracion_riesgos.ipynb |
| `asistencias_exploradas.csv` | 03_exploracion_capacitaciones.ipynb |

> Los archivos en `data/processed/` están en `.gitignore` — no se suben al repositorio porque son generados localmente con datos de producción.

---

## 10. Cómo correr los notebooks

### Abrir Jupyter

```bash
# Desde la raíz del proyecto con el venv activo
.\venv\Scripts\jupyter notebook notebooks\
```

Se abre el navegador en `http://localhost:8888/notebooks/`.

### Ejecutar un notebook

1. Haz clic en el nombre del notebook (`.ipynb`)
2. Menú **Run → Run All Cells**
3. Los resultados aparecen debajo de cada celda
4. Las gráficas se muestran en pantalla y se guardan en `data/processed/`

### Cuándo volver a ejecutar

Cada vez que quieras ver datos actualizados. Los notebooks **no guardan los datos** — cada ejecución consulta Neon en tiempo real. Si ayer había 6 incidentes y hoy hay 20, al ejecutar verás 20.

---

## 11. Tests del módulo

El archivo `tests/test_analytics_service.py` tiene **12 tests** que cubren:

| Test | Qué verifica |
|------|-------------|
| `test_analytics_incidentes_sin_datos` | Retorna ceros sin explotar cuando no hay incidentes |
| `test_analytics_incidentes_con_datos` | Distribuciones por tipo y severidad correctas |
| `test_analytics_multitenant_incidentes` | Empresa A no ve datos de empresa B |
| `test_analytics_riesgos_sin_datos` | Retorna ceros sin explotar |
| `test_analytics_riesgos_distribucion` | La suma de niveles equals total de peligros |
| `test_analytics_riesgos_pct_control` | % entre 0 y 100 |
| `test_analytics_capacitaciones_sin_datos` | Retorna ceros y lista vacía |
| `test_analytics_capacitaciones_aprobacion` | Tasa de aprobación calculada correctamente |
| `test_analytics_alerta_asistencia` | Detecta empleados con asistencia < 80% |
| `test_analytics_capacitaciones_sin_sesion_realizada` | Cuenta capacitaciones sin sesión realizada |
| `test_analytics_cumplimiento_vacio` | Score 0 con desglose de 4 componentes |
| `test_analytics_cumplimiento_con_datos_parciales` | Score parcial cuando hay datos |

**Correr los tests:**
```bash
.\venv\Scripts\python -m pytest tests/test_analytics_service.py -v
```

**Resultado esperado:** 12 passed

---

## 12. Qué ver en la sustentación

### Demostración sugerida (en vivo)

**1. Mostrar los endpoints en Swagger**
```
http://localhost:8000/docs
→ sección Analytics
→ ejecutar GET /analytics/cumplimiento con token válido
→ mostrar el score SG-SST y el desglose
```

**2. Abrir un notebook en vivo**
```
.\venv\Scripts\jupyter notebook notebooks\
→ abrir 03_exploracion_capacitaciones.ipynb
→ Run All Cells
→ mostrar la gráfica de asistencia por empleado con la línea del 80%
→ señalar los empleados en rojo (alerta)
```

**3. Argumento técnico ante el jurado**

> *"El módulo de analítica usa Pandas para transformar los datos de la BD en DataFrames, NumPy para calcular promedios y distribuciones, y Matplotlib para visualizarlos. Todo está integrado dentro del proyecto sin arquitectura adicional, siguiendo el principio de no-invasividad. Los 4 endpoints están protegidos con el mismo JWT y RBAC del resto del sistema, garantizando que cada empresa solo vea sus propios datos."*

### Puntos clave a mencionar

- **Pandas** — `value_counts()`, `groupby()`, `mean()`, `to_period()`
- **NumPy** — `np.where()` para convertir estados a 1/0, `np.round()`, `np.mean()`
- **Multi-tenancy** — toda query filtra por `empresa_id`
- **Solo lectura** — el módulo nunca escribe en la BD
- **Alertas automáticas** — el sistema detecta empleados con asistencia < 80% sin intervención manual

---

## Referencias

- Servicio: [app/services/analytics_service.py](../app/services/analytics_service.py)
- Router: [app/routers/analytics_router.py](../app/routers/analytics_router.py)
- Tests: [tests/test_analytics_service.py](../tests/test_analytics_service.py)
- Documentación técnica: [DOCUMENTACION_TECNICA.md](../DOCUMENTACION_TECNICA.md)
- Guía de implementación original: [docs/analytics_guia_implementacion.md](analytics_guia_implementacion.md)

---

*Guía preparada el 2026-06-04*
*Proyecto PISST — SENA*
