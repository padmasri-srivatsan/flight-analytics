import re
import sqlite3
from pathlib import Path
from typing import Optional
import sys


def connect_db(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection to the given database path."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def list_tables(conn: sqlite3.Connection) -> list:
    """Return a list of table names in the connected database."""
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    return [row[0] for row in cur.fetchall()]


def _validate_table_name(table: str) -> None:
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table):
        raise ValueError("Invalid table name")


def show_table_sample(conn: sqlite3.Connection, table: str, limit: int = 10) -> list:
    """Return up to `limit` rows from `table` as a list of sqlite3.Row."""
    _validate_table_name(table)
    cur = conn.cursor()
    cur.execute(f'SELECT * FROM "{table}" LIMIT ?', (limit,))
    return cur.fetchall()


def main(db_path: Optional[str] = None) -> None:
    if db_path is None:
        db_path = Path(__file__).parent / "aviation_local.db"
    else:
        db_path = Path(db_path)

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return

    conn = connect_db(str(db_path))
    try:
        print(f"Connected to {db_path}")
        tables = list_tables(conn)
        if not tables:
            print("No tables found in the database.")
            return

        print("Tables:")
        for t in tables:
            print(" -", t)

        # show a small sample from the first table
        first = tables[0]
        sample = show_table_sample(conn, first, limit=5)
        print(f"\nFirst {min(5, len(sample))} rows from '{first}':")
        for r in sample:
            print(dict(r))
    finally:
        conn.close()


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(arg)
