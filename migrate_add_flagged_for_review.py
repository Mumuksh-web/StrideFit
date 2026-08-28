from sqlalchemy import text

from database import engine


with engine.connect() as conn:
    result = conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = 'audit_logs' "
            "AND column_name = 'flagged_for_review'"
        )
    )
    column_exists = result.scalar() > 0

    if column_exists:
        print("Column flagged_for_review already exists on audit_logs — nothing to do.")
    else:
        conn.execute(text("ALTER TABLE audit_logs ADD COLUMN flagged_for_review BOOLEAN NOT NULL DEFAULT FALSE"))
        conn.commit()
        print("Added flagged_for_review column to audit_logs.")
