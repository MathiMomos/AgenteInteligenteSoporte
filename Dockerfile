
FROM python:3.12-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /code

# Copia solo el archivo de requisitos primero para aprovechar el cache de Docker
COPY ./requirements.txt /code/requirements.txt

# Instala las dependencias de Python
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copia el resto del código de tu aplicación
COPY . /code/

# Comando para ejecutar la aplicación.
# Nota: Usamos el puerto 80 para que coincida con el Ingress que ya configuramos.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]