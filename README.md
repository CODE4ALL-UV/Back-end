# Back-end · API Gateway de Code4All

Es la única puerta del backend. La aplicación Flutter solo conoce esta
dirección, y el gateway entrega cada ruta al microservicio que la atiende.

Cada microservicio vive en su propio repositorio y llega aquí como **submódulo
de git** en `services/`. Hoy todos corren dentro del mismo proceso; más abajo
se explica por qué y cómo cambiarlo.

## Qué hay en cada repositorio 

| Recuadro del diagrama | Repositorio | Paquete | Rutas | Tablas que escribe |
|---|---|---|---|---|
| API Gateway | `Back-end` (este) | `main.py` | `/` | — |
| Gestión de usuarios | `user-management-backend-service` | `user_management_service` | `/api/auth/*`, `/api/user/upload-photo`, `/uploads/*` | `Usuario` |
| Curso y contenidos de Python | `course-content-backend-service` | `course_content_service` | `/api/course/*`, `/api/modules/*` | `CourseOverride` |
| Ejercicios y evaluación | `assessment-backend-service` | `assessment_service` | `/api/analytics/*` | `QuizAnswer`, `ActivityCompletion` |
| Progreso y seguimiento | `progress-tracking-backend-service` | `progress_tracking_service` | `/api/director/*`, `/api/oversight/*` | `student_performance`, `TeacherReview`, `ContentReview` |
| Accesibilidad y adaptación | `accessibility-backend-service` | `accessibility_service` | `/api/braille/*`, `/api/youtube/*` | — |
| Interacción multimodal | `multimodal-interaction-backend-service` | `multimodal_service` | `/api/signs/*` | — |
| Infraestructura y dispositivos | `device-management-backend-service` | `device_management_service` | `/api/system/*` | — |
| Base de datos / persistencia | `neon-storage-backend-service` | `neon_storage` | — | define todas |

Todos los servicios siguen el mismo contrato: su paquete tiene un
`routes.py` con `register(app)`, que es lo único que el gateway llama, y un
`main.py` para arrancarlo solo.

Las rutas son **exactamente las mismas** que tenía el monolito: la aplicación
no necesita ningún cambio. `tests/test_route_parity.py` lo comprueba.

## Por qué un solo despliegue y no ocho

El código está separado por servicio, pero en Render se despliega **un solo
servicio**: este gateway. En el plan gratuito, desplegarlos por separado sale
peor:

- Cada servicio se duerme a los 15 minutos sin uso y tarda cerca de un minuto
  en despertar. Con ocho, la app se toparía con un servicio dormido distinto
  en cada pantalla.
- Las 750 horas gratis del mes son para todo el workspace, no para cada
  servicio.
- Los servicios gratuitos no reciben tráfico de la red privada de Render, así
  que el gateway tendría que hablar con ellos por internet.
- Hay una sola base en Neon, y sus tablas están unidas a `Usuario` por claves
  foráneas: los servicios no son independientes en los datos.

Si algún día hace falta, un servicio se puede sacar a su propio despliegue sin
tocar su código (ver «Sacar un servicio aparte»).

## Correrlo en local

```powershell
git clone --recurse-submodules -b dev-saavedra https://github.com/CODE4ALL-UV/Back-end.git
cd Back-end
git submodule foreach "git checkout dev-saavedra"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload
```

El `.env` lleva la cadena de Neon y la misma `SECRET_KEY` que usa Render. La
documentación de todas las rutas queda en `http://127.0.0.1:8000/docs`.

`git submodule foreach "git checkout dev-saavedra"` deja cada servicio en su
rama, para poder hacer commits dentro de `services/<repo>` como en cualquier
repositorio.

## Pruebas

Ninguna prueba toca Neon: cada `conftest.py` fuerza una base SQLite temporal.

```powershell
pytest
```

`pytest.ini` ya le indica que corra las del gateway y las de cada servicio.

## Cambiar algo en un servicio

1. Se hace el cambio en `services/<repo>`, se hace commit y push a
   `dev-saavedra` de **ese** repositorio.
2. Desde la raíz de `Back-end`, se le dice al gateway que use esa versión:

   ```bash
   git submodule update --remote services/<repo>
   git add services/<repo>
   git commit -m "Chore: Actualizar <repo>"
   git push
   ```

El paso 2 no es opcional: el gateway despliega la versión del submódulo que
tiene apuntada, no la última de la rama. Es lo que garantiza que lo que se
despliega es exactamente lo que se probó.

## Desplegar en Render sin cortar el servicio actual

Hoy la app usa `code4all-api`, que sale del monolito de
`user-management-backend-service`. El gateway se despliega **al lado**, se
prueba, y solo entonces se cambia la app de uno a otro. Volver atrás es
deshacer un solo cambio.

1. **Dar acceso a Render a los repositorios.** En GitHub: organización
   CODE4ALL-UV → Settings → GitHub Apps → Render → Configure → añadir los
   ocho repositorios de servicios (o «All repositories»). Render clona los
   submódulos con ese acceso; sin él, el build falla al clonarlos.
