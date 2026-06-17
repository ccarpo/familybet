# Database Migrations

This folder contains database migration scripts for the FamilyBet application.

## How it works

- Migrations are automatically applied on application startup
- Each migration runs only once (tracked in `_schema_version` table)
- Migrations run in order based on their version number
- Failed migrations stop the chain (subsequent migrations won't run)

## Creating a new migration

1. Copy `__template__.py` to a new file with naming pattern:
   ```
   <version>_<description>.py
   ```
   Example: `002_add_match_status.py`, `003_create_notifications_table.py`

2. Update the variables in the new file:
   ```python
   VERSION = 2  # Must be unique and sequential
   DESCRIPTION = "Add match status column"
   ```

3. Implement the `migrate(conn)` function with your SQL changes

4. Deploy - migrations run automatically on container restart

## Example migration

```python
"""
Migration 002: Add status column to matches table
"""

VERSION = 2
DESCRIPTION = "Add status column to matches table"


def migrate(conn):
    cursor = conn.cursor()
    
    # Add new column
    cursor.execute("""
        ALTER TABLE matches
        ADD COLUMN status TEXT DEFAULT 'scheduled'
    """)
    
    # Update existing data
    cursor.execute("""
        UPDATE matches SET status = 'finished' WHERE is_finished = 1
    """)
    
    conn.commit()
```

## Checking migration status

The app logs migration activity on startup. Check logs with:
```bash
docker logs familybet
```

You'll see messages like:
```
Database schema is up to date (version 1)
# or
Running migration 2: Add match status column
Applied migrations: [2]. Now at version 2
```

## Manual migration (if needed)

Normally migrations run automatically, but if you need to run manually:

```bash
# Inside the container
docker exec -it familybet python -c "
from app.services.migrations import check_and_run_migrations
from app import create_app
app = create_app()
with app.app_context():
    check_and_run_migrations()
"
```

## Troubleshooting

**Migration fails:**
- Check the app logs for the error message
- Fix the migration file
- Restart the container (migrations are idempotent - already-applied ones are skipped)

**Need to rollback:**
- SQLite doesn't support `ALTER TABLE DROP COLUMN`
- Create a new migration to undo the change (e.g., remove data, ignore column in code)
- For major issues, restore from backup and redeploy
