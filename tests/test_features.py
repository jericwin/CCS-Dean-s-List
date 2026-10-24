"""Announcements, feedback, settings, chat, and page rendering."""
import io

from conftest import PASSWORD, PNG_BYTES, login_admin, login_dean, login_student


def test_every_page_renders(client):
    login_student(client)
    for url in ("/student", "/student/deans_list", "/student/announcements", "/student/notifications",
                "/student/chat", "/student/feedback", "/student/settings", "/dashboard"):
        res = client.get(url, follow_redirects=True)
        assert res.status_code == 200, url
    client.get("/logout")
    login_admin(client)
    for url in ("/admin/dashboard", "/admin/dashboard?year=2025-2026&semester=1st", "/admin/announcements",
                "/admin/deans_list_applications", "/admin/deans_list_applications?status=Pending",
                "/admin/ranking", "/admin/ranking?status=All&program=BSIT", "/admin/feedback",
                "/admin/feedback?position=President", "/admin/chat", "/admin/settings"):
        assert client.get(url).status_code == 200, url
    client.get("/admin/logout")
    login_dean(client)
    for url in ("/dean/dashboard", "/dean/dashboard?year=2024-2025&semester=1st", "/dean/applications"):
        assert client.get(url).status_code == 200, url


def test_announcement_crud(app, client, db):
    login_admin(client)
    res = client.post("/admin/announcements", data={"title": "Filing opens", "body": "Submit by Friday.",
                                                    "image": (io.BytesIO(PNG_BYTES), "cover.png")},
                      content_type="multipart/form-data")
    assert res.status_code == 302
    ann = db.one("SELECT * FROM announcements WHERE title='Filing opens'")
    assert ann["image_path"].startswith("static/uploads/announcements/")

    res = client.post(f"/admin/edit_announcement/{ann['id']}", data={"title": "Filing opens Monday", "body": "Updated."})
    assert res.status_code == 200 and res.get_json()["message"]
    assert db.one("SELECT title FROM announcements WHERE id=%s", (ann["id"],))["title"] == "Filing opens Monday"
    assert client.post(f"/admin/edit_announcement/{ann['id']}", data={"title": "", "body": ""}).status_code == 422
    assert client.post("/admin/edit_announcement/999999", data={"title": "abc", "body": "x"}).status_code == 404

    client.get("/admin/logout")
    login_student(client)
    assert b"Filing opens Monday" in client.get("/student/announcements").data
    assert client.delete(f"/admin/delete_announcement/{ann['id']}").status_code == 403
    client.get("/logout")

    login_admin(client)
    res = client.delete(f"/admin/delete_announcement/{ann['id']}")
    assert res.status_code == 200
    assert db.one("SELECT id FROM announcements WHERE id=%s", (ann["id"],)) is None
    assert client.delete(f"/admin/delete_announcement/{ann['id']}").status_code == 404


def test_feedback_and_reply(client, db):
    login_student(client)
    client.post("/student/feedback", data={"position": "President", "feedback": "Please extend the deadline."})
    client.post("/student/feedback", data={"position": "VP", "feedback": "Anonymous note here", "anonymous": "on"})
    client.post("/student/feedback", data={"position": "Hacker", "feedback": "invalid position"})
    named = db.one("SELECT * FROM student_feedback WHERE feedback='Please extend the deadline.'")
    anon = db.one("SELECT * FROM student_feedback WHERE feedback='Anonymous note here'")
    assert named["student_id"] == 6 and anon["student_id"] is None and anon["anonymous"] == 1
    assert db.one("SELECT id FROM student_feedback WHERE position='Hacker'") is None
    client.get("/logout")

    login_admin(client)
    page = client.get("/admin/feedback")
    assert b"Lux Reyes" in page.data and b"Anonymous student" in page.data
    client.post("/admin/feedback", data={"feedback_id": named["id"], "reply": "Extended to Monday."})
    assert db.one("SELECT admin_reply FROM student_feedback WHERE id=%s", (named["id"],))["admin_reply"] == "Extended to Monday."
    client.get("/admin/logout")

    login_student(client)
    assert b"Extended to Monday." in client.get("/student/feedback").data


