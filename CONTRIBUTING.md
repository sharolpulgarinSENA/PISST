# Guía de contribución — PISST

## Migraciones de base de datos

### Convención de nombres

```bash
alembic revision --autogenerate -m "sprint_N_descripcion_corta"
```

Ejemplos:
```bash
alembic revision --autogenerate -m "sprint_4_agregar_indices_criticos"
alembic revision --autogenerate -m "sprint_5_tabla_notificaciones"
```

### Reglas

- Siempre usar `--autogenerate` para que Alembic detecte los cambios del modelo.
- El mensaje debe comenzar con `sprint_N_` donde N es el número de sprint actual.
- La descripción debe ser en minúsculas, sin espacios (usar guión bajo).
- **Revisar el archivo generado antes de aplicarlo** — Alembic puede detectar cambios falsos.
- Para columnas `NOT NULL` en tablas con datos existentes, agregar `server_default`:

```python
# Correcto — no falla con filas existentes
op.add_column('users', sa.Column('nuevo_campo', sa.Boolean(), nullable=False, server_default='false'))
```

### Aplicar y revertir

```bash
# Aplicar todas las migraciones pendientes
venv/Scripts/alembic upgrade head

# Revertir la última migración
venv/Scripts/alembic downgrade -1

# Ver estado actual
venv/Scripts/alembic current
```
