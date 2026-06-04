# Sustentación — Módulo de Ciencia de Datos en PISST
## Lo que hice, por qué lo hice y cómo explicarlo

**Documento personal — NO subir al repositorio**
**Fecha:** 2026-06-04

---

## Antes de empezar: el contexto

El proyecto PISST ya tenía un backend completo con FastAPI y PostgreSQL. El reto era agregar **ciencia de datos** sin romper lo que ya funcionaba y sin crear un sistema aparte. Se tomo la decisión de integrar el módulo de analítica **dentro del mismo proyecto** — esto se llama "Camino B" en la documentación interna.

¿Por qué no un servicio separado? Porque para el alcance académico era innecesario, agregaría complejidad sin beneficio, y habría duplicado la base de datos. La ciencia de datos no requiere un sistema nuevo — requiere procesar los datos que ya existen de manera inteligente.

---

## Qué es ciencia de datos y cómo la apliqué aquí

Ciencia de datos es el proceso de **extraer conocimiento útil de datos**. En PISST lo apliqué así:

| Paso de ciencia de datos | Cómo lo hice en PISST |
|--------------------------|----------------------|
| **Recolección de datos** | Los datos ya estaban en Neon PostgreSQL — los consulté con SQLAlchemy |
| **Exploración (EDA)** | Creé 3 notebooks de Jupyter para explorar incidentes, riesgos y capacitaciones |
| **Limpieza y transformación** | Usé Pandas para convertir los registros de la BD en DataFrames y limpiarlos |
| **Análisis y métricas** | Usé NumPy para calcular distribuciones, promedios y alertas |
| **Visualización** | Usé Matplotlib y Seaborn para generar gráficas de los resultados |
| **Producción** | Expuse los resultados como 4 endpoints de API con FastAPI |

---

## Las tecnologías que usé y por qué las elegí

### Pandas

Pandas es la librería estándar de Python para análisis de datos. La usé para:

- **Convertir consultas de BD en DataFrames** — estructura de tabla que permite operar fácilmente sobre columnas
- **`value_counts()`** — contar cuántos incidentes hay por tipo, por severidad, etc.
- **`groupby()`** — agrupar asistencias por empleado para calcular su porcentaje
- **`dt.to_period()`** — convertir fechas a períodos mensuales para la tendencia

**Ejemplo concreto:** para calcular cuántos incidentes hay por tipo, con SQL necesitaría un `GROUP BY`. Con Pandas es una línea:
```python
df["tipo"].value_counts().to_dict()
```

### NumPy

NumPy es la librería de cómputo numérico. La usé para:

- **`np.where()`** — convertir el estado de asistencia ("presente"/"ausente") a 1/0 para poder calcular porcentajes
- **`np.round()`** — redondear porcentajes a 1 decimal
- **`np.mean()`** — calcular el score promedio de cumplimiento SG-SST

**Ejemplo concreto:** para detectar qué empleados tienen menos del 80% de asistencia:
```python
df["presente"] = np.where(df["estado"] == "presente", 1, 0)
por_empleado = df.groupby("empleado_id")["presente"].mean() * 100
alertas = por_empleado[por_empleado < 80]
```

### Matplotlib y Seaborn

Son las librerías de visualización. Matplotlib es el motor base y Seaborn le agrega estilos más modernos.

- **Gráficas de barras** — para distribuciones por tipo y severidad
- **Gráficas de torta** — para proporciones (niveles de riesgo, asistencia)
- **Gráficas de línea con área sombreada** — para tendencia mensual de incidentes
- **Línea de umbral** — en la gráfica de asistencia por empleado, una línea punteada naranja marca el 80% mínimo requerido

### Jupyter Notebook

Es el entorno interactivo donde se ejecutan los notebooks. Lo usé para:
- Explorar los datos de Neon antes de escribir el código de producción
- Generar visualizaciones que demuestran el análisis con datos reales
- Documentar el razonamiento detrás de cada cálculo

---

## Los archivos que creé — explicados uno a uno

### `app/services/analytics_service.py`

Es el corazón del módulo. Tiene 4 funciones:

**`analizar_incidentes(db, empresa_id)`**
- Consulta la tabla `incidentes` filtrando por `empresa_id`
- Convierte a DataFrame con Pandas
- Calcula distribución por tipo y severidad con `value_counts()`
- Calcula la tasa mensual promedio: total de incidentes ÷ número de meses con actividad
- Calcula la tendencia comparando el último mes contra el anterior (si sube >20% = "aumento", si baja >20% = "baja", si no = "estable")

