"""End-to-end Dean's List workflow: student applies → SBO reviews → Dean decides."""
from conftest import PDF_BYTES, PNG_BYTES, file_field, login_admin, login_dean, login_student


def _apply(client, **overrides):
    data = {"course": "bscs_2a", "academic_year": "2025-2026", "semester": "2nd", "gwa": "1.35",
            "cog": file_field(PDF_BYTES, "grades.pdf"), "coe": file_field(PNG_BYTES, "enrolment.png")}
    data.update(overrides)
    return client.post("/student/deans_list", data=data, content_type="multipart/form-data")


def test_full_workflow(app, client, db):
    login_student(client)  # Lux Reyes, id 6
    res = _apply(client)
    assert res.status_code == 302
    app_row = db.one("SELECT * FROM deans_list_applications WHERE student_id = 6 ORDER BY id DESC LIMIT 1")
    assert app_row["status"] == "Pending" and str(app_row["gwa"]) == "1.35"
    assert app_row["full_name"] == "Lux Reyes" and app_row["course"] == "bscs_2a"
    app_id = app_row["id"]

    # duplicate for the same term is refused
    res = _apply(client)
    assert res.status_code == 422 and b"already applied" in res.data

    # the student can open their own document; others cannot
    assert client.get(f"/view_file/{app_id}/cog").data.startswith(b"%PDF")
    client.get("/logout")
    login_student(client, "leblanc@gmail.com")
    assert client.get(f"/view_file/{app_id}/cog").status_code == 403
    client.get("/logout")

    # SBO approves (with corrected GWA) → student notified
    login_admin(client)
    page = client.get("/admin/deans_list_applications")
    assert page.status_code == 200 and b"Lux Reyes" in page.data
    assert client.get(f"/view_file/{app_id}/coe").data.startswith(b"\x89PNG")
    res = client.post("/admin/deans_list_applications",
                      data={"app_id": app_id, "status": "Approved", "gwa": "1.30", "comment": "Documents verified."})
    assert res.status_code == 302
    row = db.one("SELECT status, gwa, admin_comment FROM deans_list_applications WHERE id=%s", (app_id,))
    assert row["status"] == "Approved" and str(row["gwa"]) == "1.30" and row["admin_comment"] == "Documents verified."
    note = db.one("SELECT * FROM student_notification WHERE student_id = 6 ORDER BY id DESC LIMIT 1")
    assert note["app_status"] == "Approved" and note["is_read"] == 0 and "Documents verified." in note["message"]

    # invalid admin input is rejected
    client.post("/admin/deans_list_applications", data={"app_id": app_id, "status": "Dean Approved", "gwa": "1.3"})
    client.post("/admin/deans_list_applications", data={"app_id": app_id, "status": "Approved", "gwa": "9"})
    assert db.one("SELECT status, gwa FROM deans_list_applications WHERE id=%s", (app_id,))["status"] == "Approved"

    # ranking lists it; exports work
    ranking = client.get("/admin/ranking?status=Approved&academic_year=2025-2026")
    assert b"Lux Reyes" in ranking.data
    xlsx = client.get("/admin/ranking?status=Approved&export=excel")
    assert xlsx.status_code == 200 and xlsx.data[:2] == b"PK"
    pdf = client.get("/admin/ranking?status=Approved&export=pdf")
    assert pdf.status_code == 200 and pdf.data.startswith(b"%PDF")

    # send to Dean for this term only
    res = client.post("/send_to_dean", data={"academic_year": "2025-2026", "semester": "2nd"})
    assert res.status_code == 302
    assert db.one("SELECT status FROM deans_list_applications WHERE id=%s", (app_id,))["status"] == "For Dean Review"
    client.get("/admin/logout")

    # Dean approves → final; SBO can no longer change it
    login_dean(client)
    page = client.get("/dean/applications")
    assert b"Lux Reyes" in page.data
    assert client.post("/dean/applications", data={"app_id": app_id, "status": "Approved"}).status_code == 302
    assert db.one("SELECT status FROM deans_list_applications WHERE id=%s", (app_id,))["status"] == "For Dean Review"
    client.post("/dean/applications", data={"app_id": app_id, "status": "Dean Approved", "comment": "Congratulations!"})
    assert db.one("SELECT status FROM deans_list_applications WHERE id=%s", (app_id,))["status"] == "Dean Approved"
    assert client.get("/dean/dashboard").status_code == 200
    client.get("/dean/logout")

    login_admin(client)
    client.post("/admin/deans_list_applications", data={"app_id": app_id, "status": "Pending", "gwa": "1.30"})
    assert db.one("SELECT status FROM deans_list_applications WHERE id=%s", (app_id,))["status"] == "Dean Approved"
    client.get("/admin/logout")

    # student sees the outcome and can mark notifications read
    login_student(client)
    dash = client.get("/student")
    assert b"Dean Approved" in dash.data
    notes = client.get("/student/notifications")
    assert b"Congratulations!" in notes.data
    res = client.post("/student/notifications/read", json={})
    assert res.get_json()["ok"] is True
    assert db.one("SELECT COUNT(*) AS n FROM student_notification WHERE student_id=6 AND is_read=0")["n"] == 0


def test_application_validation(client, db):
    login_student(client, "leblanc@gmail.com")
    before = db.one("SELECT COUNT(*) AS n FROM deans_list_applications")["n"]
    assert _apply(client, gwa="0.5").status_code == 422
    assert _apply(client, course="not_a_course").status_code == 422
    assert _apply(client, semester="3rd").status_code == 422
    res = _apply(client, cog=file_field(b"MZ\x90\x00 not a pdf", "evil.pdf"))
    assert res.status_code == 422 and b"valid .pdf" in res.data
    res = _apply(client, coe=file_field(b"<script>", "x.html"))
    assert res.status_code == 422
    assert db.one("SELECT COUNT(*) AS n FROM deans_list_applications")["n"] == before


def test_legacy_record_files_still_open(client):
    login_admin(client)
    # application 5 references flowchart.jpg in the legacy static/uploads folder
    res = client.get("/view_file/5/registration")
    assert res.status_code == 200 and res.data[:3] == b"\xff\xd8\xff"
    assert client.get("/view_file/5/bogus").status_code == 404
    assert client.get("/view_file/99999/cog").status_code == 404
