"""Chat HTTP API. Real-time delivery lives in portal/sockets.py.

The SBO admin is represented by id 0 in chat_messages (existing convention).
"""
from flask import Blueprint, jsonify, request, session

from .. import db
from ..security import ROLE_ADMIN, ROLE_STUDENT, login_required

bp = Blueprint("chat", __name__, url_prefix="/chat")

ADMIN_ID = 0
MAX_MESSAGE = 2000

_CONVERSATION = "((sender_id = %s AND receiver_id = 0 AND sender_role = 'student') " \
                "OR (sender_id = 0 AND receiver_id = %s AND sender_role = 'admin'))"


def serialize(message):
    message = dict(message)
    if message.get("timestamp"):
        message["timestamp"] = message["timestamp"].isoformat()
    return message


def conversation(student_id, limit=500):
    rows = db.fetch_all(
        f"""
        SELECT * FROM (
            SELECT id, sender_id, receiver_id, sender_role, sender_name, message, timestamp, is_read
            FROM chat_messages WHERE {_CONVERSATION}
            ORDER BY timestamp DESC, id DESC LIMIT {int(limit)}
        ) recent ORDER BY timestamp ASC, id ASC
        """,
        (student_id, student_id),
    )
    return [serialize(r) for r in rows]


def save_message(sender_role, sender_id, receiver_id, sender_name, text):
    """Validate and store a message. Returns (message_dict, error)."""
    text = (text or "").strip()
    if not text:
        return None, "Message cannot be empty."
    if len(text) > MAX_MESSAGE:
        return None, f"Messages are limited to {MAX_MESSAGE} characters."
    if sender_role == ROLE_ADMIN:
        student = db.fetch_one("SELECT id FROM users WHERE id = %s AND role = 'student'", (receiver_id,))
        if not student:
            return None, "That student does not exist."
    with db.transaction() as cur:
        cur.execute(
            "INSERT INTO chat_messages (sender_role, sender_name, sender_id, receiver_id, message) "
            "VALUES (%s, %s, %s, %s, %s)",
            (sender_role, sender_name, sender_id, receiver_id, text),
        )
        cur.execute("SELECT * FROM chat_messages WHERE id = %s", (cur.lastrowid,))
        return serialize(cur.fetchone()), None


def identity():
    """(role, sender_id, display_name) for the signed-in user — never taken from the client."""
    role = session.get("role")
    if role == ROLE_ADMIN:
        return role, ADMIN_ID, "SBO Admin"
    return role, session.get("user_id"), session.get("full_name") or session.get("display_name") or "Student"


@bp.route("/messages/<int:user_id>")
@login_required(ROLE_STUDENT, ROLE_ADMIN)
def messages(user_id):
    if session["role"] == ROLE_STUDENT:
        student_id = session["user_id"]  # students may only read their own thread
        db.execute(
            "UPDATE chat_messages SET is_read = 1 WHERE receiver_id = %s AND sender_role = 'admin' AND is_read = 0",
            (student_id,),
        )
    else:
        student_id = user_id
        db.execute(
            "UPDATE chat_messages SET is_read = 1 WHERE sender_id = %s AND receiver_id = 0 "
            "AND sender_role = 'student' AND is_read = 0",
            (student_id,),
        )
    return jsonify(conversation(student_id))


@bp.route("/send", methods=["POST"])
@login_required(ROLE_STUDENT, ROLE_ADMIN)
def send():
    """HTTP fallback for sending when the websocket is unavailable."""
    from ..sockets import broadcast

    payload = request.get_json(silent=True) or request.form
    role, sender_id, name = identity()
    if role == ROLE_ADMIN:
        receiver = payload.get("receiver_id")
        try:
            receiver = int(receiver)
        except (TypeError, ValueError):
            return jsonify(error="Choose a student to message."), 400
    else:
        receiver = ADMIN_ID
    message, error = save_message(role, sender_id, receiver, name, payload.get("message"))
    if error:
        return jsonify(error=error), 400
    broadcast(message)
    return jsonify(message), 201


@bp.route("/students")
@login_required(ROLE_ADMIN)
def students():
    """Conversation list for the admin; ?all=1 also includes students with no messages yet."""
    include_all = request.args.get("all") == "1"
    rows = db.fetch_all(
        f"""
        SELECT u.id, u.fullname AS name, u.email,
            (SELECT message FROM chat_messages WHERE {_CONVERSATION.replace('%s', 'u.id')}
             ORDER BY timestamp DESC, id DESC LIMIT 1) AS last_message,
            (SELECT timestamp FROM chat_messages WHERE {_CONVERSATION.replace('%s', 'u.id')}
             ORDER BY timestamp DESC, id DESC LIMIT 1) AS last_message_time,
            (SELECT COUNT(*) FROM chat_messages
             WHERE sender_id = u.id AND receiver_id = 0 AND sender_role = 'student' AND is_read = 0) AS unread_count
        FROM users u
        WHERE u.role = 'student'
        {'' if include_all else 'HAVING last_message_time IS NOT NULL'}
        ORDER BY last_message_time IS NULL, last_message_time DESC, u.fullname ASC
        """
    )
    for row in rows:
        if row["last_message_time"]:
            row["last_message_time"] = row["last_message_time"].isoformat()
        row["unread_count"] = int(row["unread_count"] or 0)
    return jsonify(rows)


@bp.route("/mark_read/<int:user_id>", methods=["POST"])
@login_required(ROLE_ADMIN)
def mark_read(user_id):
    _, changed = db.execute(
        "UPDATE chat_messages SET is_read = 1 WHERE sender_id = %s AND receiver_id = 0 "
        "AND sender_role = 'student' AND is_read = 0",
        (user_id,),
    )
    return jsonify(ok=True, updated=changed)