**`analizar_riesgos(db, empresa_id)`**
- Consulta `peligros` y sus `medidas_control`
- Para cada peligro, busca su evaluación de riesgo más reciente (no residual) para obtener el nivel (bajo/medio/alto/crítico)
- Calcula el % de peligros que tienen al menos una medida de control con estado "completada"
- Identifica peligros críticos sin ninguna medida — esto es la alerta más importante en SST

**`analizar_capacitaciones(db, empresa_id)`**
- Consulta `asistencias` solo de sesiones con estado "realizada" (las programadas no cuentan)
- Usa `np.where` para convertir presente/ausente a 1/0
- Calcula el % de asistencia por empleado con `groupby`
- Genera alertas para empleados con menos del 80% de asistencia
- También calcula la tasa de aprobación de evaluaciones

**`calcular_cumplimiento(db, empresa_id)`**
- Calcula 4 indicadores del SG-SST:
  1. % de incidentes investigados (estado != "borrador")
  2. % de peligros con medida de control implementada
  3. % de capacitaciones activas con al menos una sesión realizada
  4. % de no conformidades cerradas
- El score final es el promedio de los 4 (máximo 100 puntos)

### `app/routers/analytics_router.py`

Expone las 4 funciones como endpoints HTTP. Cada endpoint:
- Requiere un JWT válido con rol `sst` o `gerencia`
- Extrae el `empresa_id` del usuario autenticado (multi-tenancy automático)
- Llama al servicio y retorna el resultado como JSON

No hay lógica de negocio aquí — solo recibe la petición, valida el rol y delega al servicio.

### Los 3 notebooks

Son documentos interactivos que conectan a Neon y muestran el análisis con datos reales.

**`01_exploracion_incidentes.ipynb`**
- Carga incidentes con join a usuarios y áreas para saber el área del trabajador afectado
- Muestra la distribución por tipo, severidad y estado
- Genera 3 gráficas: barras por tipo, barras por severidad con colores de riesgo, línea de tendencia mensual

**`02_exploracion_riesgos.ipynb`**
- Carga peligros con sus evaluaciones de riesgo y medidas de control
- Muestra los niveles de riesgo y el estado de los controles
- Genera 3 gráficas: torta de niveles, barras por tipo de peligro, barras del estado de controles

**`03_exploracion_capacitaciones.ipynb`**
- Carga asistencias con el nombre de cada empleado
- Calcula el % de asistencia por empleado solo en sesiones realizadas
- Genera 3 gráficas: torta de asistencia general, barras por empleado con la línea del 80%, estado de sesiones

### `tests/test_analytics_service.py`

12 tests que verifican que el servicio funciona correctamente:
- Tests de casos vacíos: el servicio retorna ceros sin lanzar errores cuando no hay datos
- Tests con datos: las distribuciones se calculan correctamente
- Test de multi-tenancy: cada empresa solo ve sus propios datos
- Tests de alertas: los empleados con asistencia < 80% aparecen en la lista de alertas

---

## El concepto más importante: multi-tenancy

Cada empresa que usa PISST tiene sus propios datos. El sistema garantiza que una empresa **nunca** puede ver los datos de otra. Esto se implementa así:

```python
# TODA query en analytics_service.py filtra por empresa_id
incidentes = db.query(Incidente).filter(
    Incidente.empresa_id == empresa_id  # ← esta línea nunca se omite
).all()
```

El `empresa_id` viene del JWT del usuario autenticado — el usuario no puede cambiarlo.

---

## El concepto de "solo lectura"

El módulo de analytics **nunca escribe en la base de datos**. Solo consulta. Esto es importante porque:

1. No puede corromper datos de producción
2. Si el módulo falla, el resto del sistema sigue funcionando
3. Es más fácil de auditar — cualquier falla es de lectura, no de escritura

En código, esto significa que `analytics_service.py` **nunca usa**:
- `db.add(...)` — no crea registros
- `db.commit()` — no confirma transacciones
- `db.delete(...)` — no elimina datos

---

## Cómo explicar el flujo completo al profesor

Cuando el profesor pregunte "¿cómo funciona el módulo de ciencia de datos?", puedes responder así:

> *"El proceso tiene 4 pasos. Primero, cuando el frontend hace una petición a GET /analytics/incidentes, FastAPI valida el JWT y extrae el empresa_id del usuario. Segundo, el router llama a la función analizar_incidentes del servicio pasando la sesión de BD y el empresa_id. Tercero, el servicio consulta solo los incidentes de esa empresa usando SQLAlchemy, convierte los resultados en un DataFrame de Pandas, y aplica operaciones de NumPy para calcular las distribuciones y la tendencia mensual. Cuarto, retorna un diccionario que FastAPI serializa automáticamente como JSON."*

