# backend/tests/test_smoke.py
def test_health_check_reaches_app(client):
    res = client.get("/tickets/", headers={})  # no auth — expect a 401/403, not a 500
    assert res.status_code in (401, 403)

def test_can_register_and_login(client):
    res = client.post("/auth/register", json={
        "username": "smoke_user", "email": "smoke@test.com",
        "password": "password123", "role": "viewer"
    })
    assert res.status_code == 201, res.text

    res = client.post("/auth/login", json={"username": "smoke_user", "password": "password123"})
    assert res.status_code == 200, res.text
    assert "access_token" in res.json()