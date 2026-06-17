"""
Generic Database Migration System with Schema Versioning.

Migrations are stored in migrations/ folder with naming convention:
    001_description.py, 002_description.py, etc.

Each migration file must define:
    - VERSION: int - the migration number
    - DESCRIPTION: str - description of what this migration does
    - migrate(conn): function that performs the migration

The system tracks current schema version in _schema_version table.
"""

import sqlite3
import os
import importlib.util
from pathlib import Path
from flask import current_app


# Target schema version - increment when adding new migrations
TARGET_SCHEMA_VERSION = 1


def _get_db_path():
    """Get SQLite database path from config."""
    database_url = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if database_url.startswith('sqlite:///'):
        return database_url.replace('sqlite:///', '')
    return None


def _ensure_schema_version_table(conn):
    """Create schema version tracking table if it doesn't exist."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS _schema_version (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            version INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO _schema_version (id, version) VALUES (1, 0)
    """)
    conn.commit()


def _get_current_version(conn):
    """Get current schema version from database."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT version FROM _schema_version WHERE id = 1")
        result = cursor.fetchone()
        return result[0] if result else 0
    except sqlite3.OperationalError:
        return 0


def _set_version(conn, version):
    """Update schema version in database."""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE _schema_version SET version = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
        (version,)
    )
    conn.commit()


def _load_migrations():
    """Load all migration files from migrations/ directory."""
    migrations = []

    # Get migrations directory (same level as app/)
    migrations_dir = Path(__file__).parent.parent.parent / 'migrations'

    if not migrations_dir.exists():
        current_app.logger.warning(f"Migrations directory not found: {migrations_dir}")
        return migrations

    # Find all migration files
    for file_path in sorted(migrations_dir.glob('[0-9]*_*.py')):
        try:
            # Extract version number from filename (001_description.py -> 1)
            version_str = file_path.stem.split('_')[0]
            version = int(version_str)

            # Load the migration module
            spec = importlib.util.spec_from_file_location(f"migration_{version}", file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Validate required attributes
            if hasattr(module, 'migrate') and callable(module.migrate):
                migrations.append({
                    'version': version,
                    'file': file_path.name,
                    'migrate': module.migrate,
                    'description': getattr(module, 'DESCRIPTION', 'No description')
                })
            else:
                current_app.logger.warning(f"Migration {file_path.name} missing 'migrate' function")

        except (ValueError, ImportError) as e:
            current_app.logger.warning(f"Failed to load migration {file_path.name}: {e}")

    # Sort by version
    migrations.sort(key=lambda m: m['version'])
    return migrations


def check_and_run_migrations():
    """
    Check for pending migrations and run them automatically.
    Called on application startup.
    """
    db_path = _get_db_path()
    if not db_path:
        current_app.logger.info("Non-SQLite database detected, skipping migrations")
        return

    if not os.path.exists(db_path):
        current_app.logger.info("Database does not exist yet, no migrations needed")
        return

    try:
        conn = sqlite3.connect(db_path)

        # Ensure version tracking table exists
        _ensure_schema_version_table(conn)

        # Get current version
        current_version = _get_current_version(conn)

        # Load available migrations
        migrations = _load_migrations()

        # Find pending migrations
        pending = [m for m in migrations if m['version'] > current_version]

        if not pending:
            current_app.logger.debug(f"Database schema is up to date (version {current_version})")
            conn.close()
            return

        # Run pending migrations in order
        applied = []
        for migration in pending:
            try:
                current_app.logger.info(f"Running migration {migration['version']}: {migration['description']}")
                migration['migrate'](conn)
                _set_version(conn, migration['version'])
                applied.append(migration['version'])
            except Exception as e:
                current_app.logger.error(f"Migration {migration['version']} failed: {e}")
                # Stop here - don't continue with later migrations
                break

        if applied:
            current_app.logger.info(f"Applied migrations: {applied}. Now at version {_get_current_version(conn)}")

        conn.close()

    except sqlite3.Error as e:
        current_app.logger.error(f"Database migration error: {e}")
