# Simulacro de Sustentación Técnica — PISST Backend
## Profesor exigente | Nivel universitario/técnico

**Instrucciones de uso:**
- Lee la pregunta en voz alta como si el profesor te la hiciera
- Intenta responder sin leer la respuesta ideal
- Compara tu respuesta con la ideal
- Identifica el error que NO debes cometer

---

## BLOQUE 1 — Arquitectura en Capas (P1–P5)

---

### P1. "Explícame qué es una arquitectura en capas y por qué la eligieron para este proyecto"

**Respuesta ideal corta (30–45 segundos):**
> "Una arquitectura en capas divide el sistema en niveles con responsabilidades únicas: routers manejan HTTP, services tienen la lógica de negocio, models definen las tablas. No puede saltarse una capa. La elegimos porque separa responsabilidades y permite testear la lógica directamente sin levantar el servidor. Fue gracias a esta separación que descubrimos un bug de seguridad en `cambiar-password` al extraer el servicio de autenticación."

**Respuesta ideal técnica (1–2 minutos):**
> "La arquitectura en capas aplica el principio de responsabilidad única. Cada capa solo conoce a la inmediatamente inferior.
>
> Los **routers** en `app/routers/` son la capa HTTP: reciben la petición, validan con Pydantic, controlan autenticación con `Depends()` y serializan la respuesta con `response_model`. No tienen lógica de negocio.
>
> Los **services** en `app/services/` son la capa de negocio: toda regla de negocio, validación compleja e integración con servicios externos vive ahí. Nunca hacen `from fastapi import Request`.
>
> Los **models** en `app/models/` solo definen las tablas SQLAlchemy. No tienen métodos de negocio.
>
> El beneficio concreto: cuando extrajimos `auth_service.py` del router en el Sprint 5, inmediatamente quedó expuesto que el endpoint `/cambiar-password` no validaba el `session_token`. En un router monolítico ese bug habría sido invisible por meses. La separación hace el código auditable."

**Error que NO debes cometer:**
> ❌ Decir solo "separa el código en carpetas" sin explicar la regla de que no se puede saltarse capas ni que los routers no tienen lógica. Eso es una descripción de archivos, no de arquitectura.

---

### P2. "¿Qué hace exactamente `main.py` y cuáles son sus responsabilidades?"

**Respuesta ideal corta:**
> "Es el punto de entrada de la aplicación. Crea la instancia FastAPI, registra los 13 routers, configura CORS, rate limiting global, los dos handlers de errores (HTTP y genérico), valida variables de entorno obligatorias al arranque, y expone el health check que verifica la conexión real a la base de datos."

**Respuesta ideal técnica:**
> "En orden de ejecución:
>
> 1. **Validación de entorno al arranque**: verifica que `DATABASE_URL`, `SECRET_KEY`, `GEMINI_API_KEY` y `RESEND_API_KEY` existan. Si falta alguna, lanza `RuntimeError` antes de que el servidor levante. Esto evita arrancar en un estado inválido silencioso.
>
> 2. **Instancia FastAPI** con `docs_url=None` en producción. Swagger solo está disponible en `ENVIRONMENT=development`. En producción el endpoint `/docs` no existe.
>
> 3. **Rate limiting global** con SlowAPI. La función `_rate_limit_key` usa los últimos 30 chars del Bearer token si existe, o la IP. Esto evita que un atacante con muchas IPs evite el rate limit en endpoints autenticados.
>
> 4. **Dos exception handlers**: uno para `HTTPException` que garantiza formato uniforme `{detail, status_code}`, y uno genérico que captura cualquier excepción inesperada y responde 500 sin exponer el stack trace.
>
> 5. **CORS**: lista explícita de orígenes. En producción solo `app.pisst.online` y `pisst-frontend.vercel.app`. En development se agrega localhost.
>
> 6. **Registro de 13 routers**: auth, chat, incidente, capacitación, métricas, riesgo, auditoría, usuario, admin, área, cargo, analytics, notificación.
>
> 7. **Health check** en `GET /` que ejecuta `SELECT 1` real a la BD. Si la BD no responde, devuelve 503."

**Error que NO debes cometer:**
> ❌ Decir "main.py es donde se configura todo" sin poder nombrar al menos 4-5 responsabilidades específicas. Es el archivo que el profesor tiene más probabilidad de abrir en pantalla.

---

### P3. "¿Por qué los routers NO deben tener lógica de negocio? Dame un ejemplo concreto de qué pasaría si la tuvieran"

**Respuesta ideal corta:**
> "Si la lógica está en el router, no se puede testear sin levantar el servidor HTTP completo. El test tendría que hacer requests HTTP, manejar JWT y mockear todo el contexto FastAPI. Separando en services, el test llama directamente a la función con una sesión de BD. Fue exactamente ese diseño el que nos permitió detectar el bug de seguridad en `cambiar-password`."

**Respuesta ideal técnica:**
> "Ejemplo concreto: imagina que la validación de si se puede cerrar un incidente sin investigación estuviera en el router de incidentes. Para testear ese caso, necesitarías: crear un TestClient, hacer login para obtener JWT, crear un incidente, hacer PATCH del estado, y verificar el 400.
>
> En cambio, al estar en `incidente_service.update_estado_incidente()`, el test es:
> ```python
> def test_no_cerrar_sin_investigacion(db, empresa, usuario_sst):
>     inc = make_incidente(db, empresa, usuario_sst)
>     with pytest.raises(HTTPException) as exc:
>         incidente_service.update_estado_incidente(db, inc.id, empresa.id, 'cerrado')
>     assert exc.value.status_code == 400
> ```
> Sin HTTP, sin JWT, sin servidor. 5 milisegundos.
>
> El otro problema: lógica en routers tiende a duplicarse. Si dos routers necesitan la misma validación, la copian. Con services, se reutiliza."

**Error que NO debes cometer:**
> ❌ Responder solo "porque es mala práctica". Debes poder demostrar el impacto concreto en testabilidad.

---

### P4. "¿Qué es la inyección de dependencias en FastAPI y cómo la usan?"

**Respuesta ideal corta:**
> "FastAPI resuelve automáticamente las dependencias declaradas con `Depends()`. En cada endpoint declaramos `current_user: User = Depends(get_current_user)` y FastAPI llama a `get_current_user`, le inyecta la sesión de BD y el JWT, y pasa el resultado al endpoint. No hay estado global compartido. Si la dependencia falla, FastAPI responde el error sin ejecutar el endpoint."

**Respuesta ideal técnica:**
> "La inyección de dependencias de FastAPI funciona como un árbol de resolución. En `require_role('sst')`:
>
> ```python
> def require_role(*roles):
>     def role_checker(current_user: User = Depends(get_current_user)) -> User:
>         if current_user.role.value not in roles:
>             raise HTTPException(403, ...)
>         return current_user
>     return role_checker
> ```
>
> FastAPI resuelve: primero `get_db` (abre sesión BD), luego lo inyecta en `get_current_user` junto con el Bearer token extraído por `HTTPBearer`, y si todo pasa, llama a `role_checker`. Si en cualquier punto se lanza `HTTPException`, FastAPI responde inmediatamente sin llegar al cuerpo del endpoint.
>
> Es el patrón **Factory Method**: `require_role('sst', 'gerencia')` retorna una función de dependencia diferente según los roles. La función principal recibe distintos guardias sin cambiar su firma.
>
> En tests, sobreescribimos las dependencias con `app.dependency_overrides[get_db] = lambda: test_db_session`. Así los tests de endpoint usan SQLite sin cambiar el código de producción."

