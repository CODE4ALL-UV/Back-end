"""Un recorrido de punta a punta, como lo haría la aplicación.

Cruza varios servicios a propósito: la sesión la abre user-management y la
comprueban course-content y assessment. Si los servicios no compartieran la
clave o la base, esto es lo primero que fallaría.
"""

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from main import app
from user_management_service.presentation.api.upload_routes import UPLOAD_DIR

client = TestClient(app)


def _register_and_login(rol: str) -> dict:
    email = f"{rol}-{uuid.uuid4().hex[:8]}@example.com"

    registered = client.post(
        "/api/auth/register",
        json={
            "nombre": rol.title(),
            "correo": email,
            "password": "clave-segura",
            "rol": rol,
            "codigo_invitacion": os.environ.get(f"{rol.upper()}_SIGNUP_CODE"),
        },
    )
    assert registered.status_code == 201, registered.text

    login = client.post("/api/auth/login", json={"email": email, "password": "clave-segura"})
    assert login.status_code == 200, login.text

    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_the_root_still_answers_like_the_monolith():
    assert client.get("/").json()["status"] == "online"


def test_a_session_opened_in_users_works_in_the_other_services():
    teacher = _register_and_login("docente")
    student = _register_and_login("estudiante")

    # course-content acepta el token del docente: crea su curso y lo edita.
    course = client.post("/api/courses", json={"title": "Python 2026-1"}, headers=teacher)
    assert course.status_code == 201, course.text
    course_id = course.json()["id"]

    edited = client.put(
        f"/api/courses/{course_id}/overrides/section/m3-s1",
        json={"content": {"title": "Listas"}},
        headers=teacher,
    )
    assert edited.status_code == 200

    # El estudiante entra con el código y ve lo que editó su docente.
    joined = client.post(
        "/api/courses/join", json={"code": course.json()["join_code"]}, headers=student
    )
    assert joined.status_code == 200
    seen = client.get(f"/api/courses/{course_id}/overrides", headers=student).json()
    assert seen["items"][0]["content"] == {"title": "Listas"}

    # assessment acepta el del estudiante y le atribuye sus respuestas.
    answered = client.post(
        "/api/analytics/attempts",
        json={
            "course_id": course_id,
            "section_id": "m3-s1",
            "activity": "quiz",
            "answers": [{"question_index": 0, "correct": True}],
        },
        headers=student,
    )
    assert answered.status_code == 201

    students = client.get(
        f"/api/analytics/students?course_id={course_id}", headers=teacher
    ).json()["students"]
    assert [s["answered"] for s in students] == [1]


def test_two_teachers_teach_the_same_section_their_own_way():
    ana = _register_and_login("docente")
    luis = _register_and_login("docente")
    student = _register_and_login("estudiante")

    courses = {}
    for name, teacher in (("ana", ana), ("luis", luis)):
        created = client.post("/api/courses", json={"title": f"Curso de {name}"}, headers=teacher)
        courses[name] = created.json()
        client.put(
            f"/api/courses/{courses[name]['id']}/overrides/section/m1-s1",
            json={"content": {"title": f"Variables, según {name}"}},
            headers=teacher,
        )
        client.post(
            "/api/courses/join", json={"code": courses[name]["join_code"]}, headers=student
        )

    # El estudiante está en los dos y en cada uno ve la versión de su docente.
    mine = client.get("/api/courses/mine", headers=student).json()["courses"]
    assert {c["id"] for c in mine} >= {courses["ana"]["id"], courses["luis"]["id"]}
    for name in ("ana", "luis"):
        items = client.get(
            f"/api/courses/{courses[name]['id']}/overrides", headers=student
        ).json()["items"]
        assert [i["content"]["title"] for i in items] == [f"Variables, según {name}"]


def test_services_without_a_session_still_answer():
    braille = client.post("/api/braille/translate", json={"cells": [[1, 2, 5], [1]]})
    assert braille.json()["text"] == "ha"

    assert client.get("/api/signs/status").status_code == 200
    assert client.get("/api/system/health").json() == {"status": "ok"}


def test_photos_uploaded_before_the_split_are_still_served():
    # Las fotos ya guardadas apuntan a /uploads/<archivo>: tienen que seguir
    # saliendo desde la misma dirección.
    existing = next((p for p in UPLOAD_DIR.iterdir() if p.is_file()), None)
    if existing is None:
        pytest.skip("No hay fotos guardadas en uploads/ para comprobar.")

    response = client.get(f"/uploads/{existing.name}")
    assert response.status_code == 200
