# Guía de instalación (Ubuntu)

Ejecutar los siguientes comandos en orden.
### 1. Crear entorno virtual
`python -m venv .venv`
### 2. Activar entorno virtual
`source .venv/bin/activate`
### 3. Instalar dependencias necesarias
`pip install -r requirements.txt`
### 4. Clonar el repositorio
`git clone https://github.com/IngSoft1-Peligro-Sin-Codificar/Backend.git`
### 5. Ir al repositorio clonado
`cd Backend`
### 6. Levantar el server
`uvicorn app.main:app --reload`



### Para Correr tests
Para correr tests, es necesario instalar pytest (`pip install pytest`) y luego ejecutar `python -m pytest tests/nombre_del_test.py` dentro de la carpeta raiz.

Para correr todos los test juntos hay que ejecutar `python -m pytest`

Para correr todos los tests y obtener el coverage, además de pytest se debe instalar coverage (`pip install coverage`) y luego ejecutar:
`pytest --cov=app tests/`

