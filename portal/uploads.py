"""Validated file storage for application documents and announcement images."""
import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

DOCUMENT_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

# Leading bytes for the formats we accept, so a renamed executable is rejected.
_SIGNATURES = {
    "pdf": [b"%PDF"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "gif": [b"GIF87a", b"GIF89a"],
    "webp": [b"RIFF"],
}


class UploadError(ValueError):
    pass


def _extension(filename):
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""


def _check(file_storage, allowed, label):
    if not file_storage or not file_storage.filename:
        raise UploadError(f"{label} is required.")
    ext = _extension(file_storage.filename)
    if ext not in allowed:
        raise UploadError(f"{label} must be one of: {', '.join(sorted(allowed)).upper()}.")
    head = file_storage.stream.read(16)
    file_storage.stream.seek(0)
    if not any(head.startswith(sig) for sig in _SIGNATURES[ext]):
        raise UploadError(f"{label} does not look like a valid .{ext} file.")
    if ext == "webp" and head[8:12] != b"WEBP":
        raise UploadError(f"{label} does not look like a valid .webp file.")
    return ext


def _unique_name(original, ext, suffix):
    stem = secure_filename(original.rsplit(".", 1)[0])[:40] or "file"
    return f"{uuid.uuid4().hex}_{suffix}_{stem}.{ext}"


def save_document(file_storage, label, suffix):
    """Store a COG/COE in the private folder; returns the stored filename."""
    ext = _check(file_storage, DOCUMENT_EXTENSIONS, label)
    folder = current_app.config["PRIVATE_UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    name = _unique_name(file_storage.filename, ext, suffix)
    file_storage.save(os.path.join(folder, name))
    return name


def document_path(filename):
    """Locate a stored document: new private folder first, then the legacy public folder."""
    if not filename:
        return None
    safe = os.path.basename(filename)
    for folder in (current_app.config["PRIVATE_UPLOAD_FOLDER"], current_app.config["LEGACY_UPLOAD_FOLDER"]):
        path = os.path.join(folder, safe)
        if os.path.isfile(path):
            return path
    return None


def save_announcement_image(file_storage):
    """Store an announcement image; returns the image_path value stored in the database."""
    ext = _check(file_storage, IMAGE_EXTENSIONS, "Image")
    folder = current_app.config["ANNOUNCEMENT_UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    name = _unique_name(file_storage.filename, ext, "ann")
    file_storage.save(os.path.join(folder, name))
    # Same "static/..." shape the existing rows use.
    return f"static/uploads/announcements/{name}"


def delete_announcement_image(image_path):
    if not image_path or not image_path.startswith("static/uploads/"):
        return
    root = os.path.abspath(os.path.join(current_app.root_path, os.pardir))
    path = os.path.abspath(os.path.join(root, *image_path.split("/")))
    uploads_root = os.path.abspath(current_app.config["LEGACY_UPLOAD_FOLDER"])
    if path.startswith(uploads_root + os.sep) and os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            current_app.logger.warning("Could not delete announcement image %s", path)
