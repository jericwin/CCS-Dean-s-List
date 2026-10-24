"""Domain vocabulary shared by routes, templates and validation."""
from datetime import date
from decimal import Decimal, InvalidOperation

# Course/section values match what is already stored in deans_list_applications.course.
COURSES = [
    ("BSIT", [
        ("bsit_1a", "BSIT 1A"), ("bsit_1b", "BSIT 1B"), ("bsit_1c", "BSIT 1C"), ("bsit_1d", "BSIT 1D"),
        ("bsit_2a", "BSIT 2A"), ("bsit_2b", "BSIT 2B"), ("bsit_2c", "BSIT 2C"), ("bsit_2d", "BSIT 2D"),
        ("bsit_3a", "BSIT 3A WMAD"), ("bsit_3b", "BSIT 3B SMP"), ("bsit_3c", "BSIT 3C AMG"), ("bsit_3d", "BSIT 3D NETAD"),
        ("bsit_4a", "BSIT 4A WMAD"), ("bsit_4b", "BSIT 4B SMP"), ("bsit_4c", "BSIT 4C AMG"), ("bsit_4d", "BSIT 4D NETAD"),
    ]),
    ("BSIS", [
        ("bsis_1a", "BSIS 1A"), ("bsis_1b", "BSIS 1B"), ("bsis_2a", "BSIS 2A"), ("bsis_2b", "BSIS 2B"),
        ("bsis_3a", "BSIS 3A"), ("bsis_3b", "BSIS 3B"), ("bsis_4a", "BSIS 4A"), ("bsis_4b", "BSIS 4B"),
    ]),
    ("BSCS", [
        ("bscs_1a", "BSCS 1A"), ("bscs_1b", "BSCS 1B"), ("bscs_2a", "BSCS 2A"), ("bscs_2b", "BSCS 2B"),
        ("bscs_3a", "BSCS 3A"), ("bscs_3b", "BSCS 3B"), ("bscs_4a", "BSCS 4A"), ("bscs_4b", "BSCS 4B"),
    ]),
]
COURSE_LABELS = {value: label for _, group in COURSES for value, label in group}
PROGRAMS = [program for program, _ in COURSES]

SEMESTERS = [("1st", "1st Semester"), ("2nd", "2nd Semester")]
SEMESTER_VALUES = {value for value, _ in SEMESTERS}

# Application workflow: SBO (admin) review first, then the Dean.
STATUS_PENDING = "Pending"
STATUS_APPROVED = "Approved"
STATUS_REJECTED = "Rejected"
STATUS_DEAN_REVIEW = "For Dean Review"
STATUS_DEAN_APPROVED = "Dean Approved"
STATUS_DEAN_REJECTED = "Dean Rejected"

ALL_STATUSES = [
    STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED,
    STATUS_DEAN_REVIEW, STATUS_DEAN_APPROVED, STATUS_DEAN_REJECTED,
]
STATUS_LABELS = {
    STATUS_PENDING: "SBO Pending",
    STATUS_APPROVED: "SBO Approved",
    STATUS_REJECTED: "SBO Rejected",
    STATUS_DEAN_REVIEW: "For Dean Review",
    STATUS_DEAN_APPROVED: "Dean Approved",
    STATUS_DEAN_REJECTED: "Dean Rejected",
}
# Statuses the SBO admin may set. Final dean decisions are locked for the admin.
ADMIN_SETTABLE_STATUSES = [STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_DEAN_REVIEW]
DEAN_STATUSES = [STATUS_DEAN_REVIEW, STATUS_DEAN_APPROVED, STATUS_DEAN_REJECTED]
DEAN_FINAL_STATUSES = {STATUS_DEAN_APPROVED, STATUS_DEAN_REJECTED}

FEEDBACK_POSITIONS = [
    ("President", "President"),
    ("VP", "Vice President"),
    ("Secretary", "Secretary"),
    ("Whole Organization", "Whole Organization"),
]
FEEDBACK_POSITION_VALUES = {value for value, _ in FEEDBACK_POSITIONS}

GWA_MIN = Decimal("1.00")
GWA_MAX = Decimal("5.00")


def course_label(value):
    if not value:
        return "—"
    return COURSE_LABELS.get(value, value.replace("_", " ").upper())


def course_program(value):
    return (value or "").split("_", 1)[0].upper()


def course_section(value):
    parts = (value or "").split("_", 1)
    return parts[1].replace("_", " ").upper() if len(parts) > 1 else ""


def status_tone(status):
    """Semantic tone used for badge styling."""
    if status in (STATUS_APPROVED, STATUS_DEAN_APPROVED):
        return "success"
    if status in (STATUS_REJECTED, STATUS_DEAN_REJECTED):
        return "danger"
    if status == STATUS_DEAN_REVIEW:
        return "info"
    return "warning"


def current_academic_year(today=None):
    today = today or date.today()
    start = today.year if today.month >= 8 else today.year - 1
    return f"{start}-{start + 1}"


def academic_years(first_year, extra=()):
    """Academic years from `first_year` to next year, plus any values already in the data."""
    current_start = int(current_academic_year().split("-")[0])
    years = {f"{y}-{y + 1}" for y in range(min(first_year, current_start), current_start + 2)}
    years.update(y for y in extra if y)
    return sorted(years)


def parse_gwa(raw):
    """Return a Decimal GWA rounded to 2 places, or None when invalid."""
    try:
        value = Decimal(str(raw).strip()).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None
    if value < GWA_MIN or value > GWA_MAX:
        return None
    return value


def first_name_of(full_name):
    full_name = (full_name or "").strip()
    return full_name.split()[0].capitalize() if full_name else "Student"
