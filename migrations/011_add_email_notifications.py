"""Add email_notifications to users

Revision ID: 011
Revises: 010
Create Date: 2026-06-18
"""

revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def migrate(conn):
    conn.execute("ALTER TABLE users ADD COLUMN email_notifications BOOLEAN DEFAULT 1")
