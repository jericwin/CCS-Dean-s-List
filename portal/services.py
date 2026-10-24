"""Queries and workflows shared across blueprints."""
from datetime import date

from . import db
from .domain import STATUS_LABELS
from .extensions import socketio


def notify_student(student_id, status, remarks=None, by_dean=False):
    """Record a status-change notification and push it live to the student's open tabs."""
    if not student_id:
        return
    who = "the Dean" if by_dean else "the SBO"
    label = STATUS_LABELS.get(status, status)
    message = f"Your Dean's List application was updated to {label} by {who}."
    if remarks:
        message += f"\nRemarks: {remarks}"
    db.execute(
        "INSERT INTO student_notification (student_id, message, status, app_status, is_read) "
        "VALUES (%s, %s, 'unread', %s, 0)",
        (student_id, message, status),
    )
    socketio.emit("notification", {"message": message, "status": status}, room=f"user_{student_id}")


def student_applications(student_id, full_name):
    return db.fetch_all(
        """
        SELECT * FROM deans_list_applications
        WHERE student_id = %s OR (student_id IS NULL AND full_name = %s)
        ORDER BY created_at DESC
        """,
        (student_id, full_name),
    )


def application_for(app_id):
    return db.fetch_one("SELECT * FROM deans_list_applications WHERE id = %s", (app_id,))


def known_academic_years():
    rows = db.fetch_all(
        "SELECT DISTINCT academic_year FROM deans_list_applications WHERE academic_year IS NOT NULL"
    )
    return [r["academic_year"] for r in rows]


def monthly_counts(table, where="", params=(), months=12):
    """Counts per calendar month for the trailing `months` months, oldest first."""
    rows = db.fetch_all(
        f"""
        SELECT EXTRACT(YEAR_MONTH FROM created_at) AS ym, COUNT(*) AS n
        FROM {table}
        WHERE created_at >= DATE_SUB(
            DATE_SUB(CURDATE(), INTERVAL DAYOFMONTH(CURDATE()) - 1 DAY), INTERVAL {int(months) - 1} MONTH
        ) {where}
        GROUP BY ym
        """,
        params,
    )
    found = {int(r["ym"]): int(r["n"]) for r in rows}
    today = date.today()
    labels, values = [], []
    for offset in range(months - 1, -1, -1):
        year, month = today.year, today.month - offset
        while month <= 0:
            month += 12
            year -= 1
        key = year * 100 + month
        labels.append(date(year, month, 1).strftime("%b %y"))
        values.append(found.get(key, 0))
    return labels, values