**Error que NO debes cometer:**
> ❌ Confundir `Depends()` con un decorator. No es `@depends(get_current_user)`, es un parámetro de la función. Si el profesor pregunta "¿por qué no usaron decorators?", la respuesta es que los decorators no tienen acceso al contexto de la petición en tiempo de ejecución.

---

### P5. "¿Qué es un DTO y cuál es la diferencia entre `IncidenteCreate` e `IncidenteResponse`?"

**Respuesta ideal corta:**
> "DTO es Data Transfer Object. Define el contrato de qué entra y qué sale de cada endpoint. `IncidenteCreate` tiene los campos que el frontend envía para crear un incidente — sin IDs, sin fechas internas. `IncidenteResponse` tiene los campos que el backend devuelve — incluye el UUID, fechas y estado, pero nunca `password_hash`. Pydantic garantiza esa separación automáticamente."

**Respuesta ideal técnica:**
> "La distinción es intencional y de seguridad.
>
> `IncidenteCreate` es entrada: campos que el usuario controla. Tiene validaciones estrictas: `tipo` es un Enum (si el frontend envía un tipo inválido, Pydantic responde 422 antes de tocar la BD), `severidad` también es Enum, la fecha es obligatoria. No tiene `empresa_id` — ese viene del JWT, no del body.
>
> `IncidenteResponse` es salida: lo que el servidor decide exponer. Incluye `id`, `fecha_creacion`, `estado`, y nuevamente: nunca `password_hash` aunque el incidente esté relacionado con un usuario.
>
> El mecanismo de seguridad es `response_model` en el router:
> ```python
> @router.get('/', response_model=List[IncidenteResponse])
> def listar_incidentes(...):
> ```
> Pydantic serializa el objeto SQLAlchemy según `IncidenteResponse` y descarta todo campo que no esté definido ahí. Si por error el service retorna un objeto con `password_hash`, Pydantic lo omite automáticamente."

**Error que NO debes cometer:**
> ❌ Decir que Create y Response son lo mismo o que la diferencia es solo que Response tiene más campos. La diferencia es conceptual: entrada valida, salida protege.

---

## BLOQUE 2 — JWT, Autorización y Roles (P6–P10)

---

### P6. "¿Qué contiene exactamente un JWT en su payload y por qué esos campos específicos?"

**Respuesta ideal corta:**
> "Nuestro JWT contiene `sub` con el UUID del usuario, `role` con su rol, `sid` con el ID de sesión único, `exp` con la expiración y `iat` con la fecha de emisión. Cada campo tiene un propósito: `sub` identifica al usuario, `role` evita consultar BD en cada petición para verificar el rol, `sid` permite la sesión única, y `iat` permite auditar cuándo se emitió el token."

**Respuesta ideal técnica:**
> "El payload del JWT en PISST:
> ```json
> {
>   "sub": "uuid-del-usuario",
>   "role": "sst",
>   "sid": "session-id-de-16-chars-hex",
>   "exp": 1751400000,
>   "iat": 1751398200
> }
> ```
>
> **`sub` (subject)**: convención JWT. UUID del usuario. Con esto buscamos el usuario en BD.
>
> **`role`**: evita una query extra. Sin esto, por cada petición deberíamos consultar la BD para saber el rol. Con esto, `require_role('sst')` compara sin BD.
>
> **`sid` (session ID)**: la innovación de seguridad del proyecto. Es el valor de `session_token` en BD al momento del login. En cada petición comparamos `payload['sid']` con `user.session_token` en BD. Si el usuario hizo login desde otro dispositivo, `session_token` cambió y `sid` del token viejo ya no coincide → 401. Esto implementa sesión única sin lista negra de tokens.
>
> **`iat` (issued at)**: auditoría. Permite saber cuándo se emitió el token. Aunque en PISST no se usa para lógica, está disponible en los logs para análisis de seguridad.
>
> **Lo que NO incluimos**: `email`, `nombre`, `empresa_id`. El email podría cambiar. El nombre también. `empresa_id` lo leemos de la BD para garantizar que no se falsifique."

**Error que NO debes cometer:**
> ❌ Decir que el JWT está encriptado. El JWT está **firmado**, no encriptado. Cualquiera puede decodificar el payload con base64. Lo que no puede hacer es **modificarlo** sin invalidar la firma.

---

### P7. "¿Qué diferencia hay entre 401 y 403? Dame ejemplos reales de cuándo PISST devuelve cada uno"

**Respuesta ideal corta:**
> "401 significa no autenticado — el sistema no sabe quién eres o tu identidad no es válida. 403 significa no autorizado — el sistema sabe quién eres pero no tienes permiso. En PISST: token expirado → 401, rol incorrecto → 403, `debe_cambiar_password` → 403."

**Respuesta ideal técnica:**
> "En HTTP semánticamente:
> - **401 Unauthorized**: el servidor no puede identificarte. Requiere que te autentiques.
> - **403 Forbidden**: el servidor sabe quién eres pero decides que no puedes.
>
> Ejemplos concretos en PISST:
>
> | Situación | Código | Razón |
> |---|---|---|
> | Token expirado | 401 | No sé quién eres, tu identidad no es válida |
> | Token malformado / firma inválida | 401 | No puedo verificar tu identidad |
> | Usuario desactivado | 401 | Esa identidad no existe activamente |
> | Sesión revocada por nuevo login | 401 | Tu sesión ya no es válida |
> | Rol empleado intentando endpoint de SST | 403 | Sé que eres empleado, pero este endpoint es solo para SST |
> | `debe_cambiar_password=True` | 403 | Sé quién eres, pero tienes una restricción activa |
> | Sin header Authorization | 403 | HTTPBearer de FastAPI rechaza automáticamente |
>
> La distinción importa para el frontend: un 401 debe redirigir al login. Un 403 debe mostrar un mensaje de 'no tienes permiso' sin redirigir."

**Error que NO debes cometer:**
> ❌ Invertirlos. El error más común es decir "403 es token expirado". Un token expirado es 401 porque el sistema ya no puede autenticarte.

---

### P8. "¿Por qué `cambiar-password` no usa `get_current_user` y qué riesgo tuvo eso?"

**Respuesta ideal corta:**
> "El endpoint permite el cambio cuando `debe_cambiar_password=True`, pero `get_current_user` bloquea con 403 en ese estado. Entonces bypaseamos esa dependencia. El riesgo fue que al saltarnos `get_current_user`, también nos saltamos la validación de `session_token`. Un JWT revocado podía usarse para cambiar la contraseña. Lo corregimos validando manualmente el `session_id` en el servicio."

