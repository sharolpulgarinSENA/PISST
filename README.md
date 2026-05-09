comandos por primera vez

Antes de empezar, asegúrate de tener lo último de la rama de desarrollo.
- git checkout Dev
- git pull origin Dev

1. crear entorno virtual 
python -m venv venv

2. activar entorno
venv\Scripts\activate

3. instalar dependencias 
pip install -r requirements.txt

4. iniciar el servidor
uvicorn main:app --reload

-- inicio base de datos 
1. para iniciar el alembic que crea la carpeta de migration, se hace solo una unica vez, en este caso, ya se hizo y no se debe volver a hacer 
alembic init migrations

2. para generar las migraciones se usa el siguiente comando, solo se ejcuta una vez
alembic revision --autogenerate -m "modelos_iniciales_sprint1"

3. para migrar ahora si las tablas se ejecuta 
alembic upgrade head