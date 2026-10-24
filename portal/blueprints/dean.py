"""Dean pages: final approval of SBO-endorsed applications."""
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from .. import db, services
from ..domain import (
    DEAN_STATUSES, STATUS_DEAN_APPROVED, STATUS_DEAN_REJECTED, STATUS_DEAN_REVIEW, STATUS_LABELS, academic_years,
)
from ..security import ROLE_DEAN, login_required

bp = Blueprint("dean", __name__, url_prefix="/dean")

_IN_DEAN_STAGE = "status IN (%s, %s, %s)"


@bp.route("/dashboard")
@login_required(ROLE_DEAN)
def dashboard():
    year = request.args.get("year", "All")
    semester = request.args.get("semester", "All")
    clauses, params = [_IN_DEAN_STAGE], list(DEAN_STATUSES)
    if year != "All":
        clauses.append("academic_year = %s")
        params.append(year)
    if semester != "All":
        clauses.append("semester = %s")
        params.append(semester)
    where = " WHERE " + " AND ".join(clauses)

    by_status = {
        r["status"]: int(r["n"])
        for r in db.fetch_all(f"SELECT status, COUNT(*) AS n FROM deans_list_applications{where} GROUP BY status", params)
    }
    kpis = {
        "total": sum(by_status.values()),
        "pending": by_status.get(STATUS_DEAN_REVIEW, 0),
        "approved": by_status.get(STATUS_DEAN_APPROVED, 0),
        "rejected": by_status.get(STATUS_DEAN_REJECTED, 0),
    }
    courses = db.fetch_all(
        f"SELECT course, COUNT(*) AS n FROM deans_list_applications{where} GROUP BY course ORDER BY course", params
    )
    approved_terms = db.fetch_all(
        f"""
        SELECT COALESCE(academic_year, 'Unspecified') AS academic_year, COALESCE(semester, '—') AS semester,
               COUNT(*) AS n
        FROM deans_list_applications{where} AND status = %s
        GROUP BY academic_year, semester ORDER BY academic_year, semester
        """,
        params + [STATUS_DEAN_APPROVED],
    )
    awaiting = db.fetch_all(
        "SELECT * FROM deans_list_applications WHERE status = %s ORDER BY gwa ASC, created_at ASC LIMIT 6",
        (STATUS_DEAN_REVIEW,),
    )
    return render_template(
        "dean/dashboard.html",
        kpis=kpis,
        charts={
            "status": {"labels": [STATUS_LABELS[s] for s in DEAN_STATUSES],
                       "values": [by_status.get(s, 0) for s in DEAN_STATUSES], "keys": DEAN_STATUSES},
            "courses": {"labels": [r["course"] for r in courses], "values": [int(r["n"]) for r in courses]},
            "approved": {"labels": [f"{r['academic_year']} · {r['semester']}" for r in approved_terms],
                         "values": [int(r["n"]) for r in approved_terms]},
        },
        awaiting=awaiting,
        years=academic_years(current_app.config["FIRST_ACADEMIC_YEAR"], services.known_academic_years()),
        current_year=year,
        current_semester=semester,
    )


@bp.route("/applications", methods=["GET", "POST"])
@login_required(ROLE_DEAN)
def applications():
    if request.method == "POST":
        app_id = request.form.get("app_id", type=int)
        status = request.form.get("status", "")
        comment = request.form.get("comment", "").strip()
        record = services.application_for(app_id) if app_id else None
        if not record or record["status"] not in DEAN_STATUSES:
            flash("That application is not awaiting a Dean decision.", "danger")
        elif status not in DEAN_STATUSES:
            flash("Choose a valid decision.", "danger")
        elif len(comment) > 2000:
            flash("Comments must be 2,000 characters or fewer.", "danger")
        else:
            db.execute("UPDATE deans_list_applications SET status = %s, admin_comment = %s WHERE id = %s",
                       (status, comment or None, app_id))
            if status != record["status"] or comment != (record["admin_comment"] or ""):
                services.notify_student(record["student_id"], status, comment, by_dean=True)
            flash("Decision saved and the student was notified.", "success")
        return redirect(request.referrer or url_for("dean.applications"))

    rows = db.fetch_all(
        f"SELECT * FROM deans_list_applications WHERE {_IN_DEAN_STAGE} ORDER BY FIELD(status, %s, %s, %s), gwa ASC",
        list(DEAN_STATUSES) + list(DEAN_STATUSES),
    )
    return render_template(
        "dean/applications.html",
        applications=rows,
        years=academic_years(current_app.config["FIRST_ACADEMIC_YEAR"], services.known_academic_years()),
    )
