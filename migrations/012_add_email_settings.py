"""Add email_settings table

Revision ID: 012
Revises: 011
Create Date: 2026-06-18
"""

revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def migrate(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS email_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enabled BOOLEAN DEFAULT 0,
            mail_server VARCHAR(200),
            mail_port INTEGER,
            mail_use_tls BOOLEAN DEFAULT 1,
            mail_use_ssl BOOLEAN DEFAULT 0,
            mail_username VARCHAR(200),
            mail_password VARCHAR(200),
            mail_sender VARCHAR(200),
            send_magic_link BOOLEAN DEFAULT 1,
            send_welcome BOOLEAN DEFAULT 1,
            send_deadline_24h BOOLEAN DEFAULT 1,
            send_deadline_2h BOOLEAN DEFAULT 1,
            send_match_result BOOLEAN DEFAULT 1,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
