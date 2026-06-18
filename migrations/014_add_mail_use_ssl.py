"""Add mail_use_ssl to email_settings

Revision ID: 014
Revises: 013
Create Date: 2026-06-18
"""

revision = '014'
down_revision = '013'


def migrate(conn):
    existing = {row[1] for row in conn.execute("PRAGMA table_info(email_settings)")}
    if 'mail_use_ssl' not in existing:
        conn.execute("ALTER TABLE email_settings ADD COLUMN mail_use_ssl BOOLEAN DEFAULT 0")
