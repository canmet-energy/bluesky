"""
NECB Index Database Operations

SQLite operations for storing and querying parsed index entries.
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import List, Optional

from .config import DATABASE_PATH, TABLE_INDEX, TABLE_INDEX_FTS
from .index_models import IndexEntry

logger = logging.getLogger(__name__)


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Get database connection."""
    path = db_path or DATABASE_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_database(db_path: Optional[Path] = None) -> None:
    """
    Initialize database schema for index tables.

    Creates:
    - necb_index: Main index entries table
    - necb_index_fts: FTS5 virtual table for fast text search
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Main index table
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_INDEX} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vintage TEXT NOT NULL,
            term TEXT NOT NULL,
            parent_term TEXT,
            description TEXT,
            article_references TEXT,
            division_hints TEXT,
            see_also TEXT,
            page INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Indexes for fast lookups
    cursor.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_necb_index_vintage_term
        ON {TABLE_INDEX}(vintage, term COLLATE NOCASE)
    """)

    cursor.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_necb_index_vintage_parent
        ON {TABLE_INDEX}(vintage, parent_term COLLATE NOCASE)
    """)

    cursor.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_necb_index_vintage
        ON {TABLE_INDEX}(vintage)
    """)

    # FTS5 virtual table for fast prefix/substring search
    # Using content sync to keep FTS in sync with main table
    cursor.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS {TABLE_INDEX_FTS} USING fts5(
            term,
            description,
            content='{TABLE_INDEX}',
            content_rowid='id'
        )
    """)

    # Triggers to keep FTS in sync
    cursor.execute(f"""
        CREATE TRIGGER IF NOT EXISTS {TABLE_INDEX}_ai AFTER INSERT ON {TABLE_INDEX} BEGIN
            INSERT INTO {TABLE_INDEX_FTS}(rowid, term, description)
            VALUES (new.id, new.term, new.description);
        END
    """)

    cursor.execute(f"""
        CREATE TRIGGER IF NOT EXISTS {TABLE_INDEX}_ad AFTER DELETE ON {TABLE_INDEX} BEGIN
            INSERT INTO {TABLE_INDEX_FTS}({TABLE_INDEX_FTS}, rowid, term, description)
            VALUES ('delete', old.id, old.term, old.description);
        END
    """)

    cursor.execute(f"""
        CREATE TRIGGER IF NOT EXISTS {TABLE_INDEX}_au AFTER UPDATE ON {TABLE_INDEX} BEGIN
            INSERT INTO {TABLE_INDEX_FTS}({TABLE_INDEX_FTS}, rowid, term, description)
            VALUES ('delete', old.id, old.term, old.description);
            INSERT INTO {TABLE_INDEX_FTS}(rowid, term, description)
            VALUES (new.id, new.term, new.description);
        END
    """)

    conn.commit()
    conn.close()

    logger.info(f"Initialized index database schema: {TABLE_INDEX}, {TABLE_INDEX_FTS}")


def insert_entry(entry: IndexEntry, db_path: Optional[Path] = None) -> int:
    """Insert a single index entry. Returns the inserted row ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        f"""
        INSERT INTO {TABLE_INDEX}
        (vintage, term, parent_term, description, article_references,
         division_hints, see_also, page)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entry.vintage,
            entry.term,
            entry.parent_term,
            entry.description,
            json.dumps(entry.article_references),
            json.dumps(entry.division_hints),
            entry.see_also,
            entry.page,
        ),
    )

    row_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return row_id


def insert_batch(
    entries: List[IndexEntry],
    db_path: Optional[Path] = None,
    batch_size: int = 100,
) -> int:
    """Insert multiple entries in batches. Returns count of inserted rows."""
    if not entries:
        return 0

    conn = get_connection(db_path)
    cursor = conn.cursor()

    inserted = 0
    for i in range(0, len(entries), batch_size):
        batch = entries[i : i + batch_size]
        cursor.executemany(
            f"""
            INSERT INTO {TABLE_INDEX}
            (vintage, term, parent_term, description, article_references,
             division_hints, see_also, page)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    e.vintage,
                    e.term,
                    e.parent_term,
                    e.description,
                    json.dumps(e.article_references),
                    json.dumps(e.division_hints),
                    e.see_also,
                    e.page,
                )
                for e in batch
            ],
        )
        inserted += len(batch)
        conn.commit()

    conn.close()
    logger.info(f"Inserted {inserted} index entries")
    return inserted


def get_entry_by_term(
    term: str,
    vintage: str = "2020",
    db_path: Optional[Path] = None,
) -> Optional[IndexEntry]:
    """Get a specific index entry by exact term match."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        f"""
        SELECT * FROM {TABLE_INDEX}
        WHERE vintage = ? AND term = ? COLLATE NOCASE
        LIMIT 1
        """,
        (vintage, term),
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        return _row_to_entry(row)
    return None


def get_entries_by_term(
    term: str,
    vintage: str = "2020",
    include_children: bool = True,
    db_path: Optional[Path] = None,
) -> List[IndexEntry]:
    """
    Get index entries matching a term.

    Args:
        term: Term to search for (case-insensitive)
        vintage: NECB vintage
        include_children: Include sub-entries under this term

    Returns:
        List of matching entries (main term + children if requested)
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    if include_children:
        # Get main term and all sub-entries
        cursor.execute(
            f"""
            SELECT * FROM {TABLE_INDEX}
            WHERE vintage = ?
              AND (term = ? COLLATE NOCASE OR parent_term = ? COLLATE NOCASE)
            ORDER BY
                CASE WHEN parent_term IS NULL THEN 0 ELSE 1 END,
                term, description
            """,
            (vintage, term, term),
        )
    else:
        # Only main term
        cursor.execute(
            f"""
            SELECT * FROM {TABLE_INDEX}
            WHERE vintage = ? AND term = ? COLLATE NOCASE AND parent_term IS NULL
            ORDER BY term
            """,
            (vintage, term),
        )

    rows = cursor.fetchall()
    conn.close()

    return [_row_to_entry(row) for row in rows]


