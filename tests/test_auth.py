from conftest import PASSWORD, login_admin, login_dean, login_student


def test_public_pages_render(client):
    for url in ("/", "/login", "/signup", "/adminlogin", "/dean/login"):
        res = client.get(url)
        assert res.status_code == 200, url
        assert b"logo.png" in res.data  # the official SBO logo is used on every public page


def test_signup_validation_and_duplicate(client, db):
    res = client.post("/signup", data={"fullname": "A", "email": "bad", "password": "short", "confirm_password": "short"})
    assert res.status_code == 422
    assert b"Enter your full name" in res.data and b"valid email" in res.data

    res = client.post("/signup", data={"fullname": "Lux Reyes", "email": "LUX@gmail.com",
                                       "password": "longenough1", "confirm_password": "longenough1"})
    assert res.status_code == 409
    assert b"already registered" in res.data


def test_signup_then_login(client, db):
    res = client.post("/signup", data={"fullname": "  Tala   Santos ", "email": "Tala@Example.com",
                                       "password": "foxtrot-99", "confirm_password": "foxtrot-99"})
    assert res.status_code == 302 and "/login" in res.headers["Location"]
    row = db.one("SELECT fullname, email, role, password_hash FROM users WHERE email = 'tala@example.com'")
    assert row["fullname"] == "Tala Santos" and row["role"] == "student"
    assert row["password_hash"].startswith(("scrypt:", "pbkdf2:"))

    res = login_student(client, "tala@example.com", "foxtrot-99")
    assert res.status_code == 302 and res.headers["Location"].endswith("/student")
    assert client.get("/student").status_code == 200


def test_bad_login_rejected(client):
    res = login_student(client, password="wrong")
    assert res.status_code == 401
    assert b"Invalid email or password" in res.data
    assert client.get("/student").status_code == 302


def test_admin_plaintext_password_is_upgraded(client, db):
    assert not db.one("SELECT password FROM admin WHERE username='admin'")["password"].startswith("scrypt:")
    res = login_admin(client)
    assert res.status_code == 302 and res.headers["Location"].endswith("/admin/dashboard")
    stored = db.one("SELECT password FROM admin WHERE username='admin'")["password"]
    assert stored.startswith(("scrypt:", "pbkdf2:"))
    client.get("/admin/logout")
    assert login_admin(client).status_code == 302  # same password still works after the upgrade


def test_dean_login(client):
    assert login_dean(client, password="nope").status_code == 401
    res = login_dean(client)
    assert res.status_code == 302 and res.headers["Location"].endswith("/dean/dashboard")


def test_role_isolation(client):
    login_student(client)
    assert client.get("/admin/dashboard").status_code == 403
    assert client.get("/dean/dashboard").status_code == 403
    res = client.get("/chat/students", headers={"Accept": "application/json"})
    assert res.status_code == 403 and res.is_json


def test_unauthenticated_json_gets_401(client):
    res = client.get("/chat/messages/5", headers={"X-Requested-With": "fetch"})
    assert res.status_code == 401 and res.get_json()["error"]


def test_logout_clears_session(client):
    login_student(client)
    client.get("/logout")
    assert client.get("/student").status_code == 302


def test_next_redirect_is_local_only(client):
    res = client.post("/login?next=https://evil.example/", data={"email": "lux@gmail.com", "password": PASSWORD})
    assert res.headers["Location"].endswith("/student")
    res = client.post("/login", data={"email": "lux@gmail.com", "password": PASSWORD, "next": "/student/chat"})
    assert res.headers["Location"].endswith("/student/chat")


def test_login_throttle(app, client):
    app.config["LOGIN_MAX_ATTEMPTS"] = 3
    try:
        for _ in range(3):
            login_student(client, email="leblanc@gmail.com", password="bad")
        res = login_student(client, email="leblanc@gmail.com")  # correct password, but locked
        assert res.status_code == 429
    finally:
        app.config["LOGIN_MAX_ATTEMPTS"] = 50
        from portal.security import throttle
        throttle._failures.clear()
