"""Access-checked delivery of application documents."""
from flask import Blueprint, abort, send_file, session

from .. import services
from ..security import ROLE_ADMIN, ROLE_DEAN, ROLE_STUDENT, login_required
from ..uploads import document_path

bp = Blueprint("files", __name__)

# "registration"/"grade" are the names the previous templates used.
_KINDS = {"cog": "cog_filename", "coe": "coe_filename", "registration": "cog_filename", "grade": "coe_filename"}


@bp.route("/view_file/<int:application_id>/<string:file_type>")
@login_required(ROLE_STUDENT, ROLE_ADMIN, ROLE_DEAN)
def view_file(application_id, file_type):
    column = _KINDS.get(file_type)
    if not column:
        abort(404)
    record = services.application_for(application_id)
    if not record:
        abort(404)
    if session["role"] == ROLE_STUDENT:
        owns = record["student_id"] == session["user_id"] or (
            record["student_id"] is None and record["full_name"] == session.get("full_name")
        )
        if not owns:
            abort(403)
    path = document_path(record[column])
    if not path:
        abort(404)
    return send_file(path, as_attachment=False, max_age=0)
