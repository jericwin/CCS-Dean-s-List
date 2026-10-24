"""Landing page and sign-in/out for all three roles."""
import re

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from .. import db
from ..domain import first_name_of
from ..security import (
    HOME_ENDPOINTS, ROLE_ADMIN, ROLE_DEAN, ROLE_STUDENT, hash_password, is_hashed,
    password_problem, safe_next_url, start_session, throttle, verify_password,
)

bp = Blueprint("public", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _home_if_signed_in():
    role = session.get("role")
    if role in HOME_ENDPOINTS:
        return redirect(url_for(HOME_ENDPOINTS[role]))
    return None


def _locked(scope, identifier):
    wait = throttle.blocked_for(scope, identifier)
    if wait:
        minutes = max(1, round(wait / 60))
        flash(f"Too many failed attempts. Try again in about {minutes} minute{'s' if minutes != 1 else ''}.", "danger")
        return True
    return False


@bp.route("/")
def index():
    return render_template("public/index.html")


@bp.route("/dashboard")
def dashboard():
    return _home_if_signed_in() or redirect(url_for("public.login"))


# --------------------------------------------------------------------------- students
@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return _home_if_signed_in() or render_template("auth/signup.html", form={})

    form = {
        "fullname": " ".join(request.form.get("fullname", "").split()),
        "email": request.form.get("email", "").strip().lower(),
    }
    password = request.form.get("password", "")
    confirm = request.form.get("confirm_password")
    errors = {}
    if len(form["fullname"]) < 3 or len(form["fullname"]) > 120:
        errors["fullname"] = "Enter your full name (3–120 characters)."
    if not EMAIL_RE.match(form["email"]) or len(form["email"]) > 255:
        errors["email"] = "Enter a valid email address."
    problem = password_problem(password, confirm)
    if problem:
        errors["password"] = problem
    if errors:
        return render_template("auth/signup.html", form=form, errors=errors), 422

    try:
        db.execute(
            "INSERT INTO users (fullname, email, password_hash, college, role) VALUES (%s, %s, %s, %s, 'student')",
            (form["fullname"], form["email"], hash_password(password), "College of Computer Studies"),
        )
    except db.IntegrityError:
        errors["email"] = "That email address is already registered."
        return render_template("auth/signup.html", form=form, errors=errors), 409

    flash("Your account is ready. Sign in to continue.", "success")
    return redirect(url_for("public.login", email=form["email"]))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return _home_if_signed_in() or render_template("auth/login.html", email=request.args.get("email", ""))

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    if _locked("student", email):
        return render_template("auth/login.html", email=email), 429

    user = db.fetch_one("SELECT * FROM users WHERE email = %s AND role = 'student'", (email,))
    if not user or not verify_password(user["password_hash"], password):
        throttle.fail("student", email)
        flash("Invalid email or password.", "danger")
        return render_template("auth/login.html", email=email), 401

    throttle.reset("student", email)
    start_session(
        ROLE_STUDENT, user["id"], user["fullname"],
        full_name=user["fullname"], first_name=first_name_of(user["fullname"]), email=user["email"],
    )
    return redirect(safe_next_url(url_for("student.dashboard")))


@bp.route("/logout")
def logout():
    role = session.get("role")
    session.clear()
    flash("You have been signed out.", "info")
    if role == ROLE_ADMIN:
        return redirect(url_for("public.admin_login"))
    if role == ROLE_DEAN:
        return redirect(url_for("public.dean_login"))
    return redirect(url_for("public.login"))


# --------------------------------------------------------------------------- SBO admin
@bp.route("/adminlogin", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return _home_if_signed_in() or render_template("auth/admin_login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if _locked("admin", username):
        return render_template("auth/admin_login.html", username=username), 429

    admin = db.fetch_one("SELECT * FROM admin WHERE username = %s", (username,))
    if not admin or not verify_password(admin["password"], password):
        throttle.fail("admin", username)
        current_app.logger.warning("Failed admin login for %r from %s", username, request.remote_addr)
        flash("Invalid username or password.", "danger")
        return render_template("auth/admin_login.html", username=username), 401

    if not is_hashed(admin["password"]):
        # Upgrade the legacy plaintext password to a hash transparently.
        db.execute("UPDATE admin SET password = %s WHERE id = %s", (hash_password(password), admin["id"]))
        current_app.logger.info("Upgraded admin %s password to a secure hash.", admin["username"])

    throttle.reset("admin", username)
    start_session(ROLE_ADMIN, admin["id"], admin["username"].capitalize(),
                  admin=admin["username"], username=admin["username"], first_name=admin["username"])
    flash(f"Welcome back, {admin['username']}.", "success")
    return redirect(safe_next_url(url_for("admin.dashboard")))


@bp.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("public.admin_login"))


# --------------------------------------------------------------------------- dean
@bp.route("/dean/login", methods=["GET", "POST"])
def dean_login():
    if request.method == "GET":
        return _home_if_signed_in() or render_template("auth/dean_login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    if _locked("dean", email):
        return render_template("auth/dean_login.html", email=email), 429

    dean = db.fetch_one("SELECT * FROM deans WHERE email = %s", (email,))
    if not dean or not verify_password(dean["password_hash"], password):
        throttle.fail("dean", email)
        flash("Invalid email or password.", "danger")
        return render_template("auth/dean_login.html", email=email), 401

    throttle.reset("dean", email)
    start_session(ROLE_DEAN, dean["id"], dean["full_name"], dean=dean["email"], first_name=dean["full_name"])
    flash(f"Welcome, {dean['full_name']}.", "success")
    return redirect(safe_next_url(url_for("dean.dashboard")))


@bp.route("/dean/logout")
def dean_logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("public.dean_login"))
