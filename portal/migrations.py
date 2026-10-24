"""Idempotent, additive schema upgrades. Nothing here drops or rewrites existing data.

Run automatically at startup when AUTO_MIGRATE is on, or manually with:
    flask --app app db-upgrade
"""
from . import db


def _column_exists(cur, table, column):
    cur.execute(
        "SELECT COUNT(*) AS n FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
        (table, column),
    )
    return cur.fetchone()["n"] > 0


def _index_exists(cur, table, index):
    cur.execute(
        "SELECT COUNT(*) AS n FROM information_schema.STATISTICS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND INDEX_NAME = %s",
        (table, index),
    )
    return cur.fetchone()["n"] > 0


def upgrade(logger=None):
    applied = []
    with db.transaction() as cur:
        # 1. Link applications to the student account instead of matching on full name.
        if not _column_exists(cur, "deans_list_applications", "student_id"):
            cur.execute("ALTER TABLE deans_list_applications ADD COLUMN student_id INT(11) NULL AFTER id")
            applied.append("deans_list_applications.student_id")
        cur.execute(
            """
            UPDATE deans_list_applications dla
            JOIN users u ON u.fullname = dla.full_name AND u.role = 'student'
            SET dla.student_id = u.id
            WHERE dla.student_id IS NULL
            """
        )
        for name, columns in (
            ("idx_dla_student", "student_id"),
            ("idx_dla_status", "status"),
            ("idx_dla_term", "academic_year, semester"),
        ):
            if not _index_exists(cur, "deans_list_applications", name):
                cur.execute(f"ALTER TABLE deans_list_applications ADD INDEX {name} ({columns})")
                applied.append(f"index {name}")

        # 2. Notifications: a real read flag plus the application status the message refers to.
        #    The legacy `status` column is an enum of pending/read/unread that the old code
        #    filled with application statuses (stored as ''), so it is left untouched.
        if not _column_exists(cur, "student_notification", "is_read"):
            cur.execute("ALTER TABLE student_notification ADD COLUMN is_read TINYINT(1) NOT NULL DEFAULT 0")
            applied.append("student_notification.is_read")
        if not _column_exists(cur, "student_notification", "app_status"):
            cur.execute("ALTER TABLE student_notification ADD COLUMN app_status VARCHAR(30) NULL")
            cur.execute(
                """
                UPDATE student_notification
                SET app_status = NULLIF(TRIM(REPLACE(
                    SUBSTRING_INDEX(SUBSTRING_INDEX(message, 'updated to ', -1), '.', 1),
                    ' by the Dean', '')), 'None')
                WHERE message LIKE '%updated to %'
                """
            )
            cur.execute("UPDATE student_notification SET message = REPLACE(message, ' <br>', '')")
            applied.append("student_notification.app_status")

        # 3. Chat lookups by conversation.
        if not _index_exists(cur, "chat_messages", "idx_chat_conversation"):
            cur.execute("ALTER TABLE chat_messages ADD INDEX idx_chat_conversation (sender_id, receiver_id, timestamp)")
            applied.append("index idx_chat_conversation")

    if logger and applied:
        logger.info("Schema upgraded: %s", ", ".join(applied))
    return applied
