"""Authentication, authorization, CSRF protection and login throttling."""
import hmac
import secrets
import threading
import time
from functools import wraps

from flask import abort, current_app, flash, jsonify, redirect, request, session, url_for
from markupsafe import Markup
from werkzeug.security import check_password_hash, generate_password_hash

ROLE_STUDENT = "student"
ROLE_ADMIN = "admin"
ROLE_DEAN = "dean"

LOGIN_ENDPOINTS = {
    ROLE_STUDENT: "public.login",
    ROLE_ADMIN: "public.admin_login",
    ROLE_DEAN: "public.dean_login",
}
HOME_ENDPOINTS = {
    ROLE_STUDENT: "student.dashboard",
    ROLE_ADMIN: "admin.dashboard",
    ROLE_DEAN: "dean.dashboard",
}

MIN_PASSWORD_LENGTH = 8
_HASH_PREFIXES = ("scrypt:", "pbkdf2:")


# --------------------------------------------------------------------------- sessions
def current_role():
    return session.get("role")


def start_session(role, user_id, display_name, **extra):
    session.clear()
    session.permanent = True
    session["role"] = role
    session["user_id"] = user_id
    session["display_name"] = display_name
    session.update(extra)
    session["_csrf"] = secrets.token_urlsafe(32)


def wants_json():
    if request.is_json or request.headers.get("X-Requested-With") == "fetch":
        return True
    best = request.accept_mimetypes.best_match(["application/json", "text/html"])
    return best == "application/json" and request.accept_mimetypes[best] > request.accept_mimetypes["text/html"]


def login_required(*roles):
    """Require a logged-in session, optionally restricted to the given roles."""

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            role = current_role()
            if role is None:
                if wants_json():
                    return jsonify(error="Authentication required."), 401
                flash("Please sign in to continue.", "warning")
                target = LOGIN_ENDPOINTS.get(roles[0] if roles else ROLE_STUDENT)
                return redirect(url_for(target, next=request.full_path.rstrip("?") if request.method == "GET" else None))
            if roles and role not in roles:
                if wants_json():
                    return jsonify(error="You do not have permission to do that."), 403
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def safe_next_url(default):
    target = request.args.get("next") or request.form.get("next")
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return default


# --------------------------------------------------------------------------- passwords
def hash_password(password):
    return generate_password_hash(password)


def is_hashed(stored):
    return bool(stored) and stored.startswith(_HASH_PREFIXES)


def verify_password(stored, candidate):
    """Check a password. Supports legacy plaintext values (admin table) for upgrade-on-login."""
    if not stored or candidate is None:
        return False
    if is_hashed(stored):
        try:
            return check_password_hash(stored, candidate)
        except (ValueError, TypeError):
            return False
    return hmac.compare_digest(stored.encode(), candidate.encode())


def password_problem(password, confirm=None):
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if len(password) > 128:
        return "Password must be 128 characters or fewer."
    if confirm is not None and password != confirm:
        return "Passwords do not match."
    return None


# --------------------------------------------------------------------------- CSRF
def csrf_token():
    token = session.get("_csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf"] = token
    return token


def csrf_field():
    return Markup(f'<input type="hidden" name="csrf_token" value="{csrf_token()}">')


def protect_csrf():
    if not current_app.config.get("CSRF_ENABLED", True):
        return None
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return None
    if request.endpoint == "static":
        return None
    sent = request.headers.get("X-CSRFToken") or request.form.get("csrf_token")
    expected = session.get("_csrf")
    if not expected or not sent or not hmac.compare_digest(sent, expected):
        if wants_json():
            return jsonify(error="Your session expired. Refresh the page and try again."), 400
        flash("Your session expired. Please try again.", "danger")
        return redirect(request.referrer or url_for("public.index"))
    return None


# --------------------------------------------------------------------------- throttling
class LoginThrottle:
    """In-memory failed-login counter keyed by client IP and identifier."""

    def __init__(self):
        self._failures = {}
        self._lock = threading.Lock()

    def _key(self, scope, identifier):
        return (scope, request.remote_addr or "?", (identifier or "").strip().lower())

    def blocked_for(self, scope, identifier):
        cfg = current_app.config
        with self._lock:
            entry = self._failures.get(self._key(scope, identifier))
            if not entry:
                return 0
            count, first = entry
            elapsed = time.monotonic() - first
            if elapsed > cfg["LOGIN_LOCKOUT_SECONDS"]:
                self._failures.pop(self._key(scope, identifier), None)
                return 0
            if count >= cfg["LOGIN_MAX_ATTEMPTS"]:
                return int(cfg["LOGIN_LOCKOUT_SECONDS"] - elapsed) + 1
            return 0

    def fail(self, scope, identifier):
        key = self._key(scope, identifier)
        with self._lock:
            count, first = self._failures.get(key, (0, time.monotonic()))
            self._failures[key] = (count + 1, first)

    def reset(self, scope, identifier):
        with self._lock:
            self._failures.pop(self._key(scope, identifier), None)


throttle = LoginThrottle()
