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