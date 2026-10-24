"""Production entry point, e.g. on Linux:
    gunicorn --worker-class gthread --threads 50 -w 1 wsgi:app
(Socket.IO needs a single worker unless a message queue is configured.)
"""
from app import app  # noqa: F401
