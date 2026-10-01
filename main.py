"""API Gateway de Code4All.

Es la única puerta del backend: la aplicación solo conoce esta dirección, y el
gateway entrega cada ruta al microservicio que la atiende. Cada servicio vive
en su propio repositorio y llega aquí como submódulo de git en services/.

Hoy todos corren dentro de este mismo proceso, y es a propósito. En el plan
gratuito de Render cada servicio aparte se duerme por su cuenta y tarda un
minuto en despertar, y las 750 horas gratis del mes son para todo el
workspace, no para cada servicio. Un solo proceso despierta una vez y gasta
las horas de uno. El README explica cómo sacar un servicio a su propio
despliegue cuando haga falta.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
SERVICES_DIR = ROOT / "services"

# Las variables antes que nada: los servicios leen DATABASE_URL y SECRET_KEY
# en cuanto se importan.
load_dotenv(ROOT / ".env")

# Cada submódulo es la raíz de un repositorio, con su paquete dentro. Se
# añaden al final del camino para que nada de un servicio tape este main.py.
for repo in sorted(SERVICES_DIR.glob("*-backend-service")):
    if str(repo) not in sys.path:
        sys.path.append(str(repo))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from neon_storage import prepare_database
import accessibility_service.routes as accessibility
import assessment_service.routes as assessment
import course_content_service.routes as course_content
import device_management_service.routes as device_management
import multimodal_service.routes as multimodal
import progress_tracking_service.routes as progress_tracking
import user_management_service.routes as user_management

# Un servicio por recuadro del diagrama de arquitectura. neon-storage no está
# en la lista porque no tiene rutas: es la base que usan los demás.
SERVICES = (
    user_management,     # Gestión de usuarios: sesión, registro, foto
    course_content,      # Curso y contenidos: temario editable, módulos
    assessment,          # Ejercicios y evaluación: respuestas y resumen
    progress_tracking,   # Progreso y seguimiento: panel del director
    accessibility,       # Accesibilidad: Braille, subtítulos de YouTube
    multimodal,          # Interacción multimodal: señas con la cámara
    device_management,   # Infraestructura: estado del sistema
)

prepare_database()

app = FastAPI(title="Code4All API Gateway", version="2.0.0")

# Desde qué páginas puede un navegador llamar a este API: la web publicada en
# Render y, para desarrollar, localhost en cualquier puerto. CORS_ORIGINS
# (separados por comas) añade otros sin tocar el código, por ejemplo un
# dominio propio. Antes era "*" con credenciales, que el navegador traduce en
# «cualquier página puede llamar en nombre del usuario».
#
# Sin credenciales: la sesión viaja en la cabecera Authorization, no en
# cookies, así que no hacen falta.
CORS_ORIGINS = ["https://code4all-web.onrender.com"] + [
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

for service in SERVICES:
    service.register(app)


@app.get("/")
def read_root():
    return {"status": "online", "message": "¡Servidor conectado con éxito! 🚀"}