**Respuesta ideal técnica:**
> "El diseño original del flujo era:
>
> 1. Admin crea usuario → `debe_cambiar_password=True`
> 2. Usuario hace login → recibe JWT (funciona porque login no usa `get_current_user`)
> 3. Usuario intenta cualquier endpoint → 403 por `debe_cambiar_password`
> 4. Usuario va a `/cambiar-password` → necesita JWT válido pero que funcione con el flag activo
>
> Solución: `/cambiar-password` recibe el JWT directamente sin pasar por `get_current_user`.
>
> **El bug**: `get_current_user` también valida el `session_token`. Al bypasearlo, esa validación desapareció. Si el usuario hizo logout (que invalida `session_token`), su JWT anterior seguía siendo válido para cambiar la contraseña — un atacante con el JWT podía cambiarla aunque la sesión estuviera cerrada.
>
> **El fix** en `auth_service.cambiar_password()`:
> ```python
> def cambiar_password(user_id, session_id_del_jwt, nueva, actual, db):
>     user = db.query(User).filter(User.id == UUID(user_id)).first()
>     # Validación manual de sesión que antes se saltaba
>     if str(user.session_token) != session_id_del_jwt:
>         raise HTTPException(401, 'Sesión expirada')
>     # resto de la lógica...
> ```
>
> Lección: cuando haces bypass de una dependencia de seguridad, debes auditar qué estás saltando y compensarlo explícitamente."

**Error que NO debes cometer:**
> ❌ Decir que el bypass fue un error de diseño y que debería haberse hecho diferente. El bypass es correcto — era necesario para el flujo. El error fue no compensar la validación que se omitía. Esa distinción muestra comprensión profunda.

---

### P9. "¿Cómo funciona `require_role`? Muéstrame el código y explícalo"

**Respuesta ideal corta:**
> "`require_role` es una función que retorna una función de dependencia. Es el patrón Factory Method. Recibe los roles permitidos como parámetros, y retorna una función que llama a `get_current_user` y compara el rol del usuario con los permitidos. Si no coincide, lanza 403."

