"""Add SMTP fields to email_settings table

Revision ID: 013
Revises: 012
Create Date: 2026-06-18
"""

revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def migrate(conn):
    existing = {row[1] for row in conn.execute("PRAGMA table_info(email_settings)")}

    columns = [
        ("mail_server",   "VARCHAR(200)"),
        ("mail_port",     "INTEGER"),
        ("mail_use_tls",  "BOOLEAN DEFAULT 1"),
        ("mail_use_ssl",  "BOOLEAN DEFAULT 0"),
        ("mail_username", "VARCHAR(200)"),
        ("mail_password", "VARCHAR(200)"),
        ("mail_sender",   "VARCHAR(200)"),
    ]

    for col, col_type in columns:
        if col not in existing:
            conn.execute(f"ALTER TABLE email_settings ADD COLUMN {col} {col_type}")
