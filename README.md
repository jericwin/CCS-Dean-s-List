# CCS Dean's List — Student Portal

The CCS Dean's Lister Student Portal is the online platform of the CCS Student Body Organization (SBO).
Students apply for the Dean's List, track their application through SBO and Dean review, receive
notifications, chat with SBO support and send feedback.

## Roles

| Role | Sign-in | Can |
|---|---|---|
| Student | `/login` (self sign-up at `/signup`) | Apply (GWA + COG + COE), follow progress, notifications, chat, feedback, change password |
| SBO admin | `/adminlogin` | Review/endorse applications, rankings + Excel/PDF export, send to Dean, announcements, chat, feedback replies |
| Dean | `/dean/login` | Approve or reject SBO-endorsed applications; dashboard |

Workflow: **Pending → (SBO) Approved/Rejected → For Dean Review → (Dean) Dean Approved/Dean Rejected**.
Final Dean decisions are locked for the SBO.

## Stack

Flask 3 · MySQL/MariaDB (mysql-connector, pooled) · Flask-SocketIO (live chat & notifications) ·
Jinja templates with a shared design system (`static/css/fox.css`, `static/js/app.js`) · Chart.js.

```
app.py                 entry point (python app.py)
wsgi.py                production entry point
portal/
  __init__.py          app factory, error pages, security headers
  config.py            settings from environment / .env
  db.py                connection pool + query helpers
  security.py          auth decorators, password hashing, CSRF, login throttling
  migrations.py        additive, idempotent schema upgrades
  domain.py            courses, statuses, validation helpers
  services.py          notifications and shared queries
  uploads.py           validated file storage
  exports.py           ranking Excel/PDF
  sockets.py           Socket.IO events
  blueprints/          public, student, admin, dean, chat, files
templates/             layouts/, partials/, auth/, public/, student/, admin/, dean/, errors/
tests/                 pytest integration tests (use a throwaway *_test database)
```

## Setup

1. Start MySQL/MariaDB (e.g. XAMPP) and import the data if the database doesn't exist yet:
   ```
   mysql -u root -e "CREATE DATABASE student_portal CHARACTER SET utf8mb4"
   mysql -u root student_portal < student_portal-final.sql
   ```
2. `pip install -r requirements.txt`
3. `copy .env.example .env` and set `SECRET_KEY` and the DB credentials.
4. `python app.py` → http://127.0.0.1:5000

Schema upgrades run automatically on startup (`AUTO_MIGRATE=true`) or manually with
`flask --app app db-upgrade`. They only **add** columns/indexes (`deans_list_applications.student_id`,
`student_notification.is_read` / `app_status`, lookup indexes) and backfill them; no data is removed.

## Tests

```
python -m pytest -q
```
Requires MySQL running. Tests build and drop a separate `student_portal_test` database from
`student_portal-final.sql`; the real database is never touched.

## Production notes

* Set `APP_ENV=production` (requires `SECRET_KEY`, enables secure cookies, disables debug). Serve over HTTPS.
* Socket.IO needs a single worker (or a message queue): `gunicorn --worker-class gthread --threads 50 -w 1 wsgi:app` on Linux.
* New COG/COE uploads are stored privately in `instance/uploads/applications` and served only through
  `/view_file/<id>/<cog|coe>` to the owning student, the SBO and the Dean. Files uploaded before the
  reengineering remain in `static/uploads` and are only served to signed-in users.
* PDF export uses the official `DL.docx` template through Microsoft Word when available (Windows),
  otherwise a ReportLab layout. Force one with `PDF_EXPORT_ENGINE=docx|reportlab`.