**Respuesta ideal técnica:**
> "```python
> def require_role(*roles: str):
>     def role_checker(current_user: User = Depends(get_current_user)) -> User:
>         if current_user.role.value not in roles:
>             raise HTTPException(
>                 status_code=403,
>                 detail=f'Acceso denegado. Roles permitidos: {roles}'
>             )
>         return current_user
>     return role_checker
> ```
>
> Se usa en el router así:
> ```python
> @router.get('/')
> def listar_incidentes(
>     current_user: User = Depends(require_role('sst', 'gerencia'))
> ):
> ```
>
> Lo que FastAPI hace internamente:
> 1. Ve que el endpoint depende de `require_role('sst', 'gerencia')`
> 2. Llama a esa función, que retorna `role_checker`
> 3. `role_checker` depende de `get_current_user`
> 4. FastAPI resuelve `get_current_user` primero
> 5. Si `get_current_user` pasa, llama a `role_checker`
> 6. `role_checker` verifica el rol
>
> El orden garantiza que siempre se verifica autenticación ANTES que autorización. No hay forma de llegar a la verificación de rol sin que el JWT sea válido."

**Error que NO debes cometer:**
> ❌ Llamarlo "middleware". Los middlewares aplican a TODAS las rutas. `require_role` es una dependencia que se aplica por endpoint. Un middleware no puede verificar el rol porque el rol depende de qué endpoint se está llamando.

---

### P10. "¿Qué es la sesión única y cómo funciona técnicamente?"

**Respuesta ideal corta:**
> "Cuando el usuario hace login, generamos un `session_token` y lo guardamos en BD y en el claim `sid` del JWT. En cada petición, comparamos `sid` del JWT con `session_token` en BD. Si el usuario hace login desde otro dispositivo, se genera un nuevo `session_token` en BD. El token del primer dispositivo ya tiene un `sid` diferente al de BD → 401. Sin lista negra de tokens."

**Respuesta ideal técnica:**
> "El problema que resuelve: los JWT son stateless — una vez emitidos, no se pueden invalidar directamente. Si el usuario hace logout o login desde otro dispositivo, el JWT viejo técnicamente sigue siendo válido hasta que expire (30 minutos).
>
> La solución convencional es una lista negra de tokens en Redis. Nuestra solución es más elegante:
>
> 1. En login: `session_token = secrets.token_hex(32)` → guardado en `users.session_token` en BD
> 2. En el JWT: `{'sub': user_id, 'sid': session_token, 'exp': ...}`
> 3. En cada petición `get_current_user`:
>    ```python
>    if session_id and str(user.session_token) != session_id:
>        raise HTTPException(401, 'Sesión expirada. Iniciaste sesión desde otro dispositivo.')
>    ```
>
> Si el usuario hace un segundo login: se genera un nuevo `session_token` en BD. El `sid` del primer JWT ya no coincide → 401 en el siguiente request. Solo hay una sesión activa por usuario en todo momento.
>
> Si el usuario hace logout: `session_token=None` en BD. Cualquier JWT existente tiene `sid != None` → 401.
>
> Limitación: dentro de los 30 minutos de expiración del token, si el usuario NO hace ningún request, el logout no invalida inmediatamente el token ya emitido — el token sigue siendo un string válido criptográficamente. Pero en el primer request después del logout, el `session_token` en BD ya es `None` y falla."

**Error que NO debes cometer:**
> ❌ Decir que el JWT se invalida instantáneamente al hacer logout. El JWT como string sigue siendo criptográficamente válido — lo que invalida es la sesión en BD. La distinción importa.

---

## BLOQUE 3 — Seguridad en Endpoints (P11–P15)

---

### P11. "¿Cómo probaron que el rate limiting funciona en producción y cuál fue el bug que tenía?"

**Respuesta ideal corta:**
> "El bug era que `ENVIRONMENT=development` en Render desactivaba el rate limiting. El endpoint de login tenía 1000 peticiones/minuto efectivamente. Lo detectamos escribiendo tests que hacen 6 peticiones seguidas al login y verifican que la 6a devuelve 429. El fix fue hardcodear `@limiter.limit('5/minute')` sin condicional de entorno."

**Respuesta ideal técnica:**
> "El código original leía el límite desde variable de entorno:
> ```python
> # ANTES — vulnerable
> LOGIN_RATE_LIMIT = os.getenv('LOGIN_RATE_LIMIT', '1000/minute')
> @limiter.limit(LOGIN_RATE_LIMIT)
> ```
>
> El problema: en Render teníamos `ENVIRONMENT=development` (para no exponer Swagger), pero eso activaba el default de `LOGIN_RATE_LIMIT=1000/minute`. El endpoint de login en producción aceptaba 1000 peticiones por minuto — efectivamente sin protección contra fuerza bruta.
>
> El fix:
> ```python
> # DESPUÉS — correcto
> @limiter.limit('5/minute')  # siempre, sin condición de entorno
> ```
>
> Para los tests, el problema es que SlowAPI usa un singleton en memoria compartido entre todos los tests. Sin resetear el storage, los tests que llaman a `/auth/login` acumulan peticiones y el cupo de 5/min se agota entre tests, causando fallos en CI (429 inesperados).
>
> Solución: fixture `autouse=True` en `conftest.py`:
> ```python
> @pytest.fixture(autouse=True)
> def resetear_rate_limiter():
>     from app.routers.auth_router import limiter as auth_limiter
>     try:
>         auth_limiter._storage.reset()
>     except Exception:
>         pass
>     yield
> ```"

**Error que NO debes cometer:**
> ❌ Presentar esto como un fallo del equipo sin explicar cómo se detectó y corrigió. Al contrario: detectar un bug de seguridad real en producción y corregirlo con tests es exactamente lo que diferencia un proyecto técnico maduro.

---

### P12. "¿Cómo funciona el multi-tenancy y por qué es imposible que empresa A vea datos de empresa B?"

**Respuesta ideal corta:**
> "El `empresa_id` viene del JWT del usuario autenticado, no del request. Todos los servicios filtran por ese valor. Un atacante que modifique el `empresa_id` en el JWT invalida la firma criptográfica — `decode_token` lanza `JWTError`. No hay forma de inyectar un `empresa_id` diferente sin la `SECRET_KEY`."

**Respuesta ideal técnica:**
> "El flujo completo de aislamiento:
>
> 1. Login → servidor incluye `empresa_id` del usuario en BD dentro del JWT firmado
> 2. Cada request → `get_current_user` extrae `user_id` del JWT, consulta BD, obtiene el `User` con su `empresa_id` real
> 3. El router pasa `current_user.empresa_id` al service
> 4. El service filtra: `db.query(Incidente).filter(Incidente.empresa_id == empresa_id)`
>
> **La seguridad está en el paso 2**: el `empresa_id` que se usa para filtrar viene de la BD (del objeto `User` real), no del JWT. Aunque alguien pudiera manipular el payload del JWT (que no puede sin `SECRET_KEY`), el `empresa_id` que se usa es el que está en BD.
>
> **Prueba de multi-tenancy**:
> ```python
> def test_empresa_a_no_ve_empresa_b(db):
>     empresa_a = crear_empresa(db, nombre='A')
>     empresa_b = crear_empresa(db, nombre='B')
>     incidente_b = crear_incidente(db, empresa_b)
>
>     result = incidente_service.get_all_incidentes(db, empresa_a.id)
>     assert incidente_b not in result  # empresa A no ve incidente de B
> ```"

**Error que NO debes cometer:**
> ❌ Decir que "el `empresa_id` está en el JWT y eso lo protege". Lo que protege es que el `empresa_id` que filtra viene de la BD, no del JWT directamente. El JWT solo identifica al usuario; la empresa viene del usuario en BD.

---

### P13. "Si un atacante obtiene el token JWT de un usuario, ¿qué puede y no puede hacer?"

**Respuesta ideal corta:**
> "Puede hacer todo lo que ese usuario puede hacer, mientras el token no expire (30 minutos) o el usuario no haga login desde otro dispositivo (lo que invalida la sesión). No puede usar el token después de 30 minutos, no puede cambiar su rol en el token, y no puede acceder a datos de otras empresas."

**Respuesta ideal técnica:**
> "Análisis de riesgos con el token comprometido:
>
> **Lo que SÍ puede hacer (ventana de 30 minutos):**
> - Hacer cualquier petición con el rol del usuario robado
> - Acceder a todos los datos de la empresa del usuario
> - Crear incidentes, leer capacitaciones, descargar FURATes
>
> **Lo que NO puede hacer:**
> - Modificar el rol en el JWT (la firma lo impide)
> - Acceder a datos de otras empresas (multi-tenancy)
> - Usar el token después de 30 minutos (expiración)
> - Usar el token si el usuario original hace login (nueva sesión invalida el `session_token` en BD)
> - Cambiar la contraseña sin conocer la contraseña actual (el endpoint la valida)
>
> **Mitigación si se detecta el robo:**
> - El usuario hace login → nuevo `session_token` en BD → el token robado queda inválido en el siguiente request
> - El admin puede desactivar el usuario → `activo=False` → el token queda inválido inmediatamente
>
> **Por qué 30 minutos y no 24 horas**: ventana de compromiso reducida. Con refresh tokens, el usuario no nota diferencia — la sesión se renueva automáticamente. El atacante sin el refresh token solo tiene 30 minutos."

**Error que NO debes cometer:**
> ❌ Decir que el JWT robado es completamente inútil porque "está firmado". La firma protege la integridad del token, no su confidencialidad. Un token robado pero íntegro es completamente válido.

---

### P14. "¿Cómo validan la fortaleza de la contraseña y dónde se aplica?"

**Respuesta ideal corta:**
> "En `security.py` tenemos `validar_fortaleza_password` que usa regex. Requiere mínimo 8 caracteres, al menos una mayúscula, minúscula, número y símbolo de una lista predefinida. Se llama en todos los flujos de cambio de contraseña: al crear usuarios, en `cambiar-password` y en `reset-password`."

**Respuesta ideal técnica:**
> "El regex de validación:
> ```python
> def validar_fortaleza_password(password: str) -> None:
>     errores = []
>     if len(password) < 8:
>         errores.append('mínimo 8 caracteres')
>     if not re.search(r'[A-Z]', password):
>         errores.append('al menos una mayúscula')
>     if not re.search(r'[a-z]', password):
>         errores.append('al menos una minúscula')
>     if not re.search(r'\\d', password):
>         errores.append('al menos un número')
>     if not re.search(r'[!@#$%^&*(),.?\":{}|<>_\\-]', password):
>         errores.append('al menos un símbolo')
>     if errores:
>         raise HTTPException(400, f'Contraseña débil: {', '.join(errores)}')
> ```
>
> Puntos de aplicación:
> - `POST /admin/crear-sst` y `/crear-gerencia`: la contraseña temporal que se envía por correo no pasa por esta validación (es aleatoria y ya cumple los criterios)
> - `POST /auth/cambiar-password`: validación obligatoria de la nueva contraseña
> - `POST /auth/reset-password`: validación de la nueva contraseña
>
> El frontend conoce exactamente los símbolos válidos: `! @ # $ % ^ & * ( ) , . ? \" : { } | < > _ -`. Esto se documentó explícitamente para evitar que el frontend y el backend tengan regex distintos."

**Error que NO debes cometer:**
> ❌ Decir que la contraseña se valida "antes de guardarla". La validación es en el servicio, no a nivel de BD. La BD no tiene constraint de fortaleza. Es responsabilidad de la capa de servicio.

---

### P15. "¿Por qué en producción no hay `/docs`?"

**Respuesta ideal corta:**
> "Swagger UI expone toda la estructura de la API, los schemas, los parámetros y hasta permite probar endpoints. En producción eso es información valiosa para un atacante: les dice exactamente qué campos aceptar, qué errores buscar, y qué endpoints existen. En `main.py` solo activamos `docs_url='/docs'` cuando `ENVIRONMENT=development`."

