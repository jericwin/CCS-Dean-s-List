"""SBO admin pages."""
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, send_file, session, url_for

from .. import db, exports, services
from ..domain import (
    ADMIN_SETTABLE_STATUSES, ALL_STATUSES, DEAN_FINAL_STATUSES, PROGRAMS, SEMESTER_VALUES, STATUS_APPROVED,
    STATUS_DEAN_APPROVED, STATUS_DEAN_REVIEW, STATUS_LABELS, STATUS_PENDING, academic_years, parse_gwa,
)
from ..security import ROLE_ADMIN, hash_password, login_required, password_problem, verify_password
from ..uploads import UploadError, delete_announcement_image, save_announcement_image

bp = Blueprint("admin", __name__)


def _term_filters(year, semester, prefix=""):
    clauses, params = [], []
    if year and year != "All":
        clauses.append(f"{prefix}academic_year = %s")
        params.append(year)
    if semester and semester != "All":
        clauses.append(f"{prefix}semester = %s")
        params.append(semester)
    return clauses, params


# --------------------------------------------------------------------------- dashboard
@bp.route("/admin/dashboard")
@login_required(ROLE_ADMIN)
def dashboard():
    year = request.args.get("year", "All")
    semester = request.args.get("semester", "All")
    clauses, params = _term_filters(year, semester)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    and_where = (" AND " + " AND ".join(clauses)) if clauses else ""

    status_rows = db.fetch_all(
        f"SELECT status, COUNT(*) AS n FROM deans_list_applications{where} GROUP BY status", params
    )
    by_status = {r["status"]: int(r["n"]) for r in status_rows if r["status"]}
    kpis = {
        "students": int(db.fetch_value("SELECT COUNT(*) AS n FROM users WHERE role = 'student'")),
        "announcements": int(db.fetch_value("SELECT COUNT(*) AS n FROM announcements")),
        "feedback": int(db.fetch_value("SELECT COUNT(*) AS n FROM student_feedback")),
        "applications": sum(by_status.values()),
        "pending": by_status.get(STATUS_PENDING, 0),
        "dean_review": by_status.get(STATUS_DEAN_REVIEW, 0),
        "dean_approved": by_status.get(STATUS_DEAN_APPROVED, 0),
    }

    approved_terms = db.fetch_all(
        f"""
        SELECT COALESCE(academic_year, 'Unspecified') AS academic_year, COALESCE(semester, '—') AS semester,
               COUNT(*) AS n
        FROM deans_list_applications
        WHERE status = %s{and_where}
        GROUP BY academic_year, semester
        ORDER BY academic_year, semester
        """,
        [STATUS_DEAN_APPROVED] + params,
    )
    programs = db.fetch_all(
        f"""
        SELECT UPPER(SUBSTRING_INDEX(course, '_', 1)) AS program, COUNT(*) AS n
        FROM deans_list_applications{where}
        GROUP BY program ORDER BY n DESC
        """,
        params,
    )
    signup_labels, signup_values = services.monthly_counts("users", "AND role = 'student'")
    _, announcement_values = services.monthly_counts("announcements")
    _, feedback_values = services.monthly_counts("student_feedback")

    recent_applications = db.fetch_all(
        f"SELECT * FROM deans_list_applications{where} ORDER BY created_at DESC LIMIT 5", params
    )
    recent_feedback = db.fetch_all(
        """
        SELECT sf.*, u.fullname FROM student_feedback sf
        LEFT JOIN users u ON u.id = sf.student_id
        ORDER BY sf.created_at DESC LIMIT 4
        """
    )
    return render_template(
        "admin/dashboard.html",
        kpis=kpis,
        charts={
            "status": {"labels": [STATUS_LABELS.get(s, s) for s in ALL_STATUSES if by_status.get(s)],
                       "values": [by_status[s] for s in ALL_STATUSES if by_status.get(s)],
                       "keys": [s for s in ALL_STATUSES if by_status.get(s)]},
            "approved": {"labels": [f"{r['academic_year']} · {r['semester']}" for r in approved_terms],
                         "values": [int(r["n"]) for r in approved_terms]},
            "programs": {"labels": [r["program"] for r in programs], "values": [int(r["n"]) for r in programs]},
            "activity": {"labels": signup_labels, "signups": signup_values,
                         "announcements": announcement_values, "feedback": feedback_values},
        },
        recent_applications=recent_applications,
        recent_feedback=recent_feedback,
        years=academic_years(current_app.config["FIRST_ACADEMIC_YEAR"], services.known_academic_years()),
        current_year=year,
        current_semester=semester,
    )


