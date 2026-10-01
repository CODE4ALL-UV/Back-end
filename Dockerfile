# Imagen del API Gateway de Code4All.
#
# Junta todos los microservicios en un solo proceso (ver main.py). Va en
# Docker y no en el entorno de Python que trae Render por dos motivos:
#
# 1. MediaPipe, que usa el servicio de interacción multimodal, necesita
#    librerías del sistema (libGL, libEGL, libglib) que el entorno nativo de
#    Render no tiene y no deja instalar.
# 2. Así la versión de Python es la misma aquí y en producción.
#
# Render clona los submódulos de services/ antes de construir la imagen.

FROM python:3.12-slim

# Librerías del sistema que piden MediaPipe y OpenCV.
#
# MediaPipe arrastra la pila de OpenGL aunque solo use la CPU. Sin libEGL
# falla al CREAR el detector, no al importarse: el servicio parece sano y se
# cae en cuanto alguien usa la cámara.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libegl1 \
    libgles2 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Primero solo los requirements: así un cambio en el código no obliga a
# reinstalar todas las dependencias en cada despliegue. Van uno por uno porque
# el requirements.txt del gateway los incluye por su ruta.
COPY requirements.txt .
COPY services/neon-storage-backend-service/requirements.txt services/neon-storage-backend-service/
COPY services/user-management-backend-service/requirements.txt services/user-management-backend-service/
COPY services/course-content-backend-service/requirements.txt services/course-content-backend-service/
COPY services/assessment-backend-service/requirements.txt services/assessment-backend-service/
COPY services/progress-tracking-backend-service/requirements.txt services/progress-tracking-backend-service/
COPY services/accessibility-backend-service/requirements.txt services/accessibility-backend-service/
COPY services/multimodal-interaction-backend-service/requirements.txt services/multimodal-interaction-backend-service/
COPY services/device-management-backend-service/requirements.txt services/device-management-backend-service/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

# Render manda el puerto en la variable PORT. Hay que escuchar en 0.0.0.0:
# en 127.0.0.1 el contenedor no recibiría nada de fuera.
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