**Respuesta ideal técnica:**
> "En `main.py`:
> ```python
> _dev = os.getenv('ENVIRONMENT') == 'development'
> app = FastAPI(
>     docs_url='/docs' if _dev else None,
>     redoc_url='/redoc' if _dev else None,
>     openapi_url='/openapi.json' if _dev else None,
> )
> ```
>
> Con `openapi_url=None`, ni siquiera el JSON de OpenAPI está disponible. Un atacante no puede hacer `curl https://api.pisst.online/openapi.json` para descubrir la estructura.
>
> **Riesgo sin esta protección**: Swagger permite probar endpoints directamente en el navegador. Un atacante puede usar la interfaz gráfica para probar ataques de fuerza bruta en el login (con autocompletado de campos), intentar inyecciones en campos de texto, y mapear todos los endpoints disponibles.
>
> **La desventaja**: el equipo de frontend no puede usar Swagger en producción. Lo compensamos con `DOCUMENTACION_TECNICA.md` que documenta todos los endpoints, y con el entorno de desarrollo local donde sí están disponibles."

**Error que NO debes cometer:**
> ❌ Decir que "es por seguridad pero no importa mucho". Importa. Security through obscurity no es una estrategia de seguridad, pero reducir la superficie de ataque sí lo es.

---

## BLOQUE 4 — SQLAlchemy, UUID y Modelado (P16–P19)

---

### P16. "¿Qué es el problema N+1 y cómo lo resolvieron?"

**Respuesta ideal corta:**
> "N+1 ocurre cuando por cada elemento de una lista se hace una query adicional para cargar datos relacionados. Si tenemos 50 incidentes y queremos mostrar el nombre de quien los reportó, sin `joinedload` haremos 51 queries. Con `joinedload`, SQLAlchemy hace un solo JOIN. Lo aplicamos en `get_all_incidentes` y en `get_incidente_by_id`."

**Respuesta ideal técnica:**
> "El problema concreto en PISST: `GET /incidentes/` devuelve la lista de incidentes con el nombre de quien los reportó (`creado_por_nombre`). Sin optimización:
>
> ```
> Query 1: SELECT * FROM incidentes WHERE empresa_id = X  → retorna 50 incidentes
> Query 2: SELECT * FROM users WHERE id = uuid_1         → para incidente 1
> Query 3: SELECT * FROM users WHERE id = uuid_2         → para incidente 2
> ... hasta Query 51
> ```
>
> Con `joinedload`:
> ```python
> db.query(Incidente)
>   .options(joinedload(Incidente.reportado_por))
>   .filter(Incidente.empresa_id == empresa_id)
>   .all()
> ```
>
> SQLAlchemy genera: `SELECT incidentes.*, users.* FROM incidentes LEFT JOIN users ON incidentes.reportado_por_id = users.id WHERE empresa_id = X`
>
> Una sola query. Esto es especialmente importante en endpoints de listado que pueden retornar hasta 500 registros (el límite de paginación).
>
> SQLAlchemy también ofrece `subqueryload` (subquery separada) y `selectinload` (IN query). `joinedload` es el más eficiente para relaciones muchos-a-uno como `Incidente → User`."

**Error que NO debes cometer:**
> ❌ Decir que es "un problema de la base de datos". N+1 es un problema del ORM — la BD recibe queries bien formadas. El problema es que el código las genera en bucle sin necesidad.

---

### P17. "¿Cómo funciona Alembic y por qué tienen 21 migraciones en cadena lineal?"

**Respuesta ideal corta:**
> "Alembic versiona los cambios al modelo de datos como archivos Python. Cada migración tiene un `upgrade()` y un `downgrade()`. La cadena lineal garantiza que siempre hay un solo camino para llegar al estado actual de la BD. En Render, `alembic upgrade head` aplica las migraciones pendientes en el orden correcto automáticamente al desplegar."

**Respuesta ideal técnica:**
> "Cada migración tiene:
> ```python
> revision = 'abc123'
> down_revision = 'xyz789'  # la anterior en la cadena
>
> def upgrade() -> None:
>     op.add_column('incidentes', sa.Column('trabajador_afectado_id', UUID(), ...))
>
> def downgrade() -> None:
>     op.drop_column('incidentes', 'trabajador_afectado_id')
> ```
>
> **Por qué cadena lineal**: si hubiera bifurcaciones (dos migraciones con el mismo `down_revision`), Alembic no sabería en qué orden aplicarlas. Las bifurcaciones ocurren cuando dos ramas de Git modifican modelos simultáneamente. En PISST lo evitamos con el flujo `barner-acosta → Dev → main`.
>
> **Migraciones idempotentes**: algunas migraciones usan `_column_exists()` para verificar antes de crear. Esto permite re-ejecutar `alembic upgrade head` en una BD que ya tiene la columna sin error:
> ```python
> def _column_exists(table, column, conn):
>     result = conn.execute(text(f'SELECT column_name FROM information_schema.columns WHERE table_name='{table}' AND column_name='{column}''))
>     return result.fetchone() is not None
> ```
>
> **Estado actual**: 21 migraciones, cadena lineal sin bifurcaciones, head en `d2e3f4a5b6c7`."

**Error que NO debes cometer:**
> ❌ Confundir Alembic con Django migrations. Son conceptualmente similares pero Alembic es independiente del ORM y más explícito. En Django las migrations son más "mágicas". En Alembic escribes SQL explícito.

---

### P18. "¿Por qué SQLite en tests si en producción es PostgreSQL?"

**Respuesta ideal corta:**
> "SQLite en memoria es instantáneo, no requiere conexión de red y cada test empieza limpio. La compatibilidad es suficiente para la lógica de negocio. Y paradójicamente, SQLite es más estricto que PostgreSQL en tipado — cuando SQLite falla y PostgreSQL no, encontramos bugs. Fue así como descubrimos el bug del UUID string."

**Respuesta ideal técnica:**
> "El caso concreto: en PostgreSQL, `db.query(User).filter(User.id == 'string-de-uuid')` funciona porque PostgreSQL convierte automáticamente strings a UUID. En SQLite eso falla con `AttributeError: 'str' object has no attribute 'hex'`.
>
> Cuando escribimos los tests con SQLite y la query tenía `user_id` como string, el test falló. La corrección fue:
> ```python
> # Antes (bug silencioso en prod, error en test):
> user = db.query(User).filter(User.id == user_id).first()
>
> # Después (correcto):
> user = db.query(User).filter(User.id == UUID(user_id)).first()
> ```
>
> Esto es semánticamente correcto — `user_id` del JWT es un string, el ID en BD es un UUID. La conversión explícita es lo correcto.
>
> **Los tests usan `dependency_overrides`**:
> ```python
> app.dependency_overrides[get_db] = lambda: test_session
> ```
> Reemplaza la función `get_db` que abre una conexión a Neon con una función que retorna la sesión SQLite. El código de producción no cambia."

**Error que NO debes cometer:**
> ❌ Decir que los tests con SQLite no son válidos porque "no es el mismo motor". La diferencia no está en las queries sino en la configuración. El 99% de la lógica de negocio que testeamos es agnóstica al motor de BD.

---

### P19. "¿Qué son las transacciones atómicas y cómo las usan en `audit_service`?"

