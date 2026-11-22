
import sqlite3

from opportunity_intelligence.storage.database import (
    get_connection,
    initialize_database
)


def test_initialize_database_creates_file(tmp_path):
    database_path = tmp_path / "test.db"

    initialize_database(database_path)

    assert database_path.exists()


def test_initialize_database_creates_opportunities_table(tmp_path):
    database_path = tmp_path / "test.db"

    initialize_database(database_path)

    with get_connection(database_path) as connection:
        result = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name = 'opportunities'
            """
        ).fetchone()

    assert result is not None


def test_opportunities_table_has_expected_columns(tmp_path):
    database_path = tmp_path / "test.db"

    initialize_database(database_path)

    with get_connection(database_path) as connection:
        columns = connection.execute(
            "PRAGMA table_info(opportunities)"
        ).fetchall()

    column_names = [column["name"] for column in columns]

    assert "id" in column_names
    assert "title" in column_names
    assert "organization" in column_names
    assert "category" in column_names
    assert "source_url" in column_names
    assert "created_at" in column_names
    assert "updated_at" in column_names


def test_initialize_database_can_run_multiple_times(tmp_path):
    database_path = tmp_path / "test.db"

    initialize_database(database_path)
    initialize_database(database_path)

    with get_connection(database_path) as connection:
        result = connection.execute(
            "SELECT COUNT(*) FROM opportunities"
        ).fetchone()

    assert result[0] == 0