---

## Preguntas que el profesor puede hacer

**¿Por qué usaste Pandas si podrías hacer lo mismo en SQL?**

> Porque Pandas permite expresar transformaciones complejas más claramente en Python. Un `GROUP BY` con filtros condicionales en SQL se vuelve difícil de leer. Con Pandas, `value_counts()` y `groupby()` son una línea cada uno y el código es más mantenible.

**¿Qué es un DataFrame?**

> Es la estructura principal de Pandas. Funciona como una tabla — tiene filas y columnas. Cada columna es una Serie de valores del mismo tipo. Permiten aplicar operaciones vectorizadas sobre millones de filas en milisegundos.

**¿Para qué sirve NumPy si ya tienes Pandas?**

> NumPy opera a nivel de arrays numéricos, que es más rápido que las Series de Pandas para cálculos puros. Uso `np.where()` para conversiones condicionales (presente/ausente → 1/0), `np.round()` para redondeo, y `np.mean()` para el score de cumplimiento. Pandas internamente usa NumPy — son complementarios.

**¿Por qué los notebooks no se despliegan en Render?**

> Porque son herramientas de exploración y análisis, no parte del servicio. El análisis que validé en los notebooks está implementado en `analytics_service.py` que sí se despliega. Los notebooks conectan directamente a Neon desde mi máquina para exploración y sustentación.

**¿Cómo garantizas que una empresa no ve datos de otra?**

> Toda query en `analytics_service.py` filtra por `empresa_id` que viene del JWT del usuario autenticado. El usuario no puede modificar su propio `empresa_id` porque está firmado criptográficamente en el token. Los 12 tests incluyen un test específico de multi-tenancy que verifica esto.

**¿Qué pasa si no hay datos en la BD?**

> Cada función tiene un caso de retorno vacío explícito. Si no hay incidentes, retorna `{"total_incidentes": 0, "por_tipo": {}, ...}` sin lanzar ningún error. Esto es importante para que el frontend no se rompa cuando una empresa es nueva y todavía no tiene datos.

**¿Cuál es el score de cumplimiento SG-SST?**

> Es un indicador de 0 a 100 que mide qué tan bien está implementado el Sistema de Gestión de Seguridad y Salud en el Trabajo. Lo calculé con 4 componentes de igual peso (25 puntos cada uno): porcentaje de incidentes investigados, porcentaje de peligros con medida de control, porcentaje de capacitaciones realizadas, y porcentaje de no conformidades cerradas. El promedio de los 4 da el score final.

---

## Lo que debes mostrar en pantalla durante la sustentación

### Paso 1 — El endpoint en Swagger (2 minutos)

1. Abrir `http://localhost:8000/docs`
2. Ir a la sección **Analytics**
3. Hacer login primero: `POST /auth/login` con las credenciales SST
4. Copiar el `access_token`
5. Hacer clic en **Authorize** (arriba a la derecha) y pegar el token
6. Ejecutar `GET /analytics/cumplimiento`
7. Mostrar el score y el desglose de los 4 componentes

### Paso 2 — El notebook con gráficas (3 minutos)

1. Abrir terminal: `.\venv\Scripts\jupyter notebook notebooks\`
2. Abrir `03_exploracion_capacitaciones.ipynb`
3. Ir directo a la sección **5b. Visualizaciones**
4. Ejecutar esa celda (Shift+Enter)
5. Mostrar la gráfica de barras por empleado con la línea del 80%
6. Señalar los empleados en rojo (están bajo el umbral de alerta)

### Paso 3 — El código (2 minutos)

Abrir `app/services/analytics_service.py` y mostrar la función `analizar_capacitaciones`:
- Señalar el `db.query(...).filter(empresa_id == empresa_id)` — multi-tenancy
- Señalar el `np.where(estado == "presente", 1, 0)` — NumPy en acción
- Señalar el `groupby("empleado_id")["presente"].mean() * 100` — Pandas calculando el %

---

## Resumen de lo implementado

| Qué | Dónde | Tecnología |
|-----|-------|-----------|
| 4 endpoints analíticos | `app/routers/analytics_router.py` | FastAPI |
| Lógica de análisis | `app/services/analytics_service.py` | Pandas + NumPy |
| Exploración interactiva | `notebooks/*.ipynb` | Jupyter |
| Visualizaciones | Sección 5b de cada notebook | Matplotlib + Seaborn |
| Tests | `tests/test_analytics_service.py` | pytest (12 tests) |

**Total del proyecto:** 207 tests pasando — 91% de cobertura de código.

---

*Documento preparado el 2026-06-04*
*Proyecto PISST — SENA*
