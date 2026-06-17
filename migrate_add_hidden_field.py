"""
Migration script to add is_hidden_from_leaderboard column to users table.

Run this script after deploying the code changes:
    python migrate_add_hidden_field.py
"""

import sqlite3
import os

# Path to the database
db_path = os.path.join(os.path.dirname(__file__), 'instance', 'familybet.db')

def migrate():
    """Add the is_hidden_from_leaderboard column to the users table."""
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        print("The migration will be applied automatically when the app starts with SQLAlchemy.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'is_hidden_from_leaderboard' in columns:
            print("Column 'is_hidden_from_leaderboard' already exists. Migration not needed.")
            return

        # Add the new column with default value False (0)
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN is_hidden_from_leaderboard BOOLEAN DEFAULT 0
        """)

        conn.commit()
        print("Successfully added 'is_hidden_from_leaderboard' column to users table.")
        print("All existing users are set to visible (is_hidden_from_leaderboard = False).")

    except sqlite3.Error as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
