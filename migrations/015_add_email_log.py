"""Add email_log table to prevent duplicate sends

Revision ID: 015
Revises: 014
Create Date: 2026-06-18
"""

revision = '015'
down_revision = '014'


def migrate(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS email_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_type VARCHAR(50) NOT NULL,
            user_id INTEGER REFERENCES users(id),
            ref_id VARCHAR(100),
            sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS ix_email_log_lookup
        ON email_log (email_type, user_id, ref_id)
    """)