**Respuesta ideal corta:**
> "`audit_service.registrar_auditoria()` agrega el log a la sesión pero NO llama a `commit()`. El commit lo hace el servicio que llama. Así el log de auditoría y la operación principal se persisten en la misma transacción — si la operación falla, el rollback borra también el log. Si el log estuviera en una transacción separada, podría quedar un log de una operación que nunca ocurrió."

**Respuesta ideal técnica:**
> "El patrón de Unit of Work:
>
> ```python
> # audit_service.py
> def registrar_auditoria(db, accion, entidad, entidad_id, detalle):
>     log = AuditLog(accion=accion, entidad=entidad, ...)
>     db.add(log)
>     # NO hay db.commit() aquí — intencional
>
> # incidente_service.py
> def update_estado_incidente(db, incidente_id, empresa_id, nuevo_estado):
>     incidente.estado = nuevo_estado
>     registrar_auditoria(db, 'cambiar_estado', ...)  # agrega log a la sesión
>     db.commit()  # persiste AMBOS: cambio de estado Y el log, en una sola transacción
> ```
>
> Si `db.commit()` falla por cualquier razón (constraint violation, conexión perdida, etc.), SQLAlchemy hace rollback automático de toda la sesión — incluyendo el log. Esto garantiza consistencia: nunca hay un log sin la operación que lo originó.
>
> En cambio, si `audit_service` hiciera su propio `commit()`, podría ocurrir:
> 1. `registrar_auditoria()` → `commit()` → log guardado
> 2. `update_estado_incidente()` → falla antes de su `commit()`
> 3. Resultado: hay un log que dice 'estado cambiado a cerrado' pero el incidente sigue abierto."

**Error que NO debes cometer:**
> ❌ Decir que no llamar a `commit()` en `audit_service` es un olvido o un bug. Es la decisión de diseño más sutil del proyecto y muestra comprensión profunda de transacciones.

---

## BLOQUE 5 — Tests, Cobertura y Regresiones (P20–P22)

---

### P20. "¿Qué significa 93% de cobertura? ¿Qué hay en el 7% que no está cubierto?"

**Respuesta ideal corta:**
> "93% significa que el 93% de las líneas de código se ejecutan en al menos un test. El 7% son principalmente ramas de error de servicios externos — cuando Cloudinary falla al subir la foto, cuando Gemini no responde, cuando el correo de Resend retorna error. Son difíciles de reproducir en tests porque requieren simular fallos de red complejos."

**Respuesta ideal técnica:**
> "La cobertura se mide con `pytest --cov=app`. Cuenta líneas ejecutadas / líneas totales.
>
> **Lo que cubre el 93%**: toda la lógica de negocio, todos los flujos de éxito, todos los flujos de error del dominio (404, 400, 401, 403), todos los endpoints HTTP.
>
> **El 7% restante** son casos como:
> - `except Exception` en handlers genéricos — requeriría forzar un error de BD en tiempo de test
> - Ramas del tipo `if cloudinary_error:` cuando el upload falla por razones de red
> - Código de compatibilidad hacia atrás que nunca se ejecuta en el flujo actual
>
> **Por qué 100% no es el objetivo**: el principio de rendimientos decrecientes. Pasar de 90% a 93% requiere ~40 tests y cubre lógica real. Pasar de 93% a 100% requeriría mockear fallos de red muy específicos para cubrir 3 líneas de código que quizás nunca fallen en producción.
>
> **Lo importante**: los módulos críticos de seguridad (`auth_service`, `deps.py`) están al 100%."

**Error que NO debes cometer:**
> ❌ Decir que 93% "está bien" sin poder explicar qué hay en el 7%. El profesor probablemente espera que sepas qué no está cubierto.

---

### P21. "¿Cómo evitaron que los tests fallen entre sí por el rate limiter de SlowAPI?"

**Respuesta ideal corta:**
> "SlowAPI usa un singleton en memoria compartido entre todos los tests de una sesión. Sin resetear, los tests de login acumulan peticiones y el cupo de 5/min se agota en el test de otra suite, causando 429 inesperados en CI. Lo resolvemos con un fixture `autouse=True` en `conftest.py` que llama a `lim._storage.reset()` antes de cada test."

**Respuesta ideal técnica:**
> "El problema se manifestó en CI cuando `test_perfil_notificaciones.py` fallaba con `HTTP 429` — no por hacer muchas peticiones, sino porque tests anteriores en la misma sesión habían consumido el cupo del singleton compartido.
>
> Solución implementada:
> ```python
> # tests/conftest.py
> @pytest.fixture(autouse=True)
> def resetear_rate_limiter():
>     from app.routers.auth_router import limiter as auth_limiter
>     from app.routers.chat_router import limiter as chat_limiter
>     for lim in (auth_limiter, chat_limiter):
>         try:
>             lim._storage.reset()
>         except Exception:
>             pass
>     yield
> ```
>
> `autouse=True` hace que este fixture se ejecute ANTES de cada test, sin que los tests lo declaren explícitamente.
>
> **Alternativa descartada**: desactivar el rate limiting en tests con `ENVIRONMENT=test`. Esto fue lo que causó el bug en producción — nunca más condicionamos seguridad al entorno.
>
> **Segunda alternativa**: los tests de auth ahora usan `_tokens_para(db, usuario)` que crea tokens directamente en BD sin pasar por `/auth/login`, evitando el rate limiter por diseño."

**Error que NO debes cometer:**
> ❌ Decir que la solución fue desactivar el rate limiting en tests. Eso fue exactamente el bug original. La solución es resetear el storage, no deshabilitar la protección.

---

### P22. "¿Cuál fue el test que falló en CI y por qué? Explícalo técnicamente"

**Respuesta ideal corta:**
> "El test `test_reporte_excel_contiene_kpis` buscaba la palabra 'KPI' en la columna 1 (A) del Excel. Cuando rediseñamos el reporte con una columna de margen a la izquierda, el contenido se movió a la columna 2 (B). El test buscaba en la columna correcta del diseño anterior, no del nuevo. Fix: cambiar `column=1` a `column=2`."

**Respuesta ideal técnica:**
> "El test original:
> ```python
> def test_reporte_excel_contiene_kpis(db, empresa, usuario_sst):
>     resultado = metricas_service.generar_reporte_excel(db, empresa.id, 'trimestral')
>     wb = openpyxl.load_workbook(resultado)
>     ws = wb['Reporte PISST']
>     valores = [ws.cell(row=r, column=1).value  # ← columna A
>                for r in range(1, ws.max_row + 1)]
>     assert any('KPI' in str(v) for v in valores if v)
> ```
>
> Después del rediseño, la paleta corporativa usa columna A como margen visual vacío y columna B para el contenido. El texto 'KPI' apareció ahora en `column=2`.
>
> Fix:
> ```python
> valores = [ws.cell(row=r, column=2).value  # ← columna B (contenido real)
>            for r in range(1, ws.max_row + 1)]
> ```
>
> **La lección**: los tests de generación de documentos (PDF/Excel) son tests de contrato, no solo de que el archivo se genera. Cuando el diseño cambia, los tests también deben actualizarse. El CI detectó inmediatamente que el test no pasaba — sin CI, este cambio podría haber pasado desapercibido hasta que alguien descargara un Excel vacío."

