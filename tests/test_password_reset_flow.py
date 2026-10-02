"""Recuperar la contraseña de punta a punta, contra el gateway.

Se registra una cuenta, se pide el enlace, se cambia la contraseña y se
entra con la nueva. El correo no sale: se recoge lo que se habría enviado.
"""

import uuid
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from main import app
from user_management_service.application.use_cases import password_reset
from user_management_service.core import mailer

client = TestClient(app)


@pytest.fixture
def mailbox(monkeypatch):
    mails = []
    monkeypatch.setenv("BREVO_API_KEY", "clave-de-prueba")
    monkeypatch.setenv("MAIL_FROM", "code4all@example.com")
    monkeypatch.setenv("FRONTEND_URL", "https://code4all-web.onrender.com")
    monkeypatch.setattr(mailer, "send_mail", lambda **mail: mails.append(mail))
    password_reset._last_sent.clear()
    return mails


def _register() -> str:
    email = f"ana-{uuid.uuid4().hex[:8]}@example.com"
    response = client.post(
        "/api/auth/register",
        json={"nombre": "Ana", "correo": email, "password": "clave-vieja"},
    )
    assert response.status_code == 201
    return email


def _token(mail) -> str:
    link = mail["text"].split("abre este enlace:\n\n", 1)[1].split("\n", 1)[0]
    return parse_qs(urlparse(link).query)["restablecer"][0]


def _login(email, password):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_forgotten_password_can_be_changed_with_the_mailed_link(mailbox):
    email = _register()

    asked = client.post("/api/auth/password/forgot", json={"correo": email})
    assert asked.status_code == 200
    assert len(mailbox) == 1

    token = _token(mailbox[0])
    changed = client.post(
        "/api/auth/password/reset", json={"token": token, "password": "clave-nueva"}
    )
    assert changed.status_code == 200

    assert _login(email, "clave-nueva").status_code == 200
    assert _login(email, "clave-vieja").status_code == 401

    # El mismo enlace ya no sirve.
    again = client.post("/api/auth/password/reset", json={"token": token, "password": "otra-mas"})
    assert again.status_code == 400


def test_the_reply_does_not_tell_who_is_registered(mailbox):
    email = _register()

    known = client.post("/api/auth/password/forgot", json={"correo": email})
    unknown = client.post(
        "/api/auth/password/forgot", json={"correo": f"nadie-{uuid.uuid4().hex[:6]}@example.com"}
    )

    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert len(mailbox) == 1


def test_the_link_does_not_open_the_rest_of_the_api(mailbox):
    email = _register()
    client.post("/api/auth/password/forgot", json={"correo": email})
    token = _token(mailbox[0])

    response = client.get("/api/courses/mine", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_without_mail_the_server_says_so(monkeypatch):
    for name in ("BREVO_API_KEY", "MAIL_FROM", "ALLOW_DEV_LOGIN"):
        monkeypatch.delenv(name, raising=False)

    response = client.post("/api/auth/password/forgot", json={"correo": "ana@example.com"})

    assert response.status_code == 503
