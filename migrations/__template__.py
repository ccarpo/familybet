"""
Migration XXX: <Description>

<Detailed description of what this migration does>
"""

VERSION = 0  # TODO: Replace with migration number (e.g., 2, 3, 4...)
DESCRIPTION = "<Brief description>"


def migrate(conn):
    """Execute migration."""
    cursor = conn.cursor()

    # Example: Add new column
    # cursor.execute("""
    #     ALTER TABLE table_name
    #     ADD COLUMN new_column_name DATA_TYPE DEFAULT default_value
    # """)

    # Example: Create new table
    # cursor.execute("""
    #     CREATE TABLE IF NOT EXISTS new_table (
    #         id INTEGER PRIMARY KEY,
    #         name TEXT NOT NULL,
    #         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    #     )
    # """)

    # Example: Update existing data
    # cursor.execute("""
    #     UPDATE table_name SET column = value WHERE condition
    # """)

    conn.commit()