# --------------------------------------------------------------------------- announcements
@bp.route("/admin/announcements", methods=["GET", "POST"])
@login_required(ROLE_ADMIN)
def announcements():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        if not (3 <= len(title) <= 255) or not body:
            flash("Give the announcement a title (3–255 characters) and some content.", "danger")
            return redirect(url_for("admin.announcements"))
        image_path = None
        image = request.files.get("image")
        if image and image.filename:
            try:
                image_path = save_announcement_image(image)
            except UploadError as err:
                flash(str(err), "danger")
                return redirect(url_for("admin.announcements"))
        db.execute("INSERT INTO announcements (title, body, image_path) VALUES (%s, %s, %s)", (title, body, image_path))
        flash("Announcement posted.", "success")
        return redirect(url_for("admin.announcements"))

    rows = db.fetch_all("SELECT * FROM announcements ORDER BY created_at DESC")
    return render_template("admin/announcements.html", announcements=rows)


@bp.route("/admin/edit_announcement/<int:id>", methods=["POST"])
@login_required(ROLE_ADMIN)
def edit_announcement(id):
    existing = db.fetch_one("SELECT * FROM announcements WHERE id = %s", (id,))
    if not existing:
        return jsonify(error="Announcement not found."), 404
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    if not (3 <= len(title) <= 255) or not body:
        return jsonify(error="Title (3–255 characters) and content are required."), 422

    image_path = existing["image_path"]
    image = request.files.get("image")
    remove_image = request.form.get("remove_image") == "1"
    if image and image.filename:
        try:
            image_path = save_announcement_image(image)
        except UploadError as err:
            return jsonify(error=str(err)), 422
        delete_announcement_image(existing["image_path"])
    elif remove_image:
        delete_announcement_image(existing["image_path"])
        image_path = None

    db.execute("UPDATE announcements SET title = %s, body = %s, image_path = %s WHERE id = %s",
               (title, body, image_path, id))
    return jsonify(message="Announcement updated.")


@bp.route("/admin/delete_announcement/<int:id>", methods=["DELETE"])
@login_required(ROLE_ADMIN)
def delete_announcement(id):
    existing = db.fetch_one("SELECT image_path FROM announcements WHERE id = %s", (id,))
    if not existing:
        return jsonify(error="Announcement not found."), 404
    db.execute("DELETE FROM announcements WHERE id = %s", (id,))
    delete_announcement_image(existing["image_path"])
    return jsonify(message="Announcement deleted.")


# --------------------------------------------------------------------------- feedback
@bp.route("/admin/feedback", methods=["GET", "POST"])
@login_required(ROLE_ADMIN)
def feedback():
    if request.method == "POST":
        feedback_id = request.form.get("feedback_id", type=int)
        reply = request.form.get("reply", "").strip()
        if not feedback_id or len(reply) > 2000:
            flash("Write a reply of up to 2,000 characters.", "danger")
        else:
            _, changed = db.execute("UPDATE student_feedback SET admin_reply = %s WHERE id = %s",
                                    (reply or None, feedback_id))
            flash("Reply saved." if changed else "That feedback no longer exists.", "success" if changed else "warning")
        return redirect(url_for("admin.feedback", position=request.args.get("position")))

    position = request.args.get("position", "All")
    params, where = [], ""
    if position != "All":
        where, params = " WHERE sf.position = %s", [position]
    rows = db.fetch_all(
        f"""
        SELECT sf.*, u.fullname, u.email FROM student_feedback sf
        LEFT JOIN users u ON u.id = sf.student_id{where}
        ORDER BY sf.created_at DESC
        """,
        params,
    )
    return render_template("admin/feedback.html", feedbacks=rows, position=position)


# --------------------------------------------------------------------------- applications
@bp.route("/admin/deans_list_applications", methods=["GET", "POST"])
@login_required(ROLE_ADMIN)
def applications():
    if request.method == "POST":
        app_id = request.form.get("app_id", type=int)
        record = services.application_for(app_id) if app_id else None
        back = redirect(request.referrer or url_for("admin.applications"))
        if not record:
            flash("Application not found.", "danger")
            return back
        if record["status"] in DEAN_FINAL_STATUSES:
            flash("The Dean has already decided on this application; it can no longer be changed.", "warning")
            return back
        status = request.form.get("status", "")
        gwa = parse_gwa(request.form.get("gwa", ""))
        comment = request.form.get("comment", "").strip()
        if status not in ADMIN_SETTABLE_STATUSES:
            flash("Choose a valid status.", "danger")
            return back
        if gwa is None:
            flash("GWA must be between 1.00 and 5.00.", "danger")
            return back
        if len(comment) > 2000:
            flash("Remarks must be 2,000 characters or fewer.", "danger")
            return back

        db.execute("UPDATE deans_list_applications SET status = %s, gwa = %s, admin_comment = %s WHERE id = %s",
                   (status, gwa, comment or None, app_id))
        if record["student_id"]:
            if status != record["status"] or comment != (record["admin_comment"] or ""):
                services.notify_student(record["student_id"], status, comment)
            flash("Application updated and the student was notified.", "success")
        else:
            flash("Application updated, but no student account is linked for notifications.", "warning")
        return back

    status = request.args.get("status", "All")
    year = request.args.get("academic_year", "All")
    semester = request.args.get("semester", "All")
    clauses, params = _term_filters(year, semester)
    if status != "All":
        clauses.append("status = %s")
        params.append(status)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = db.fetch_all(f"SELECT * FROM deans_list_applications{where} ORDER BY created_at DESC", params)
    return render_template(
        "admin/applications.html",
        applications=rows,
        status_filter=status,
        academic_year_filter=year,
        semester_filter=semester,
        years=academic_years(current_app.config["FIRST_ACADEMIC_YEAR"], services.known_academic_years()),
    )


