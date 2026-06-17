"""
Migration: Add betting phase locks table
Created: 2025-01-17
"""

import sqlite3
import os


def migrate(description=None):
    """Add betting_phase_locks table."""
    db_path = os.environ.get('DATABASE_PATH', '/app/data/familybet.db')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='betting_phase_locks'")
    if cursor.fetchone():
        print("Table betting_phase_locks already exists, skipping creation")
        conn.close()
        return True

    # Create betting_phase_locks table
    cursor.execute('''
        CREATE TABLE betting_phase_locks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phase_name VARCHAR(50) UNIQUE NOT NULL,
            is_locked BOOLEAN DEFAULT 0,
            locked_at DATETIME,
            locked_by INTEGER,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Insert default unlocked records for all phases
    phases = [
        'gruppenphase',
        'sechzehntelfinale',
        'achtelfinale',
        'viertelfinale',
        'halbfinale',
        'finale'
    ]

    for phase in phases:
        cursor.execute('''
            INSERT INTO betting_phase_locks (phase_name, is_locked)
            VALUES (?, 0)
        ''', (phase,))

    conn.commit()
    conn.close()

    print("✅ Created betting_phase_locks table with default unlocked phases")
    return True


def rollback(description=None):
    """Remove betting_phase_locks table."""
    db_path = os.environ.get('DATABASE_PATH', '/app/data/familybet.db')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('DROP TABLE IF EXISTS betting_phase_locks')

    conn.commit()
    conn.close()

    print("✅ Dropped betting_phase_locks table")
    return True


if __name__ == '__main__':
    migrate()
