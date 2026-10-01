"""Lo que el gateway no deja hacer a quien no debe.

Cada prueba nace de un agujero que hubo: CORS abierto a cualquier página,
registrarse como director eligiéndolo en el formulario y entrar al login de
Google con un token inventado.
"""

import uuid

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

WEB = "https://code4all-web.onrender.com"


def _preflight(origin: str):
    return client.options(
        "/api/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )


def test_the_published_web_and_localhost_can_call_the_api():
    for origin in (WEB, "http://localhost:5173", "http://127.0.0.1:8080"):
        response = _preflight(origin)
        assert response.status_code == 200, origin
        assert response.headers.get("access-control-allow-origin") == origin


def test_any_other_page_cannot():
    response = _preflight("https://pagina-cualquiera.example")

    assert "access-control-allow-origin" not in response.headers


def test_nobody_registers_as_director_without_the_code():
    for code in (None, "", "codigo-de-prueba-docente", "adivinado"):
        response = client.post(
            "/api/auth/register",
            json={
                "nombre": "Intruso",
                "correo": f"intruso-{uuid.uuid4().hex[:8]}@example.com",
                "password": "clave-segura",
                "rol": "director",
                "codigo_invitacion": code,
            },
        )
        assert response.status_code == 403, code


def test_a_student_still_registers_without_a_code():
    response = client.post(
        "/api/auth/register",
        json={
            "nombre": "Ana",
            "correo": f"ana-{uuid.uuid4().hex[:8]}@example.com",
            "password": "clave-segura",
        },
    )

    assert response.status_code == 201
    assert response.json()["rol"] == "estudiante"


def test_dev_tokens_do_not_open_a_session(monkeypatch):
    monkeypatch.delenv("ALLOW_DEV_LOGIN", raising=False)

    response = client.post("/api/auth/google", json={"id_token": "dev:director@example.com"})

    assert response.status_code == 401
