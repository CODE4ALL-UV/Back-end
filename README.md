# Back-end · API Gateway de Code4All

Este repositorio es la **puerta de entrada del backend** de Code4All. La app
(Flutter) solo conoce una dirección, la de este gateway, y el gateway le
entrega cada petición al microservicio que la atiende: el login a gestión de
usuarios, las ediciones del curso a contenidos, las respuestas de los quices a
evaluación, y así con todo.

Cada microservicio vive en su propio repositorio y llega aquí como **submódulo
de git** en la carpeta `services/`. Hoy todos corren **dentro del mismo
proceso**: el gateway los importa y monta sus rutas en una sola aplicación de
FastAPI. Más abajo se explica por qué se hizo así y cómo cambiarlo.

## Qué hay en cada repositorio

| Recuadro del diagrama | Repositorio | Paquete | Rutas | Tablas que escribe |
|---|---|---|---|---|
| API Gateway | `Back-end` (este) | `main.py` | `/` | — |
| Gestión de usuarios | [user-management-backend-service](https://github.com/CODE4ALL-UV/user-management-backend-service) | `user_management_service` | `/api/auth/*`, `/api/user/upload-photo`, `/uploads/*` | `Usuario` |
| Curso y contenidos de Python | [course-content-backend-service](https://github.com/CODE4ALL-UV/course-content-backend-service) | `course_content_service` | `/api/courses/*`, `/api/course/*`, `/api/modules/*` | `Course`, `CourseEnrollment`, `CourseOverride` |
| Ejercicios y evaluación | [assessment-backend-service](https://github.com/CODE4ALL-UV/assessment-backend-service) | `assessment_service` | `/api/analytics/*` | `QuizAnswer`, `ActivityCompletion` |
| Progreso y seguimiento | [progress-tracking-backend-service](https://github.com/CODE4ALL-UV/progress-tracking-backend-service) | `progress_tracking_service` | `/api/director/*`, `/api/oversight/*` | `student_performance`, `TeacherReview`, `ContentReview` |
| Accesibilidad y adaptación | [accessibility-backend-service](https://github.com/CODE4ALL-UV/accessibility-backend-service) | `accessibility_service` | `/api/braille/*`, `/api/youtube/*` | — |
| Interacción multimodal | [multimodal-interaction-backend-service](https://github.com/CODE4ALL-UV/multimodal-interaction-backend-service) | `multimodal_service` | `/api/signs/*` | — |
| Infraestructura y dispositivos | [device-management-backend-service](https://github.com/CODE4ALL-UV/device-management-backend-service) | `device_management_service` | `/api/system/*` | — |
| Base de datos / persistencia | [neon-storage-backend-service](https://github.com/CODE4ALL-UV/neon-storage-backend-service) | `neon_storage` | — | define todas |

La app está en [Front-end](https://github.com/CODE4ALL-UV/Front-end).

Todos los servicios siguen el mismo contrato: su paquete tiene un `routes.py`
con una función `register(app)`, que es lo único que el gateway llama, y un
`main.py` para arrancarlo solo. Cada repositorio tiene su propio README con el
detalle de sus rutas, qué guarda y cómo probarlo.

## Qué rutas expone

Al montar todo quedan **52 rutas**:

- **Las 33 que tenía el monolito** (`code4all-api`), sin cambios. La app que
  hoy habla con el monolito puede hablar con el gateway sin tocar nada.
- **19 nuevas**, que solo existen en el gateway:
  - entrar con Facebook y recuperar la contraseña por correo
    (`/api/auth/facebook`, `/api/auth/password/forgot`, `/api/auth/password/reset`);
  - los cursos por docente (`/api/courses/*`, 13 rutas) y la vista de cursos
    de la coordinación (`/api/oversight/courses`);
  - el estado del sistema (`/api/system/health` y `/api/system/status`).

`tests/test_route_parity.py` lo comprueba: que no se haya perdido ninguna ruta
del monolito y que no aparezca ninguna que no esté en la lista de nuevas.

Con el servidor corriendo, la documentación interactiva de todas las rutas está
en `/docs`.

## Cómo funciona `main.py`

1. **Carga el `.env`** antes de importar nada, porque los servicios leen
   `DATABASE_URL` y `SECRET_KEY` en cuanto se importan.
2. **Añade cada `services/*-backend-service` al `sys.path`**, en orden
   alfabético y al final, para que nada de un servicio tape el `main.py` del
   gateway. Así se pueden importar `user_management_service`,
   `neon_storage`, etc., sin instalarlos con pip.
3. **Prepara la base de datos** con `prepare_database()` de neon-storage: crea
   las tablas que falten, aplica las migraciones y crea el Curso general. Si
   Neon no responde, avisa en el log y **arranca igual**.
4. **Configura CORS.** Solo pueden llamar al API desde el navegador la web
   publicada (`https://code4all-web.onrender.com`), `localhost` en cualquier
   puerto y lo que se ponga en `CORS_ORIGINS`. No se usan cookies
   (`allow_credentials=False`): la sesión viaja en la cabecera
   `Authorization`.
5. **Registra los servicios** en este orden: usuarios, contenidos, evaluación,
   progreso, accesibilidad, multimodal y dispositivos. neon-storage no se
   registra porque no tiene rutas.
6. Su única ruta propia es `GET /`, que responde `{"status": "online", ...}`.

No hay manejo de errores global: cada servicio responde sus propios errores,
con mensajes en castellano.

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

- El `.env` lleva la cadena de Neon y la misma `SECRET_KEY` que usa Render.
  Para probar sin tocar Neon se puede poner una base SQLite local, por ejemplo
  `DATABASE_URL=sqlite:///./local.db`.
- `requirements.txt` incluye el `requirements.txt` de cada servicio, así que
  un solo `pip install` deja todo listo.
- `git submodule foreach "git checkout dev-saavedra"` deja cada servicio en su
  rama, para poder hacer commits dentro de `services/<repo>` como en cualquier
  repositorio.
- Después de un `git pull` del gateway conviene correr
  `git submodule update --init --recursive`, para que cada servicio quede en
  la versión que el gateway tiene apuntada.
- Para probar el login de Google sin cuenta de Google, se puede añadir
  `ALLOW_DEV_LOGIN=1` al `.env` (solo en local).

La documentación de todas las rutas queda en `http://127.0.0.1:8000/docs`.

## Variables de entorno

| Variable | Para qué | ¿Obligatoria? |
|---|---|---|
| `DATABASE_URL` | La cadena de conexión de Neon. Sin ella el gateway no arranca. | Sí |
| `SECRET_KEY` | Firma y comprueba los tokens de sesión. Tiene que ser la misma de `code4all-api`. | Sí |
| `ALGORITHM` | Algoritmo del token. Por defecto `HS256`. | No |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duración de la sesión. Por defecto `1440` (24 h). | No |
| `GOOGLE_CLIENT_ID` | El Client ID de Google de Code4All (varios, separados por comas). | Para entrar con Google |
| `DOCENTE_SIGNUP_CODE`, `DIRECTOR_SIGNUP_CODE` | Los códigos para registrarse como docente o director. Sin ellos esos registros quedan cerrados. | No |
| `FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET` | La app de Facebook. | Para entrar con Facebook |
| `BREVO_API_KEY`, `MAIL_FROM` | El correo de «¿Olvidaste tu contraseña?». | Para recuperar la contraseña |
| `MAIL_FROM_NAME` | El nombre del remitente. Por defecto `Code4All`. | No |
| `FRONTEND_URL` | Adónde lleva el enlace del correo. Por defecto la web publicada. | No |
| `TRANSLATE_PROVIDER`, `TRANSLATE_API_KEY` | Traducir los subtítulos de YouTube (`google` o `deepl`). | No |
| `CORS_ORIGINS` | Otras páginas que pueden llamar al API desde el navegador, separadas por comas. | No |
| `ALLOW_DEV_LOGIN` | `1` para aceptar tokens `dev:correo` y escribir los correos en consola. **Nunca en Render.** | No |

`.env.example` trae las principales. `render.yaml` declara las que necesita
Render; `TRANSLATE_*` no está ahí y, si se quiere traducir los subtítulos, hay
que añadirlas a mano en el panel. Qué hace cada una en detalle está en el
README del servicio que la usa.

## Pruebas

Ninguna prueba toca Neon: cada `conftest.py` fuerza una base SQLite temporal.

```powershell
pytest
```

`pytest.ini` le indica que corra las del gateway (`tests/`) y las de cada
servicio (`services/*/tests`). Para correr solo las de un servicio:
`pytest services/<repo>/tests`.

Las pruebas propias del gateway recorren varios servicios a la vez:

| Archivo | Qué comprueba |
|---|---|
| `test_gateway_flow.py` | Una sesión abierta en usuarios vale en los demás servicios: el docente crea un curso y edita una sección, el estudiante entra con el código, ve la edición y responde, y el docente ve la respuesta. Dos docentes editan la misma sección sin pisarse. Braille, señas y el estado del sistema responden sin sesión. Las fotos subidas antes de la separación se siguen sirviendo. |
| `test_password_reset_flow.py` | Recuperar la contraseña de principio a fin; la respuesta no revela qué correos tienen cuenta; el enlace no sirve como sesión; sin correo configurado responde 503. |
| `test_route_parity.py` | Están todas las rutas del monolito y solo las nuevas que se esperan. |
| `test_security.py` | CORS solo para la web y localhost; nadie se registra como director sin el código; los tokens `dev:` no abren sesión sin `ALLOW_DEV_LOGIN`. |

En GitHub, cada push o pull request a `main` corre las pruebas del gateway con
cobertura y la sube a Codacy (`.github/workflows/codacy-coverage.yml`). Ese
workflow no usa los submódulos: clona los ocho servicios desde su rama
principal.

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

Si el cambio añade una ruta nueva, hay que agregarla también a `NEW_ROUTES` en
`tests/test_route_parity.py`.

## Desplegar en Render sin cortar el servicio actual

Hoy la app usa `code4all-api`, que sale del monolito de
`user-management-backend-service`. El gateway se despliega **al lado**, se
prueba, y solo entonces se cambia la app de uno a otro. Volver atrás es
deshacer un solo cambio.

El despliegue usa el `Dockerfile` de este repositorio: Python 3.12, las
librerías del sistema que necesita MediaPipe (`libgl1`, `libegl1`, `libgles2`,
`libglib2.0-0`) y `uvicorn main:app`. Render clona los submódulos antes de
construir.

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
     dos separados por comas. (`GOOGLE_SERVER_CLIENT_ID` está declarada, pero
     hoy el código del backend no la lee.)
   - `DOCENTE_SIGNUP_CODE` y `DIRECTOR_SIGNUP_CODE`: los mismos de
     `code4all-api`. Sin ellos nadie se puede registrar como docente ni como
     director.
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
   `Dockerfile`, `render.yaml`, la carpeta `neon_storage/` que reexporta
   `app/` y lo que sobre de `requirements.txt`). En ese orden: si se quita
   antes de suspenderlo, el siguiente despliegue de `code4all-api` falla.

La base de datos no cambia en ningún paso: el gateway usa las mismas tablas de
Neon, y al arrancar solo crea lo que falte. Lo único que añade la primera vez
son las tablas y columnas de los cursos por docente, y deja todo lo anterior en
el Curso general. Ese paso también cambia algunas restricciones únicas, pero
solo en PostgreSQL: las pruebas automáticas usan SQLite, donde ese cambio se
salta, así que conviene probarlo antes en una rama de Neon.

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
- El servicio necesita `neon-storage` en su imagen y, si comprueba la sesión,
  también `user-management`, igual que aquí: como submódulos de su propio
  repositorio. assessment necesita además `course-content`, de donde toma las
  reglas de acceso a cada curso.
