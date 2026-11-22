
"""SQLite database connection and schema management."""

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_DATABASE = (
    PROJECT_ROOT / "data" / "database" / "opportunities.db"
)


TABLE_COLUMNS = {
    "field": "TEXT",
    "location": "TEXT",
    "work_mode": "TEXT",
    "description": "TEXT",
    "evidence": "TEXT",
    "requirements": "TEXT",
    "preferred_skills": "TEXT",
    "compensation": "TEXT",
    "duration": "TEXT",
    "start_date": "TEXT",
    "deadline": "TEXT",
    "start_date_text": "TEXT",
    "deadline_text": "TEXT",
    "eligibility": "TEXT",
    "application_url": "TEXT",
    "related_source_urls": "TEXT",
    "date_discovered": "TEXT",
    "last_verified": "TEXT",
    "status": "TEXT",
    "created_at": "TEXT",
    "updated_at": "TEXT",
}


def get_connection(
    database_path: Path = DEFAULT_DATABASE
) -> sqlite3.Connection:
    """Create a connection to the opportunity database."""

    database_path = Path(database_path)
    database_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")

    return connection


def migrate_database(
    connection: sqlite3.Connection
) -> None:
    """Add missing columns to an existing opportunities table."""

    existing_columns = {
        column["name"]
        for column in connection.execute(
            "PRAGMA table_info(opportunities)"
        ).fetchall()
    }

    for column_name, column_type in TABLE_COLUMNS.items():
        if column_name not in existing_columns:
            connection.execute(
                f"ALTER TABLE opportunities "
                f"ADD COLUMN {column_name} {column_type}"
            )

    connection.execute(
        """
        UPDATE opportunities
        SET created_at = CURRENT_TIMESTAMP
        WHERE created_at IS NULL
        """
    )

    connection.execute(
        """
        UPDATE opportunities
        SET updated_at = CURRENT_TIMESTAMP
        WHERE updated_at IS NULL
        """
    )


def initialize_database(
    database_path: Path = DEFAULT_DATABASE
) -> None:
    """Create or upgrade the opportunity database."""

    with get_connection(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                title TEXT NOT NULL,
                organization TEXT NOT NULL,
                category TEXT NOT NULL,
                opportunity_type TEXT NOT NULL,

                field TEXT,
                location TEXT,
                work_mode TEXT,
                description TEXT,

                evidence TEXT,
                requirements TEXT,
                preferred_skills TEXT,

                compensation TEXT,
                duration TEXT,
                start_date TEXT,
                deadline TEXT,
                start_date_text TEXT,
                deadline_text TEXT,

                eligibility TEXT,
                application_url TEXT,
                source_url TEXT NOT NULL,
                related_source_urls TEXT,

                date_discovered TEXT,
                last_verified TEXT,
                status TEXT,

                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        migrate_database(connection)

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_opportunities_title
            ON opportunities(title)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_opportunities_category
            ON opportunities(category)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_opportunities_deadline
            ON opportunities(deadline)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_opportunities_identity
            ON opportunities(
                lower(trim(title)),
                lower(trim(organization)),
                category
            )
            """
        )

"""SQLite database connection and schema management."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_DATABASE = (
    PROJECT_ROOT / "data" / "database" / "opportunities.db"
)


TABLE_COLUMNS = {
    "field": "TEXT",
    "location": "TEXT",
    "work_mode": "TEXT",
    "description": "TEXT",
    "evidence": "TEXT",
    "requirements": "TEXT",
    "preferred_skills": "TEXT",
    "compensation": "TEXT",
    "duration": "TEXT",
    "start_date": "TEXT",
    "deadline": "TEXT",
    "start_date_text": "TEXT",
    "deadline_text": "TEXT",
    "eligibility": "TEXT",
    "application_url": "TEXT",
    "related_source_urls": "TEXT",
    "date_discovered": "TEXT",
    "last_verified": "TEXT",
    "status": "TEXT",
    "created_at": "TEXT",
    "updated_at": "TEXT",
}


@contextmanager
def get_connection(
    database_path: Path = DEFAULT_DATABASE
) -> Iterator[sqlite3.Connection]:
    """Create, manage, and reliably close a database connection."""

    database_path = Path(database_path)
    database_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def migrate_database(
    connection: sqlite3.Connection
) -> None:
    """Add missing columns to an existing opportunities table."""

    existing_columns = {
        column["name"]
        for column in connection.execute(
            "PRAGMA table_info(opportunities)"
        ).fetchall()
    }

    for column_name, column_type in TABLE_COLUMNS.items():
        if column_name not in existing_columns:
            connection.execute(
                f"ALTER TABLE opportunities "
                f"ADD COLUMN {column_name} {column_type}"
            )

    connection.execute(
        """
        UPDATE opportunities
        SET created_at = CURRENT_TIMESTAMP
        WHERE created_at IS NULL
        """
    )

    connection.execute(
        """
        UPDATE opportunities
        SET updated_at = CURRENT_TIMESTAMP
        WHERE updated_at IS NULL
        """
    )


def initialize_database(
    database_path: Path = DEFAULT_DATABASE
) -> None:
    """Create or upgrade the opportunity database."""

    with get_connection(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                title TEXT NOT NULL,
                organization TEXT NOT NULL,
                category TEXT NOT NULL,
                opportunity_type TEXT NOT NULL,

                field TEXT,
                location TEXT,
                work_mode TEXT,
                description TEXT,

                evidence TEXT,
                requirements TEXT,
                preferred_skills TEXT,

                compensation TEXT,
                duration TEXT,
                start_date TEXT,
                deadline TEXT,
                start_date_text TEXT,
                deadline_text TEXT,

                eligibility TEXT,
                application_url TEXT,
                source_url TEXT NOT NULL,
                related_source_urls TEXT,

                date_discovered TEXT,
                last_verified TEXT,
                status TEXT,

                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        migrate_database(connection)

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS verification_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                opportunity_id INTEGER NOT NULL,
                checked_at TEXT NOT NULL,
                outcome TEXT NOT NULL,

                changed_fields TEXT NOT NULL DEFAULT '[]',
                previous_values TEXT NOT NULL DEFAULT '{}',
                current_values TEXT NOT NULL DEFAULT '{}',

                source_url TEXT,
                notes TEXT,

                FOREIGN KEY (opportunity_id)
                    REFERENCES opportunities(id)
                    ON DELETE CASCADE
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_opportunities_title
            ON opportunities(title)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_opportunities_category
            ON opportunities(category)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_opportunities_deadline
            ON opportunities(deadline)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_opportunities_identity
            ON opportunities(
                lower(trim(title)),
                lower(trim(organization)),
                category
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_verification_opportunity
            ON verification_history(opportunity_id, checked_at)
            """
        )
