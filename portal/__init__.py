"""CCS Dean's List portal — application factory."""
import logging
import os
from datetime import datetime

from flask import Flask, jsonify, render_template, request, session

from . import db, domain, security
from .config import BASE_DIR, Config, resolve_secret_key
from .extensions import socketio


def create_app(overrides=None):
    app = Flask(
        __name__,
        static_folder=os.path.join(BASE_DIR, "static"),
        template_folder=os.path.join(BASE_DIR, "templates"),
        instance_path=os.path.join(BASE_DIR, "instance"),
    )
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)
    app.config["SECRET_KEY"] = resolve_secret_key(app.config)
    if not app.config.get("TESTING") and not os.environ.get("SECRET_KEY"):
        app.logger.warning("SECRET_KEY is not set; using a temporary key (sessions reset on restart).")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    from .blueprints import admin, chat, dean, files, public, student

    for module in (public, student, admin, dean, chat, files):
        app.register_blueprint(module.bp)

    socketio.init_app(app)
    from . import sockets  # noqa: F401  (registers Socket.IO handlers)

    _register_hooks(app)
    _register_template_helpers(app)
    _register_error_handlers(app)
    _register_cli(app)

    if app.config.get("AUTO_MIGRATE"):
        with app.app_context():
            try:
                from . import migrations

                migrations.upgrade(app.logger)
            except db.DatabaseError as err:
                app.logger.error("Could not run schema upgrade (is MySQL running?): %s", err)

    return app


def _register_hooks(app):
    @app.before_request
    def guard():
        # Application documents uploaded before the reengineering sit under static/uploads.
        # Only signed-in users may fetch them; announcement images stay public.
        path = request.path
        if path.startswith("/static/uploads/") and not path.startswith("/static/uploads/announcements/"):
            if not session.get("role"):
                return render_template("errors/error.html", code=403, title="Sign in required",
                                       message="Sign in to view uploaded files."), 403
        return security.protect_csrf()

    @app.after_request
    def headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response


def _register_template_helpers(app):
    @app.context_processor
    def inject():
        from .navigation import nav_for

        role = session.get("role")
        return {
            "csrf_token": security.csrf_token,
            "csrf_field": security.csrf_field,
            "current_role": role,
            "current_user_name": session.get("display_name"),
            "nav_items": nav_for(role) if role else [],
            "domain": domain,
            "now": datetime.now(),
        }

    @app.template_filter("course_label")
    def course_label(value):
        return domain.course_label(value)

    @app.template_filter("status_label")
    def status_label(value):
        return domain.STATUS_LABELS.get(value, value or "—")

    @app.template_filter("status_tone")
    def status_tone(value):
        return domain.status_tone(value)

    @app.template_filter("datefmt")
    def datefmt(value, fmt="%b %d, %Y"):
        if not value:
            return "—"
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return value
        return value.strftime(fmt)

    @app.template_filter("timeago")
    def timeago(value):
        if not value:
            return ""
        delta = datetime.now() - value
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return "just now"
        for unit, size in (("year", 31536000), ("month", 2592000), ("week", 604800),
                           ("day", 86400), ("hour", 3600), ("minute", 60)):
            if seconds >= size:
                n = seconds // size
                return f"{n} {unit}{'s' if n != 1 else ''} ago"
        return "just now"

    @app.template_filter("initials")
    def initials(value):
        parts = [p for p in (value or "").split() if p]
        return ("".join(p[0] for p in parts[:2]) or "?").upper()


def _register_error_handlers(app):
    def render_error(code, title, message):
        if security.wants_json():
            return jsonify(error=message), code
        return render_template("errors/error.html", code=code, title=title, message=message), code

    @app.errorhandler(400)
    def bad_request(_):
        return render_error(400, "Bad request", "The request could not be understood.")

    @app.errorhandler(403)
    def forbidden(_):
        return render_error(403, "Access denied", "Your account does not have access to this page.")

    @app.errorhandler(404)
    def not_found(_):
        return render_error(404, "Trail went cold", "We couldn't find the page you were looking for.")

    @app.errorhandler(405)
    def not_allowed(_):
        return render_error(405, "Not allowed", "That action isn't supported here.")

    @app.errorhandler(413)
    def too_large(_):
        limit = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        return render_error(413, "File too large", f"Uploads are limited to {limit} MB in total.")

    @app.errorhandler(db.DatabaseError)
    def database_down(err):
        app.logger.exception("Database error: %s", err)
        return render_error(503, "Service unavailable",
                            "We couldn't reach the database. Please try again in a moment.")

    @app.errorhandler(500)
    def server_error(_):
        return render_error(500, "Something went wrong", "An unexpected error occurred. Please try again.")


def _register_cli(app):
    @app.cli.command("db-upgrade")
    def db_upgrade():
        """Apply additive schema upgrades."""
        from . import migrations

        applied = migrations.upgrade(app.logger)
        print("Applied: " + (", ".join(applied) if applied else "nothing (already up to date)"))
