"""Sidebar navigation per role, with live badge counts."""
from flask import session

from . import db
from .domain import STATUS_DEAN_REVIEW, STATUS_PENDING
from .security import ROLE_ADMIN, ROLE_DEAN, ROLE_STUDENT


def _safe_count(sql, params=()):
    try:
        return int(db.fetch_value(sql, params))
    except db.DatabaseError:
        return 0


def nav_for(role):
    uid = session.get("user_id")
    if role == ROLE_STUDENT:
        return [
            {"endpoint": "student.dashboard", "label": "Dashboard", "icon": "fa-gauge-high"},
            {"endpoint": "student.deans_list", "label": "Dean's List", "icon": "fa-award"},
            {"endpoint": "student.announcements", "label": "Announcements", "icon": "fa-bullhorn"},
            {"endpoint": "student.notifications", "label": "Notifications", "icon": "fa-bell",
             "badge": _safe_count("SELECT COUNT(*) AS n FROM student_notification WHERE student_id=%s AND is_read=0", (uid,)),
             "badge_id": "notifBadge"},
            {"endpoint": "student.chat", "label": "Chat Support", "icon": "fa-headset",
             "badge": _safe_count("SELECT COUNT(*) AS n FROM chat_messages WHERE receiver_id=%s AND sender_role='admin' AND is_read=0", (uid,)),
             "badge_id": "chatBadge"},
            {"endpoint": "student.feedback", "label": "Feedback", "icon": "fa-comment-dots"},
            {"endpoint": "student.settings", "label": "Settings", "icon": "fa-gear"},
        ]
    if role == ROLE_ADMIN:
        return [
            {"endpoint": "admin.dashboard", "label": "Dashboard", "icon": "fa-gauge-high"},
            {"endpoint": "admin.applications", "label": "Applications", "icon": "fa-file-signature",
             "badge": _safe_count("SELECT COUNT(*) AS n FROM deans_list_applications WHERE status=%s", (STATUS_PENDING,))},
            {"endpoint": "admin.ranking", "label": "Rankings", "icon": "fa-ranking-star"},
            {"endpoint": "admin.announcements", "label": "Announcements", "icon": "fa-bullhorn"},
            {"endpoint": "admin.chat", "label": "Chat Support", "icon": "fa-headset",
             "badge": _safe_count("SELECT COUNT(*) AS n FROM chat_messages WHERE receiver_id=0 AND sender_role='student' AND is_read=0"),
             "badge_id": "chatBadge"},
            {"endpoint": "admin.feedback", "label": "Feedback", "icon": "fa-comment-dots"},
            {"endpoint": "admin.settings", "label": "Settings", "icon": "fa-gear"},
        ]
    if role == ROLE_DEAN:
        return [
            {"endpoint": "dean.dashboard", "label": "Dashboard", "icon": "fa-gauge-high"},
            {"endpoint": "dean.applications", "label": "Applications", "icon": "fa-file-signature",
             "badge": _safe_count("SELECT COUNT(*) AS n FROM deans_list_applications WHERE status=%s", (STATUS_DEAN_REVIEW,))},
        ]
    return []
