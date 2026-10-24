"""Entry point: `python app.py` (development) or `flask --app app run`.

The application itself lives in the `portal` package.
"""
import os

from dotenv import load_dotenv

load_dotenv()

from portal import create_app  # noqa: E402  (load .env before reading config)
from portal.extensions import socketio  # noqa: E402

app = create_app()

if __name__ == "__main__":
    socketio.run(
        app,
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=app.config["DEBUG"],
        allow_unsafe_werkzeug=True,
    )
