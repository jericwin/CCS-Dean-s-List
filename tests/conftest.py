"""Integration-test fixtures.

Tests run against a throwaway MySQL database (`<DB_NAME>_test`) rebuilt from
student_portal-final.sql, so the real data is never touched. MySQL must be running.
"""
import io
import os
import re
import sys

import mysql.connector
import pytest
from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, ROOT)
load_dotenv(os.path.join(ROOT, ".env"))

from portal import create_app  # noqa: E402
from portal.security import hash_password  # noqa: E402

TEST_DB = os.environ.get("TEST_DB_NAME", os.environ.get("DB_NAME", "student_portal") + "_test")
assert TEST_DB.endswith("_test"), "Refusing to run tests against a non-test database."
PASSWORD = "FoxTest#2026"

# Minimal valid file payloads (magic bytes are checked by the upload validator).
PDF_BYTES = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def _server():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"), port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "root"), password=os.environ.get("DB_PASSWORD", ""),
    )


def _statements(sql):
    """Split a phpMyAdmin dump into statements (no semicolons appear inside its string data)."""
    sql = re.sub(r"^--.*$", "", sql, flags=re.M)
    for stmt in sql.split(";\n"):
        stmt = stmt.strip()
        if stmt and not stmt.startswith("/*!"):
            yield stmt


@pytest.fixture(scope="session")
def database():
    conn = _server()
    cur = conn.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS `{TEST_DB}`")
    cur.execute(f"CREATE DATABASE `{TEST_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci")
    cur.execute(f"USE `{TEST_DB}`")
    with open(os.path.join(ROOT, "student_portal-final.sql"), encoding="utf-8") as fh:
        for stmt in _statements(fh.read()):
            cur.execute(stmt)
    conn.commit()
    # Known passwords for the seeded accounts (test database only).
    hashed = hash_password(PASSWORD)
    cur.execute("UPDATE users SET password_hash = %s WHERE role = 'student'", (hashed,))
    cur.execute("UPDATE deans SET password_hash = %s", (hashed,))
    conn.commit()
    cur.close()
    conn.close()
    yield TEST_DB
    conn = _server()
    conn.cursor().execute(f"DROP DATABASE IF EXISTS `{TEST_DB}`")
    conn.close()


@pytest.fixture(scope="session")
def app(database, tmp_path_factory):
    uploads = tmp_path_factory.mktemp("uploads")
    application = create_app({
        "TESTING": True,
        "DB_NAME": database,
        "SECRET_KEY": "test-secret",
        "CSRF_ENABLED": False,
        "AUTO_MIGRATE": True,
        "PRIVATE_UPLOAD_FOLDER": str(uploads / "applications"),
        "ANNOUNCEMENT_UPLOAD_FOLDER": str(uploads / "announcements"),
        "PDF_EXPORT_ENGINE": "reportlab",
        "LOGIN_MAX_ATTEMPTS": 50,
    })
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    from portal import db as portal_db

    class Helper:
        def all(self, sql, params=()):
            with app.app_context():
                return portal_db.fetch_all(sql, params)

        def one(self, sql, params=()):
            with app.app_context():
                return portal_db.fetch_one(sql, params)

        def run(self, sql, params=()):
            with app.app_context():
                return portal_db.execute(sql, params)

    return Helper()


def login_student(client, email="lux@gmail.com", password=PASSWORD):
    return client.post("/login", data={"email": email, "password": password})


def login_admin(client, username="admin", password="password"):
    return client.post("/adminlogin", data={"username": username, "password": password})


def login_dean(client, email="dean@gmail.com", password=PASSWORD):
    return client.post("/dean/login", data={"email": email, "password": password})


def file_field(data=PDF_BYTES, name="doc.pdf"):
    return (io.BytesIO(data), name)