**Error que NO debes cometer:**
> ❌ Presentar esto como un error. Fue el sistema funcionando correctamente: el código cambió, el test detectó la incompatibilidad, se actualizó el test. El CI hizo su trabajo.

---

## BLOQUE 6 — Cinco Preguntas Trampa (P23–P27)

> ⚠️ Estas preguntas intentan hacerte contradecir o confundir. Léelas con cuidado.

---

### P23 [TRAMPA]. "¿Dijiste que los servicios no deben tener lógica HTTP, pero en `incidente_service` usan `HTTPException`. ¿No es eso una dependencia de FastAPI en la capa de negocio?"

**Por qué es trampa:** intenta hacerte contradecir la arquitectura en capas.

**Respuesta correcta:**
> "Es una inconsistencia aparente que tiene justificación pragmática. `HTTPException` de FastAPI es en realidad solo una subclase de Python `Exception` con campos `status_code` y `detail`. FastAPI la intercepta en los handlers, pero cualquier código puede lanzarla. La alternativa sería crear excepciones de dominio propias (`IncidenteNoEncontradoError`) y mapearlas a HTTP en los routers.
>
> En proyectos medianos como PISST, ese nivel de abstracción agregaría complejidad sin beneficio real — tendríamos el doble de clases de excepción. La decisión fue pragmática: `HTTPException` en services es un compromiso aceptado, documentado, y que no afecta la testabilidad (los tests de servicio capturan `HTTPException` directamente con `pytest.raises`)."

**Error que NO debes cometer:**
> ❌ Defender que `HTTPException` en services es perfectamente correcto sin reconocer que es un compromiso. El profesor sabe que no es puramente correcto. Reconocer la impureza y justificarla es la respuesta madura.

---

### P24 [TRAMPA]. "Dijeron que el JWT no está encriptado, entonces cualquiera puede leer el rol del usuario. ¿Eso no es un problema de seguridad?"

**Por qué es trampa:** mezcla confidencialidad con integridad.

**Respuesta correcta:**
> "Es correcto que el payload del JWT es legible — es base64, no cifrado. Cualquiera con el token puede decodificarlo y ver el rol. Eso NO es un problema de seguridad porque el rol en el JWT solo se usa para decisiones de acceso. Para modificar el rol en el JWT, el atacante necesita la `SECRET_KEY` para generar una firma válida. Sin la firma correcta, `decode_token` lanza `JWTError` y la petición falla.
>
> La distinción es: **confidencialidad** (nadie puede leerlo) vs **integridad** (nadie puede modificarlo). JWT garantiza integridad, no confidencialidad. Para datos confidenciales en el token, se usaría JWE (JSON Web Encryption). En PISST, no hay datos confidenciales en el payload — el UUID del usuario y su rol no son secretos."

**Error que NO debes cometer:**
> ❌ Decir que "no importa porque nadie lo haría" o que "el JWT está seguro". Debes distinguir confidencialidad de integridad con precisión.

---

### P25 [TRAMPA]. "¿No es redundante tener tanto `must_change_password` en la BD como verificarlo en cada petición? ¿Por qué no solo validarlo en el login?"

**Por qué es trampa:** suena razonable pero llevaría a un sistema inseguro.

**Respuesta correcta:**
> "Si solo lo validamos en el login, el flujo sería: el usuario hace login, recibe un JWT, y con ese JWT puede hacer cualquier petición antes de que cambie la contraseña. La validación en login solo impediría el login — pero el usuario ya tiene el token.
>
> Verificarlo en cada petición en `get_current_user` garantiza que incluso si el usuario tiene un JWT válido emitido antes de que el admin activara el flag, está bloqueado. El flag puede activarse después del login.
>
> Un caso concreto: el admin activa el flag de 'debe cambiar contraseña' en un usuario que ya tiene sesión activa. Si solo verificamos en login, ese usuario puede seguir usando la app indefinidamente hasta que el token expire. Verificando en cada request, el bloqueo es inmediato."

**Error que NO debes cometer:**
> ❌ Aceptar la premisa de que es redundante. No lo es — son dos verificaciones en dos momentos diferentes del ciclo de vida de la sesión.

---

### P26 [TRAMPA]. "Dijeron que tienen 93% de cobertura. Pero tener tests no significa que el código sea correcto. ¿Pueden demostrar que el código es correcto?"

**Por qué es trampa:** ataca la premisa de que cobertura = corrección.

**Respuesta correcta:**
> "Tiene razón en la distinción — cobertura y corrección son cosas diferentes. Cobertura dice que las líneas se ejecutan; no dice que el resultado es correcto. Demostramos corrección con lo que los tests verifican: no solo que el código se ejecuta, sino que devuelve los valores esperados.
>
> Ejemplos concretos: `test_kpis_con_accidentes` no solo ejecuta `get_kpis` — verifica que `tasa_accidentalidad > 0` con los datos que insertó. `test_no_cerrar_sin_investigacion` verifica que el status code es exactamente 400. `test_cambiar_password_session_invalida` verifica que es 401.
>
> Donde tenemos mayor confianza: módulos con 100% de cobertura Y casos de borde verificados — auth, incidente, riesgo. Donde tenemos menos confianza: las ramas del 7% no cubierto, que son principalmente manejo de fallos de servicios externos."

**Error que NO debes cometer:**
> ❌ Defender que "93% de cobertura significa que el código es correcto". El profesor tiene razón en su distinción. Acéptala y demuestra que tus tests verifican comportamiento, no solo ejecución.

---

### P27 [TRAMPA]. "¿Por qué en producción tienen `ENVIRONMENT=development`? ¿Eso no es contradictorio?"

**Por qué es trampa:** parece una contradicción grave pero tiene una razón válida.

**Respuesta correcta:**
> "Es una deuda técnica que reconocemos. La razón histórica: el backend en Render necesitaba que Swagger (`/docs`) no estuviera expuesto en producción, y la condición original era `ENVIRONMENT == 'production'` para desactivarlo. Al desplegar, pusieron `ENVIRONMENT=development` para asegurar que Swagger quedara desactivado... lo cual es lo inverso de la lógica.
>
> El efecto secundario fue el bug del rate limiting: código que condicionaba comportamiento a `ENVIRONMENT=production` quedaba desactivado.
>
> La solución correcta — que implementamos — es no condicionar comportamiento de seguridad al entorno. `docs_url=None` cuando no es development, rate limiting hardcodeado. Ahora `ENVIRONMENT=development` solo controla si Swagger aparece, no comportamientos de seguridad."

**Error que NO debes cometer:**
> ❌ Negar que es una contradicción o decir que "está bien así". Reconocer la deuda técnica y explicar cómo se mitigó es la respuesta honesta y técnicamente madura.

---

## Rúbrica de Evaluación

Para autoevaluarte después de cada respuesta, usa esta rúbrica de 4 dimensiones:

### Dimensión 1: Claridad Técnica (0–25 puntos)

