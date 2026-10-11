import smtplib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from customers import email_verification
from models import User, VerificationToken, Customer, Ticket
from settings import cors_origins, validate_hosted_settings


@pytest.fixture
def production(monkeypatch):
    for name, value in {
        "APP_ENV": "production",
        "FRONTEND_URL": "https://triage.example.com",
        "CORS_ORIGINS": "https://triage.example.com",
        "EMAIL_BACKEND": "resend",
        "EMAIL_FROM": "support@example.com",
        "RESEND_API_KEY": "test-email-key",
    }.items():
        monkeypatch.setenv(name, value)


def test_public_signup_cannot_create_employee_in_production(client, db_session, production):
    for role in ("admin", "agent", "viewer"):
        response = client.post("/auth/register", json={
            "username": "untrusted", "email": "untrusted@example.com",
            "password": "a-long-password", "role": role,
        })
        assert response.status_code == 403
    assert db_session.query(User).filter_by(username="untrusted").first() is None


def test_local_signup_cannot_self_assign_admin(client, db_session, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    response = client.post("/auth/register", json={
        "username": "untrusted", "email": "untrusted@example.com",
        "password": "a-long-password", "role": "admin",
    })
    assert response.status_code == 403
    assert db_session.query(User).filter_by(username="untrusted").first() is None


def test_hosted_email_link_verifies_customer(client, db_session, production, monkeypatch, capsys):
    sent = []

    def send(url, **kwargs):
        sent.append((url, kwargs))
        return httpx.Response(200, request=httpx.Request("POST", url), json={"id": "test"})

    monkeypatch.setattr(email_verification.httpx, "post", send)
    response = client.post("/customers/request-verification", json={"email": "customer@example.com"})
    assert response.status_code == 200
    token = db_session.query(VerificationToken).one()
    assert sent[0][0] == "https://api.resend.com/emails"
    payload = sent[0][1]["json"]
    assert payload["to"] == ["customer@example.com"]
    assert f"https://triage.example.com/customerComplaint?token={token.token}" in payload["text"]
    assert "localhost" not in payload["text"]
    assert token.token not in capsys.readouterr().out
    verified = client.get("/customers/verify-email", params={"token": token.token})
    assert verified.status_code == 200
    assert db_session.get(VerificationToken, token.id).used


def test_email_failure_is_not_reported_as_sent(client, db_session, production, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("provider detail containing private credentials")

    monkeypatch.setattr(email_verification.httpx, "post", fail)
    response = client.post("/customers/request-verification", json={"email": "customer@example.com"})
    assert response.status_code == 502
    assert "private credentials" not in response.text
    assert db_session.query(VerificationToken).count() == 0


@pytest.mark.parametrize("origin", ["http://localhost:5173", "*", "https://example.com/path"])
def test_production_rejects_invalid_website_origin(production, monkeypatch, origin):
    monkeypatch.setenv("FRONTEND_URL", origin)
    with pytest.raises(RuntimeError, match="HTTPS website origins"):
        validate_hosted_settings()


def test_production_requires_real_email(production, monkeypatch):
    monkeypatch.setenv("EMAIL_BACKEND", "console")
    with pytest.raises(RuntimeError, match="EMAIL_BACKEND"):
        validate_hosted_settings()


def test_production_accepts_explicit_website_origins(production, monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://triage.example.com/, https://custom.example.com")
    validate_hosted_settings()
    assert cors_origins() == ["https://triage.example.com", "https://custom.example.com"]


@pytest.mark.parametrize("port", [465, 587])
def test_smtp_uses_tls_and_authenticates(monkeypatch, port):
    for name, value in {"EMAIL_BACKEND": "smtp", "EMAIL_FROM": "support@example.com",
                        "FRONTEND_URL": "https://triage.example.com", "SMTP_HOST": "smtp.example.com",
                        "SMTP_PORT": str(port), "SMTP_USERNAME": "support@example.com",
                        "SMTP_PASSWORD": "test-mail-password"}.items():
        monkeypatch.setenv(name, value)
    calls = []

    class Server:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def starttls(self, *, context):
            calls.append("tls")

        def login(self, username, password):
            calls.append("login")

        def send_message(self, message):
            calls.append(message["To"])

    def ssl_server(*args, **kwargs):
        calls.append("ssl")
        return Server()

    monkeypatch.setattr(smtplib, "SMTP_SSL", ssl_server)
    monkeypatch.setattr(smtplib, "SMTP", lambda *args, **kwargs: Server())
    email_verification.send_verification_email("customer@example.com", "test-token")
    assert calls == ["ssl" if port == 465 else "tls", "login", "customer@example.com"]


def test_health_reports_dependency_failure(client, monkeypatch):
    from main import app

    async def unavailable():
        raise OSError("private connection details")

    monkeypatch.setattr(app.state, "redis", SimpleNamespace(ping=unavailable), raising=False)
    response = client.get("/health")
    assert response.status_code == 503
    assert "private connection" not in response.text


@pytest.mark.parametrize("case", ["missing", "wrong-customer", "expired", "not-verified"])
def test_complaint_rejects_unverified_identity(client, db_session, case):
    from agent.queue import get_redis_pool
    from main import app

    jobs = []

    class Queue:
        async def enqueue_job(self, *args):
            jobs.append(args)

    app.dependency_overrides[get_redis_pool] = lambda: Queue()
    customer = Customer(name="Verified", email="verified@example.com", email_verified=True)
    other = Customer(name="Other", email="other@example.com", email_verified=True)
    db_session.add_all([customer, other])
    db_session.flush()
    token = VerificationToken(
        customer_id=customer.id, token="private-email-token",
        used=case != "not-verified",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=-1 if case == "expired" else 30),
    )
    db_session.add(token)
    db_session.commit()
    response = client.post("/tickets/", json={
        "customer_id": other.id if case == "wrong-customer" else customer.id,
        "subject": "Complaint", "description": "Details",
        "verification_token": None if case == "missing" else token.token,
    })
    assert response.status_code == 403
    assert not jobs
    assert db_session.query(Ticket).count() == 0
