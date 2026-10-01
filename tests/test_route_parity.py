"""El gateway expone exactamente lo que exponía el monolito.

La aplicación no sabe nada de microservicios: llama a las mismas rutas de
siempre. Si al repartir el código se pierde una, o cambia su método, la app se
rompe en silencio. Esta prueba lo impide.

MONOLITH_ROUTES es la tabla de rutas de user-management-backend-service en el
commit 838aa86, el último antes de separar los servicios.
"""

from main import app

MONOLITH_ROUTES = {
    "DELETE /api/analytics/attempts",
    "DELETE /api/course/overrides/{scope}/{target_id}",
    "GET /",
    "GET /api/analytics/students",
    "GET /api/analytics/summary",
    "GET /api/course/can-edit",
    "GET /api/course/overrides",
    "GET /api/course/overrides/{scope}/{target_id}",
    "GET /api/director/performances",
    "GET /api/director/performances/aggregate",
    "GET /api/director/performances/average",
    "GET /api/director/students",
    "GET /api/modules/{module_id}",
    "GET /api/oversight/content",
    "GET /api/oversight/reviews/{user_id}",
    "GET /api/oversight/teachers",
    "GET /api/oversight/teachers/{user_id}/activity",
    "GET /api/signs/status",
    "GET /api/youtube/captions",
    "PATCH /api/modules/{module_id}",
    "POST /api/analytics/attempts",
    "POST /api/analytics/completions",
    "POST /api/auth/google",
    "POST /api/auth/login",
    "POST /api/auth/register",
    "POST /api/braille/translate",
    "POST /api/director/performances",
    "POST /api/modules/",
    "POST /api/oversight/reviews",
    "POST /api/signs/landmarks",
    "POST /api/user/upload-photo",
    "PUT /api/course/overrides/{scope}/{target_id}",
    "PUT /api/oversight/content/{section_id}",
}

# Lo nuevo: el estado del sistema (device-management) y los cursos por
# docente (course-content y progress-tracking).
NEW_ROUTES = {
    "GET /api/system/health",
    "GET /api/system/status",
    "DELETE /api/courses/{course_id}",
    "DELETE /api/courses/{course_id}/enrollment",
    "DELETE /api/courses/{course_id}/overrides/{scope}/{target_id}",
    "GET /api/courses/mine",
    "GET /api/courses/{course_id}",
    "GET /api/courses/{course_id}/overrides",
    "GET /api/courses/{course_id}/overrides/{scope}/{target_id}",
    "GET /api/oversight/courses",
    "PATCH /api/courses/{course_id}",
    "POST /api/courses",
    "POST /api/courses/join",
    "POST /api/courses/{course_id}/join-code",
    "PUT /api/courses/{course_id}/overrides/{scope}/{target_id}",
}


def _gateway_routes() -> set[str]:
    paths = app.openapi()["paths"]
    return {f"{method.upper()} {path}" for path, ops in paths.items() for method in ops}


def test_no_route_of_the_monolith_was_lost():
    missing = MONOLITH_ROUTES - _gateway_routes()

    assert not missing, f"El gateway perdió estas rutas: {sorted(missing)}"


def test_nothing_unexpected_was_added():
    extra = _gateway_routes() - MONOLITH_ROUTES - NEW_ROUTES

    assert not extra, f"Rutas que no estaban en el monolito: {sorted(extra)}"