def search_entries(
    query: str,
    vintage: str = "2020",
    limit: int = 50,
    db_path: Optional[Path] = None,
) -> List[IndexEntry]:
    """
    Search index entries using FTS5.

    Args:
        query: Search query (supports FTS5 syntax)
        vintage: NECB vintage
        limit: Maximum results

    Returns:
        List of matching entries ranked by relevance
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Use FTS5 MATCH with prefix search
    fts_query = f"{query}*"

    try:
        cursor.execute(
            f"""
            SELECT i.* FROM {TABLE_INDEX} i
            JOIN {TABLE_INDEX_FTS} fts ON i.id = fts.rowid
            WHERE fts.{TABLE_INDEX_FTS} MATCH ?
              AND i.vintage = ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts_query, vintage, limit),
        )
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        # Fallback to LIKE if FTS fails
        cursor.execute(
            f"""
            SELECT * FROM {TABLE_INDEX}
            WHERE vintage = ?
              AND (term LIKE ? COLLATE NOCASE OR description LIKE ? COLLATE NOCASE)
            ORDER BY term
            LIMIT ?
            """,
            (vintage, f"%{query}%", f"%{query}%", limit),
        )
        rows = cursor.fetchall()

    conn.close()
    return [_row_to_entry(row) for row in rows]


def list_terms(
    prefix: str = "",
    vintage: str = "2020",
    limit: int = 50,
    db_path: Optional[Path] = None,
) -> List[str]:
    """
    List distinct main terms, optionally filtered by prefix.

    Args:
        prefix: Optional prefix to filter terms
        vintage: NECB vintage
        limit: Maximum results

    Returns:
        List of distinct term names
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    if prefix:
        cursor.execute(
            f"""
            SELECT DISTINCT term FROM {TABLE_INDEX}
            WHERE vintage = ? AND parent_term IS NULL
              AND term LIKE ? COLLATE NOCASE
            ORDER BY term
            LIMIT ?
            """,
            (vintage, f"{prefix}%", limit),
        )
    else:
        cursor.execute(
            f"""
            SELECT DISTINCT term FROM {TABLE_INDEX}
            WHERE vintage = ? AND parent_term IS NULL
            ORDER BY term
            LIMIT ?
            """,
            (vintage, limit),
        )

    rows = cursor.fetchall()
    conn.close()

    return [row["term"] for row in rows]


def get_entries_by_vintage(
    vintage: str,
    db_path: Optional[Path] = None,
) -> List[IndexEntry]:
    """Get all index entries for a vintage."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        f"""
        SELECT * FROM {TABLE_INDEX}
        WHERE vintage = ?
        ORDER BY term, description
        """,
        (vintage,),
    )

    rows = cursor.fetchall()
    conn.close()

    return [_row_to_entry(row) for row in rows]


def get_entry_count(
    vintage: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> int:
    """Get count of index entries, optionally filtered by vintage."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    if vintage:
        cursor.execute(
            f"SELECT COUNT(*) as count FROM {TABLE_INDEX} WHERE vintage = ?",
            (vintage,),
        )
    else:
        cursor.execute(f"SELECT COUNT(*) as count FROM {TABLE_INDEX}")

    count = cursor.fetchone()["count"]
    conn.close()

    return count


def delete_vintage(
    vintage: str,
    db_path: Optional[Path] = None,
) -> int:
    """Delete all index entries for a vintage. Returns count deleted."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        f"DELETE FROM {TABLE_INDEX} WHERE vintage = ?",
        (vintage,),
    )

    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    logger.info(f"Deleted {deleted} index entries for vintage {vintage}")
    return deleted


def get_vintage_stats(db_path: Optional[Path] = None) -> dict:
    """Get statistics for each vintage."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT
            vintage,
            COUNT(*) as total_entries,
            COUNT(CASE WHEN parent_term IS NULL THEN 1 END) as main_terms,
            COUNT(CASE WHEN parent_term IS NOT NULL THEN 1 END) as sub_terms,
            COUNT(CASE WHEN see_also IS NOT NULL THEN 1 END) as cross_refs
        FROM {TABLE_INDEX}
        GROUP BY vintage
        ORDER BY vintage
    """)

    stats = {}
    for row in cursor.fetchall():
        stats[row["vintage"]] = {
            "total_entries": row["total_entries"],
            "main_terms": row["main_terms"],
            "sub_terms": row["sub_terms"],
            "cross_refs": row["cross_refs"],
        }

    conn.close()
    return stats


def _row_to_entry(row: sqlite3.Row) -> IndexEntry:
    """Convert database row to IndexEntry model."""
    return IndexEntry(
        term=row["term"],
        parent_term=row["parent_term"],
        description=row["description"],
        article_references=json.loads(row["article_references"] or "[]"),
        division_hints=json.loads(row["division_hints"] or "[]"),
        see_also=row["see_also"],
        page=row["page"],
        vintage=row["vintage"],
    )