def test_password_changes(client, db):
    login_student(client, "leblanc@gmail.com")
    client.post("/student/settings", data={"current_password": "wrong", "new_password": "newpass123", "confirm_password": "newpass123"})
    client.post("/student/settings", data={"current_password": PASSWORD, "new_password": "short", "confirm_password": "short"})
    client.get("/logout")
    assert login_student(client, "leblanc@gmail.com").status_code == 302  # unchanged so far
    res = client.post("/student/settings", data={"current_password": PASSWORD, "new_password": "newpass123", "confirm_password": "newpass123"})
    assert res.status_code == 302
    client.get("/logout")
    assert login_student(client, "leblanc@gmail.com").status_code == 401
    assert login_student(client, "leblanc@gmail.com", "newpass123").status_code == 302
    client.post("/student/settings", data={"current_password": "newpass123", "new_password": PASSWORD, "confirm_password": PASSWORD})
    client.get("/logout")

    login_admin(client)
    res = client.post("/admin/settings", data={"current_password": "password", "new_password": "admin-pass-2026", "confirm_password": "admin-pass-2026"})
    assert res.status_code == 302
    client.get("/admin/logout")
    assert login_admin(client).status_code == 401
    assert login_admin(client, password="admin-pass-2026").status_code == 302
    client.post("/admin/settings", data={"current_password": "admin-pass-2026", "new_password": "password", "confirm_password": "password"})


def test_chat_http_and_socket(app, client, db):
    from portal.extensions import socketio

    login_student(client)  # Lux, id 6
    student_sock = socketio.test_client(app, flask_test_client=client)
    assert student_sock.is_connected()
    # Even if the client lies about who it is, the server uses the session identity.
    ack = student_sock.emit("send_message", {"message": "Hello SBO", "sender_role": "admin", "sender_id": 0,
                                             "receiver_id": 5}, callback=True)
    assert ack["ok"]
    saved = db.one("SELECT * FROM chat_messages WHERE id=%s", (ack["id"],))
    assert saved["sender_role"] == "student" and saved["sender_id"] == 6 and saved["receiver_id"] == 0
    assert saved["sender_name"] == "Lux Reyes"
    assert student_sock.emit("send_message", {"message": "   "}, callback=True)["error"]

    history = client.get("/chat/messages/1").get_json()  # path id is ignored for students
    assert all(6 in (m["sender_id"], m["receiver_id"]) for m in history)
    assert history[-1]["message"] == "Hello SBO"

    admin_client = app.test_client()
    login_admin(admin_client)
    admin_sock = socketio.test_client(app, flask_test_client=admin_client)
    students = admin_client.get("/chat/students?all=1").get_json()
    lux = next(s for s in students if s["id"] == 6)
    assert lux["unread_count"] >= 1 and lux["last_message"] == "Hello SBO"
    assert admin_client.get("/chat/messages/6").status_code == 200
    assert db.one("SELECT COUNT(*) AS n FROM chat_messages WHERE sender_id=6 AND receiver_id=0 AND is_read=0")["n"] == 0

    # Flask-SocketIO 5.3.5's test client can't observe emits with python-socketio 5.10, so capture
    # the server-side emits to verify routing (real delivery is checked against the live server).
    sent = []
    original = socketio.emit
    socketio.emit = lambda event, data=None, **kw: sent.append((event, data, kw.get("room") or kw.get("to")))
    try:
        ack = admin_sock.emit("send_message", {"message": "Hi Lux, how can we help?", "receiver_id": 6}, callback=True)
    finally:
        socketio.emit = original
    assert ack["ok"]
    rooms = {room for event, data, room in sent if event == "receive_message" and data["message"] == "Hi Lux, how can we help?"}
    assert rooms == {"user_6", "admin_room"}
    assert admin_sock.emit("send_message", {"message": "x", "receiver_id": 99999}, callback=True)["error"]

    # HTTP fallback
    res = admin_client.post("/chat/send", json={"message": "Via HTTP", "receiver_id": 6})
    assert res.status_code == 201 and res.get_json()["sender_role"] == "admin"
    assert admin_client.post("/chat/send", json={"message": "x" * 2001, "receiver_id": 6}).status_code == 400

    # anonymous sockets are refused
    anon = socketio.test_client(app, flask_test_client=app.test_client())
    assert not anon.is_connected()
    student_sock.disconnect()
    admin_sock.disconnect()


def test_csrf_enforced(app, client):
    app.config["CSRF_ENABLED"] = True
    try:
        res = client.post("/login", data={"email": "lux@gmail.com", "password": PASSWORD})
        assert res.status_code == 302 and "/student" not in res.headers["Location"]  # bounced, not signed in
        page = client.get("/login")
        token = page.data.split(b'name="csrf-token" content="')[1].split(b'"')[0].decode()
        res = client.post("/login", data={"email": "lux@gmail.com", "password": PASSWORD, "csrf_token": token})
        assert res.headers["Location"].endswith("/student")
        res = client.post("/student/notifications/read", json={}, headers={"X-Requested-With": "fetch"})
        assert res.status_code == 400
    finally:
        app.config["CSRF_ENABLED"] = False


def test_legacy_uploads_require_sign_in(client):
    assert client.get("/static/uploads/flowchart.jpg").status_code == 403
    login_student(client)
    assert client.get("/static/uploads/flowchart.jpg").status_code == 200
    assert client.get("/static/logo.png").status_code == 200
