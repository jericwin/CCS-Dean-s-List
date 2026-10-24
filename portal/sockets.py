"""Socket.IO events for live chat. Identity always comes from the server-side session."""
from flask import current_app, session
from flask_socketio import emit, join_room

from .blueprints.chat import ADMIN_ID, identity, save_message
from .extensions import socketio
from .security import ROLE_ADMIN, ROLE_STUDENT

ADMIN_ROOM = "admin_room"


def broadcast(message):
    student_id = message["sender_id"] if message["sender_role"] == ROLE_STUDENT else message["receiver_id"]
    socketio.emit("receive_message", message, room=f"user_{student_id}")
    socketio.emit("receive_message", message, room=ADMIN_ROOM)


@socketio.on("connect")
def on_connect(auth=None):
    role = session.get("role")
    if role == ROLE_STUDENT:
        join_room(f"user_{session['user_id']}")
    elif role == ROLE_ADMIN:
        join_room(ADMIN_ROOM)
    else:
        return False  # reject anonymous and dean sockets
    return None


@socketio.on("join")
def on_join(_data=None):
    """Kept for older clients; rooms are assigned from the session on connect."""
    return {"ok": True}


@socketio.on("send_message")
def on_send_message(data):
    role, sender_id, name = identity()
    if role not in (ROLE_STUDENT, ROLE_ADMIN):
        return {"error": "Not signed in."}
    data = data if isinstance(data, dict) else {}
    if role == ROLE_ADMIN:
        try:
            receiver = int(data.get("receiver_id"))
        except (TypeError, ValueError):
            return {"error": "Choose a student to message."}
    else:
        receiver = ADMIN_ID
    try:
        message, error = save_message(role, sender_id, receiver, name, data.get("message"))
    except Exception:  # database failure: tell the sender instead of dropping silently
        current_app.logger.exception("Could not save chat message")
        return {"error": "Message could not be saved. Please try again."}
    if error:
        return {"error": error}
    broadcast(message)
    return {"ok": True, "id": message["id"]}


@socketio.on("typing")
def on_typing(data):
    role, sender_id, _ = identity()
    data = data if isinstance(data, dict) else {}
    if role == ROLE_STUDENT:
        emit("typing", {"student_id": sender_id, "from": "student"}, room=ADMIN_ROOM)
    elif role == ROLE_ADMIN:
        try:
            emit("typing", {"student_id": int(data.get("receiver_id")), "from": "admin"},
                 room=f"user_{int(data.get('receiver_id'))}")
        except (TypeError, ValueError):
            pass