# --------------------------------------------------------------------------- ranking
def _ranking_query(program, status, year, semester):
    clauses, params = _term_filters(year, semester)
    if status != "All":
        clauses.append("status = %s")
        params.append(status)
    if program != "All":
        clauses.append("UPPER(SUBSTRING_INDEX(course, '_', 1)) = %s")
        params.append(program.upper())
    clauses.append("gwa IS NOT NULL")
    return db.fetch_all(
        f"SELECT * FROM deans_list_applications WHERE {' AND '.join(clauses)} ORDER BY gwa ASC, full_name ASC",
        params,
    )


@bp.route("/admin/ranking")
@login_required(ROLE_ADMIN)
def ranking():
    program = request.args.get("program", "All")
    status = request.args.get("status", STATUS_APPROVED)
    year = request.args.get("academic_year", "All")
    semester = request.args.get("semester", "All")
    if program != "All" and program.upper() not in PROGRAMS:
        program = "All"
    if status != "All" and status not in ALL_STATUSES:
        status = STATUS_APPROVED
    rows = _ranking_query(program, status, year, semester)

    export = request.args.get("export")
    if export in ("excel", "pdf"):
        if not rows:
            flash("There is nothing to export for these filters.", "warning")
            return redirect(url_for("admin.ranking", program=program, status=status, academic_year=year, semester=semester))
        if export == "excel":
            return send_file(exports.to_excel(rows), as_attachment=True, download_name="ranking.xlsx",
                             mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        subtitle = " · ".join([
            "All programs" if program == "All" else program,
            "All statuses" if status == "All" else STATUS_LABELS.get(status, status),
            "All years" if year == "All" else f"A.Y. {year}",
            "All semesters" if semester == "All" else f"{semester} Semester",
        ])
        return send_file(exports.to_pdf(rows, subtitle), as_attachment=True, download_name="Deans_List.pdf",
                         mimetype="application/pdf")

    return render_template(
        "admin/ranking.html",
        applications=rows,
        program_filter=program,
        status_filter=status,
        academic_year_filter=year,
        semester_filter=semester,
        years=academic_years(current_app.config["FIRST_ACADEMIC_YEAR"], services.known_academic_years()),
        approved_count=int(db.fetch_value(
            "SELECT COUNT(*) AS n FROM deans_list_applications WHERE status = %s", (STATUS_APPROVED,))),
    )


@bp.route("/send_to_dean", methods=["POST"])
@login_required(ROLE_ADMIN)
def send_to_dean():
    """Forward SBO-approved applications (optionally for one term) to the Dean."""
    year = request.form.get("academic_year", "All")
    semester = request.form.get("semester", "All")
    clauses, params = _term_filters(year, semester)
    where = "".join(f" AND {c}" for c in clauses)
    targets = db.fetch_all(
        f"SELECT id, student_id FROM deans_list_applications WHERE status = %s{where}", [STATUS_APPROVED] + params
    )
    if not targets:
        flash("There are no SBO-approved applications to send for that selection.", "warning")
    else:
        db.execute(
            f"UPDATE deans_list_applications SET status = %s WHERE status = %s{where}",
            [STATUS_DEAN_REVIEW, STATUS_APPROVED] + params,
        )
        for row in targets:
            services.notify_student(row["student_id"], STATUS_DEAN_REVIEW)
        flash(f"Sent {len(targets)} application{'s' if len(targets) != 1 else ''} to the Dean for review.", "success")
    return redirect(url_for("admin.ranking", status=STATUS_DEAN_REVIEW, academic_year=year, semester=semester))


# --------------------------------------------------------------------------- chat & settings
@bp.route("/admin/chat")
@login_required(ROLE_ADMIN)
def chat():
    return render_template("admin/chat.html", open_student=request.args.get("student", type=int))


@bp.route("/admin/settings", methods=["GET", "POST"])
@login_required(ROLE_ADMIN)
def settings():
    admin = db.fetch_one("SELECT * FROM admin WHERE id = %s", (session["user_id"],))
    if request.method == "POST":
        current = request.form.get("current_password", "")
        new = request.form.get("new_password", "")
        problem = password_problem(new, request.form.get("confirm_password", ""))
        if not admin or not verify_password(admin["password"], current):
            flash("Your current password is incorrect.", "danger")
        elif problem:
            flash(problem, "danger")
        else:
            db.execute("UPDATE admin SET password = %s WHERE id = %s", (hash_password(new), admin["id"]))
            flash("Password updated.", "success")
            return redirect(url_for("admin.settings"))
    return render_template("admin/settings.html", admin=admin)