2. **Crear el servicio.** En Render: New → Blueprint → repositorio
   `Back-end`, rama `dev-saavedra`. Lee `render.yaml` y crea
   `code4all-gateway`. Pide estos valores:
   - `DATABASE_URL`: la misma de `code4all-api`.
   - `SECRET_KEY`: **copiada de `code4all-api`** → Environment. Si es otra,
     todas las sesiones abiertas dejan de valer al cambiar de servidor.
   - `GOOGLE_CLIENT_ID` y `GOOGLE_SERVER_CLIENT_ID`: los de `code4all-api`.
     `GOOGLE_CLIENT_ID` es **obligatorio**: el servidor comprueba que cada
     inicio con Google sea de este Client ID, y sin él responde que Google
     no está configurado. Si la web y el móvil usan IDs distintos, van los
     dos separados por comas.
   - `FACEBOOK_APP_ID` y `FACEBOOK_APP_SECRET`: los de la app de Facebook
     (ver «Entrar con Facebook» más abajo). Opcionales.
   - `BREVO_API_KEY` y `MAIL_FROM`: para el correo de «¿Olvidaste tu
     contraseña?» (ver «Correo» más abajo). Opcionales.
3. **Comprobar que arrancó.**
   - `https://code4all-gateway.onrender.com/api/system/health` → `{"status": "ok"}`
   - `https://code4all-gateway.onrender.com/api/system/status` → `"database": {"ok": true, ...}`
   - `https://code4all-gateway.onrender.com/docs` → todas las rutas.
4. **Probar la app contra el gateway**, sin tocar la web publicada:

   ```bash
   flutter run -d chrome --dart-define=BACKEND_URL=https://code4all-gateway.onrender.com
   ```

   Iniciar sesión, editar una sección como docente, responder un quiz,
   el teclado Braille y la cámara de señas.
5. **Cambiar la app.** En Render → `code4all-web` → Environment →
   `BACKEND_URL` = la dirección del gateway → Save, rebuild and deploy.
6. **Si algo falla**, volver a poner en `BACKEND_URL` la dirección de
   `code4all-api`. Nada se borró: sigue funcionando igual que antes.
7. **Cuando lleve unos días estable**, suspender `code4all-api` y, después,
   quitar el monolito de `user-management-backend-service` (`app/`, `main.py`,
   `Dockerfile`, `render.yaml` y lo que sobre de `requirements.txt`). En ese
   orden: si se quita antes de suspenderlo, el siguiente despliegue de
   `code4all-api` falla.

La base de datos no cambia en ningún paso: el gateway usa las mismas tablas de
Neon, y al arrancar solo crea lo que falte, que es nada.

## Entrar con Facebook

1. En <https://developers.facebook.com/apps> → Crear app → «Autenticar y
   solicitar datos a los usuarios con el inicio de sesión con Facebook».
2. Inicio de sesión con Facebook → Configuración → **URI de redireccionamiento
   de OAuth válidos**: `https://code4all-web.onrender.com/` (con la barra
   final) y, para probar en local, `http://localhost:5000/`.
3. Configuración → Básica: copiar el identificador de la app y la clave
   secreta. El identificador va en `FACEBOOK_APP_ID` del gateway **y** de
   `code4all-web`; la clave secreta, solo en el gateway.
4. Para que entre cualquiera y no solo quien administra la app: poner la URL
   de la política de privacidad y pasar la app a modo **Activo**.

## Correo

El enlace de «¿Olvidaste tu contraseña?» sale por la API de Brevo: Render
gratis bloquea los puertos SMTP desde septiembre de 2025.

1. Cuenta gratuita en <https://www.brevo.com> (300 correos al día).
2. Senders, Domains & Dedicated IPs → Senders → añadir y verificar el correo
   que enviará los mensajes. No hace falta dominio propio.
3. SMTP & API → API Keys → crear una clave.
4. En el gateway: `BREVO_API_KEY` = la clave, `MAIL_FROM` = el correo
   verificado.

En local, sin Brevo y con `ALLOW_DEV_LOGIN=1`, el enlace se escribe en la
consola del servidor en vez de enviarse.

## Sacar un servicio aparte

Cuando el plan lo permita, un servicio puede ir en su propio despliegue con
`uvicorn <paquete>.main:app`. Los que no usan base ni sesión
(`accessibility`, `multimodal`) no dependen de nadie. El candidato natural es
`multimodal`: MediaPipe y OpenCV son, con diferencia, lo más pesado de la
imagen.

Antes de separar uno que use la base:

- Todos deben compartir `SECRET_KEY` (en Render, con un *Environment Group*).
- Conviene usar la cadena del **pooler** de Neon: cada servicio abre su propio
  grupo de conexiones, y la base gratuita admite unas 100 directas.
- El servicio necesita `neon-storage` y `user-management` en su imagen, igual
  que aquí: como submódulos de su propio repositorio.