| Puntos | Criterio |
|---|---|
| 20–25 | Explica con terminología correcta, sin ambigüedades, con ejemplos de código o rutas reales |
| 15–19 | Explicación correcta pero general, sin ejemplos concretos del proyecto |
| 10–14 | Explicación parcialmente correcta con alguna confusión terminológica |
| 0–9 | Respuesta vaga, incorrecta o no responde lo que se preguntó |

### Dimensión 2: Profundidad (0–25 puntos)

| Puntos | Criterio |
|---|---|
| 20–25 | Va más allá de la descripción superficial, explica el por qué de las decisiones y sus consecuencias |
| 15–19 | Describe correctamente pero no profundiza en motivaciones o trade-offs |
| 10–14 | Respuesta superficial, describe el qué pero no el por qué |
| 0–9 | No demuestra comprensión del impacto o contexto de la tecnología |

### Dimensión 3: Seguridad al Hablar (0–25 puntos)

| Puntos | Criterio |
|---|---|
| 20–25 | Habla con convicción, no duda antes de responder, corrige si se equivoca sin ponerse nervioso |
| 15–19 | Responde bien pero con algunas dudas o vacilaciones en los detalles |
| 10–14 | Se nota inseguridad, busca confirmación del interlocutor, respuestas terminan en pregunta |
| 0–9 | Respuestas evasivas, "creo que...", "no estoy seguro pero..." |

### Dimensión 4: Manejo de Objeciones (0–25 puntos)

| Puntos | Criterio |
|---|---|
| 20–25 | Escucha completo antes de responder, no se contradice, acepta puntos válidos del interlocutor |
| 15–19 | Responde bien a objeciones directas pero se desestabiliza con las trampas |
| 10–14 | Se defiende pero no demuestra que entiende por qué la objeción es razonable o no |
| 0–9 | Cede ante cualquier presión o se pone a la defensiva ante preguntas normales |

**Puntaje mínimo para aprobar**: 70/100
**Puntaje objetivo**: 85/100

---

## Top 10 Frases que Debes Memorizar

> Pronúncialas en voz alta hasta que salgan naturales.

1. **"La arquitectura en capas nos permitió descubrir un bug de seguridad que habría sido invisible en un router monolítico."**
   — Para cualquier pregunta sobre por qué separar capas.

2. **"El JWT está firmado, no encriptado. Garantiza integridad, no confidencialidad."**
   — Para cualquier pregunta sobre JWT y seguridad.

3. **"El `empresa_id` que filtra las queries viene de la BD, no del JWT directamente."**
   — Para cualquier pregunta sobre multi-tenancy.

4. **"En cada petición verificamos: firma válida, usuario activo, sesión vigente, rol permitido, y si debe cambiar contraseña."**
   — Para el flujo completo de autenticación.

5. **"`audit_service` no llama a `commit()` de forma intencional — el log y la operación se persisten en la misma transacción."**
   — Para cualquier pregunta sobre transacciones atómicas.

6. **"440 tests, 93% de cobertura, 0 CVEs, CI en verde en cada push."**
   — Cifras clave del estado del proyecto.

7. **"SQLite en tests es más estricto que PostgreSQL en tipado, lo que nos ayudó a encontrar el bug del UUID."**
   — Para preguntas sobre la estrategia de testing.

8. **"El rate limiting estaba desactivado en producción. Lo detectamos con tests y lo corregimos hardcodeando los límites."**
   — Bug real detectado y resuelto — muestra madurez técnica.

9. **"Si la dependencia de seguridad falla, FastAPI responde el error sin ejecutar el endpoint."**
   — Para preguntas sobre cómo funciona `Depends()`.

10. **"La cobertura del 93% incluye 100% en los módulos críticos de seguridad: auth, deps, incidente, furat."**
    — Para no dejar que la pregunta sobre el 7% parezca una debilidad.

---

## Top 10 Errores que Debes Evitar

1. **❌ Decir que el JWT está encriptado.**
   El JWT está firmado (HMAC-SHA256). Es legible. No es confidencial. Es íntegro.

2. **❌ Confundir 401 y 403.**
   401 = no sé quién eres (autenticación). 403 = sé quién eres pero no puedes (autorización).

3. **❌ Decir que la cobertura de 93% significa que el código es correcto.**
   Cobertura mide ejecución, no corrección. Los tests verifican comportamiento esperado.

4. **❌ Presentar el bug del rate limiting como un descuido sin importancia.**
   Es un bug de seguridad real en producción que dejaba el login sin protección. Fue importante.

5. **❌ Decir que `HTTPException` en los servicios es perfectamente correcto.**
   Es un compromiso pragmático aceptado, no el diseño ideal. Reconocerlo muestra madurez.

6. **❌ Decir que los tests con SQLite "no son válidos" porque no es PostgreSQL.**
   Son válidos para la lógica de negocio. La diferencia de motor fue incluso un beneficio.

7. **❌ Decir que "no llamar a `commit()` en `audit_service` fue un olvido".**
   Es la decisión más sutil del proyecto. Es intencional por transacciones atómicas.

8. **❌ Decir que `require_role` es un middleware.**
   Es una dependencia FastAPI. Un middleware aplica a todas las rutas. Una dependencia, solo a las que la declaran.

9. **❌ Negar las contradicciones evidentes (como `ENVIRONMENT=development` en producción).**
   Reconocer deuda técnica y explicar la mitigación es más profesional que negarla.

10. **❌ Usar "creo que..." o "no estoy seguro pero..." al responder.**
    Si no sabes algo, di: "No tengo ese dato memorizado ahora mismo, pero el comportamiento del sistema es [X] porque [razón técnica]." Eso es más profesional que dudar.

---

## Cierre de 1 Minuto — Termina con Fuerza

> Usa esto textualmente o adáptalo. Practicalo hasta que fluya natural.

---

*"Para cerrar, quiero contextualizar el alcance del trabajo:*

*PISST es un backend en producción que cumple con la normativa colombiana SG-SST — Decreto 1072 de 2015 y Resolución 0312 de 2019. No es un proyecto académico de prueba: tiene usuarios reales, genera FURATes oficiales y está desplegado en [https://app.pisst.online](https://app.pisst.online).*

*Técnicamente: 440 tests con 93% de cobertura, CI/CD activo, 0 CVEs en dependencias, rate limiting en producción, multi-tenancy con aislamiento real entre empresas, JWT con sesión única y validación en cada petición.*

*Durante el desarrollo cometimos errores reales — el rate limiting desactivado en producción, el `session_token` no validado en `cambiar-password`. Lo importante es que los tests y el CI los detectaron antes de que causaran daño, y los corregimos con evidencia.*

*El proyecto tiene deuda técnica reconocida — `ENVIRONMENT=development` en Render, el selector de trabajador afectado pendiente en el frontend, caché de métricas para escalabilidad futura. No pretendemos que está perfecto, pero sí que está sólido, probado y en producción.*

*Eso es PISST."*

---

*Simulacro preparado el 2026-07-01 — Proyecto PISST, SENA*
*Basado en el estado real del repositorio: rama `main`, 440 tests, CI verde*
