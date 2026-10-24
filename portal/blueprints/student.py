"""Student-facing pages."""
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, session, url_for

from .. import db, services
from ..domain import (
    COURSE_LABELS, FEEDBACK_POSITION_VALUES, SEMESTER_VALUES, STATUS_PENDING, academic_years,
    current_academic_year, parse_gwa,
)
from ..security import ROLE_STUDENT, hash_password, login_required, password_problem, verify_password
from ..uploads import UploadError, save_document

bp = Blueprint("student", __name__, url_prefix="/student")


def _me():
    return session["user_id"], session.get("full_name", "")


@bp.route("", strict_slashes=False)
@login_required(ROLE_STUDENT)
def dashboard():
    uid, full_name = _me()
    applications = services.student_applications(uid, full_name)
    counts = {"total": len(applications), "pending": 0, "progress": 0, "approved": 0, "rejected": 0}
    for app in applications:
        tone = app["status"]
        if tone == "Pending":
            counts["pending"] += 1
        elif tone in ("Approved", "For Dean Review"):
            counts["progress"] += 1
        elif tone == "Dean Approved":
            counts["approved"] += 1
        elif tone in ("Rejected", "Dean Rejected"):
            counts["rejected"] += 1
    announcements = db.fetch_all("SELECT * FROM announcements ORDER BY created_at DESC LIMIT 3")
    notifications = db.fetch_all(
        "SELECT * FROM student_notification WHERE student_id = %s ORDER BY created_at DESC LIMIT 4", (uid,)
    )
    return render_template(
        "student/dashboard.html",
        applications=applications,
        latest=applications[0] if applications else None,
        counts=counts,
        announcements=announcements,
        notifications=notifications,
    )


@bp.route("/deans_list", methods=["GET", "POST"])
@login_required(ROLE_STUDENT)
def deans_list():
    uid, full_name = _me()
    years = academic_years(current_app.config["FIRST_ACADEMIC_YEAR"])
    form, errors = {}, {}

    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in ("course", "academic_year", "semester", "gwa")}
        if form["course"] not in COURSE_LABELS:
            errors["course"] = "Choose your course and section."
        if form["academic_year"] not in years:
            errors["academic_year"] = "Choose a valid academic year."
        if form["semester"] not in SEMESTER_VALUES:
            errors["semester"] = "Choose a semester."
        gwa = parse_gwa(form["gwa"])
        if gwa is None:
            errors["gwa"] = "Enter a GWA between 1.00 and 5.00."

        if not errors:
            existing = db.fetch_one(
                """
                SELECT id FROM deans_list_applications
                WHERE (student_id = %s OR (student_id IS NULL AND full_name = %s))
                  AND academic_year = %s AND semester = %s
                """,
                (uid, full_name, form["academic_year"], form["semester"]),
            )
            if existing:
                errors["academic_year"] = "You already applied for this academic year and semester."

        cog_name = coe_name = None
        if not errors:
            try:
                cog_name = save_document(request.files.get("cog"), "Certificate of Grades (COG)", "COG")
                coe_name = save_document(request.files.get("coe"), "Certificate of Enrollment (COE)", "COE")
            except UploadError as err:
                errors["files"] = str(err)

        if errors:
            flash("Please fix the highlighted fields.", "danger")
            status_code = 422
        else:
            db.execute(
                """
                INSERT INTO deans_list_applications
                    (student_id, full_name, course, gwa, academic_year, semester, cog_filename, coe_filename, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (uid, full_name, form["course"], gwa, form["academic_year"], form["semester"],
                 cog_name, coe_name, STATUS_PENDING),
            )
            flash("Application submitted! The SBO will review it soon.", "success")
            return redirect(url_for("student.deans_list"))
    else:
        status_code = 200
        form = {"academic_year": current_academic_year()}

    return render_template(
        "student/deans_list.html",
        applications=services.student_applications(uid, full_name),
        years=years,
        form=form,
        errors=errors,
    ), status_code


@bp.route("/announcements")
@login_required(ROLE_STUDENT)
def announcements():
    rows = db.fetch_all("SELECT * FROM announcements ORDER BY created_at DESC")
    return render_template("student/announcements.html", announcements=rows)


@bp.route("/notifications")
@login_required(ROLE_STUDENT)
def notifications():
    uid, _ = _me()
    rows = db.fetch_all(
        "SELECT * FROM student_notification WHERE student_id = %s ORDER BY created_at DESC", (uid,)
    )
    return render_template("student/notifications.html", notifications=rows)


@bp.route("/notifications/read", methods=["POST"])
@login_required(ROLE_STUDENT)
def mark_notifications_read():
    uid, _ = _me()
    ids = request.get_json(silent=True) or {}
    notif_id = ids.get("id") if isinstance(ids, dict) else None
    if notif_id:
        _, changed = db.execute(
            "UPDATE student_notification SET is_read = 1 WHERE id = %s AND student_id = %s", (int(notif_id), uid)
        )
    else:
        _, changed = db.execute("UPDATE student_notification SET is_read = 1 WHERE student_id = %s", (uid,))
    return jsonify(ok=True, updated=changed)


@bp.route("/chat")
@login_required(ROLE_STUDENT)
def chat():
    return render_template("student/chat.html", user_id=session["user_id"])


@bp.route("/feedback", methods=["GET", "POST"])
@login_required(ROLE_STUDENT)
def feedback():
    uid, _ = _me()
    if request.method == "POST":
        position = request.form.get("position", "")
        text = request.form.get("feedback", "").strip()
        anonymous = request.form.get("anonymous") == "on"
        if position not in FEEDBACK_POSITION_VALUES:
            flash("Choose who your feedback is for.", "danger")
        elif len(text) < 5 or len(text) > 2000:
            flash("Feedback must be between 5 and 2,000 characters.", "danger")
        else:
            db.execute(
                "INSERT INTO student_feedback (student_id, anonymous, position, feedback) VALUES (%s, %s, %s, %s)",
                (None if anonymous else uid, anonymous, position, text),
            )
            flash("Thanks! Your feedback was sent to the SBO.", "success")
            return redirect(url_for("student.feedback"))

    rows = db.fetch_all(
        "SELECT * FROM student_feedback WHERE student_id = %s OR anonymous = 1 ORDER BY created_at DESC", (uid,)
    )
    return render_template("student/feedback.html", feedbacks=rows)


@bp.route("/settings", methods=["GET", "POST"])
@login_required(ROLE_STUDENT)
def settings():
    uid, _ = _me()
    user = db.fetch_one("SELECT id, fullname, email, college, created_at, password_hash FROM users WHERE id = %s", (uid,))
    if request.method == "POST":
        current = request.form.get("current_password", "")
        new = request.form.get("new_password", "")
        problem = password_problem(new, request.form.get("confirm_password", ""))
        if not verify_password(user["password_hash"], current):
            flash("Your current password is incorrect.", "danger")
        elif problem:
            flash(problem, "danger")
        else:
            db.execute("UPDATE users SET password_hash = %s WHERE id = %s", (hash_password(new), uid))
            flash("Password updated.", "success")
            return redirect(url_for("student.settings"))
    return render_template("student/settings.html", user=user)
