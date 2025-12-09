"""
SQLite database operations for NECB figure storage.

Extends necb_production.db with figure tables.
"""

import logging
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict

from . import figure_config as config
from .figure_models import Figure

logger = logging.getLogger(__name__)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection() -> sqlite3.Connection:
    """Get database connection.

    Returns:
        SQLite connection object
    """
    db_path = config.DATABASE_PATH

    # Create parent directory if needed
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_figures_table():
    """Initialize database schema for figures.

    Creates necb_figures table and indexes if they don't exist.
    """
    logger.info(f"Initializing figures table in: {config.DATABASE_PATH}")

    conn = get_connection()
    cursor = conn.cursor()

    # Create necb_figures table
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {config.TABLE_FIGURES} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vintage TEXT NOT NULL,
            division TEXT,
            label TEXT NOT NULL,
            caption TEXT,
            page INTEGER NOT NULL,
            bbox_x0 REAL,
            bbox_y0 REAL,
            bbox_x1 REAL,
            bbox_y1 REAL,
            image_path TEXT NOT NULL,
            image_type TEXT NOT NULL,
            image_format TEXT,
            width INTEGER,
            height INTEGER,
            file_size INTEGER,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes
    cursor.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_figure_label
        ON {config.TABLE_FIGURES}(label, vintage)
    """)

    cursor.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_figure_page
        ON {config.TABLE_FIGURES}(page, vintage)
    """)

    cursor.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_figure_vintage
        ON {config.TABLE_FIGURES}(vintage)
    """)

    cursor.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_figure_division
        ON {config.TABLE_FIGURES}(division)
    """)

    conn.commit()
    conn.close()

    logger.info("Figures table initialization complete")


# ============================================================
# INSERT OPERATIONS
# ============================================================

def insert_figure(figure: Figure) -> int:
    """Insert a single figure into database.

    Args:
        figure: Figure object to insert

    Returns:
        Database ID of inserted figure
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(f"""
            INSERT INTO {config.TABLE_FIGURES} (
                vintage, division, label, caption, page,
                bbox_x0, bbox_y0, bbox_x1, bbox_y1,
                image_path, image_type, image_format,
                width, height, file_size
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            figure.vintage,
            figure.division,
            figure.label,
            figure.caption,
            figure.page,
            figure.bbox[0],
            figure.bbox[1],
            figure.bbox[2],
            figure.bbox[3],
            figure.image_path,
            figure.image_type,
            figure.image_format,
            figure.width,
            figure.height,
            figure.file_size
        ))

        figure_id = cursor.lastrowid
        conn.commit()

        logger.debug(f"Inserted figure {figure.label} with ID {figure_id}")
        return figure_id

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to insert figure {figure.label}: {e}")
        raise

    finally:
        conn.close()


def insert_batch(figures: List[Figure], batch_size: int = 100) -> int:
    """Insert multiple figures in batches.

    Args:
        figures: List of Figure objects to insert
        batch_size: Number of figures per batch

    Returns:
        Number of figures successfully inserted
    """
    logger.info(f"Inserting {len(figures)} figures in batches of {batch_size}")

    inserted_count = 0

    for i in range(0, len(figures), batch_size):
        batch = figures[i:i + batch_size]

        try:
            for figure in batch:
                insert_figure(figure)
                inserted_count += 1

            if (inserted_count % batch_size) == 0:
                logger.info(f"Inserted {inserted_count}/{len(figures)} figures")

        except Exception as e:
            logger.error(f"Failed to insert batch starting at index {i}: {e}")
            # Continue with next batch

    logger.info(f"Batch insert complete: {inserted_count}/{len(figures)} figures inserted")
    return inserted_count


# ============================================================
# QUERY OPERATIONS
# ============================================================

def get_figure_by_label(label: str, vintage: str) -> Optional[Figure]:
    """Get figure by label and vintage.

    Args:
        label: Figure label (e.g., "A-8.4.4.17.(2)")
        vintage: NECB vintage year

    Returns:
        Figure object if found, None otherwise
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT * FROM {config.TABLE_FIGURES}
        WHERE label = ? AND vintage = ?
    """, (label, vintage))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return _row_to_figure(row)


def get_figures_by_vintage(vintage: str) -> List[Figure]:
    """Get all figures for a specific vintage.

    Args:
        vintage: NECB vintage year

    Returns:
        List of Figure objects
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT * FROM {config.TABLE_FIGURES}
        WHERE vintage = ?
        ORDER BY page, label
    """, (vintage,))

    rows = cursor.fetchall()
    conn.close()

    figures = [_row_to_figure(row) for row in rows]
    logger.info(f"Retrieved {len(figures)} figures for vintage {vintage}")
    return figures


def get_figures_by_page(page: int, vintage: str) -> List[Figure]:
    """Get all figures on a specific page.

    Args:
        page: Page number (0-indexed)
        vintage: NECB vintage year

    Returns:
        List of Figure objects on that page
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT * FROM {config.TABLE_FIGURES}
        WHERE page = ? AND vintage = ?
        ORDER BY bbox_y0
    """, (page, vintage))

    rows = cursor.fetchall()
    conn.close()

    return [_row_to_figure(row) for row in rows]


def get_figure_count(vintage: Optional[str] = None) -> int:
    """Get count of figures in database.

    Args:
        vintage: Optional vintage to filter by

    Returns:
        Number of figures
    """
    conn = get_connection()
    cursor = conn.cursor()

    if vintage:
        cursor.execute(f"SELECT COUNT(*) FROM {config.TABLE_FIGURES} WHERE vintage = ?", (vintage,))
    else:
        cursor.execute(f"SELECT COUNT(*) FROM {config.TABLE_FIGURES}")

    count = cursor.fetchone()[0]
    conn.close()

    return count


def get_vintage_stats() -> Dict[str, int]:
    """Get figure counts by vintage.

    Returns:
        Dictionary mapping vintage to figure count
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT vintage, COUNT(*) as count
        FROM {config.TABLE_FIGURES}
        GROUP BY vintage
        ORDER BY vintage
    """)

    rows = cursor.fetchall()
    conn.close()

    return {row["vintage"]: row["count"] for row in rows}


# ============================================================
# DELETE OPERATIONS
# ============================================================

def delete_vintage(vintage: str) -> int:
    """Delete all figures for a specific vintage.

    Args:
        vintage: NECB vintage year to delete

    Returns:
        Number of figures deleted
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Count before delete
    cursor.execute(f"SELECT COUNT(*) FROM {config.TABLE_FIGURES} WHERE vintage = ?", (vintage,))
    count = cursor.fetchone()[0]

    # Delete
    cursor.execute(f"DELETE FROM {config.TABLE_FIGURES} WHERE vintage = ?", (vintage,))

    conn.commit()
    conn.close()

    logger.info(f"Deleted {count} figures for vintage {vintage}")
    return count


def clear_all_figures():
    """Delete all figures from database.

    Use with caution!
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Count before delete
    cursor.execute(f"SELECT COUNT(*) FROM {config.TABLE_FIGURES}")
    count = cursor.fetchone()[0]

    # Delete all
    cursor.execute(f"DELETE FROM {config.TABLE_FIGURES}")

    conn.commit()
    conn.close()

    logger.warning(f"Deleted ALL {count} figures from database")
    return count


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def _row_to_figure(row: sqlite3.Row) -> Figure:
    """Convert database row to Figure object.

    Args:
        row: SQLite row object

    Returns:
        Figure object
    """
    return Figure(
        id=row["id"],
        vintage=row["vintage"],
        division=row["division"] if "division" in row.keys() else None,
        label=row["label"],
        caption=row["caption"],
        page=row["page"],
        bbox=(row["bbox_x0"], row["bbox_y0"], row["bbox_x1"], row["bbox_y1"]),
        image_path=row["image_path"],
        image_type=row["image_type"],
        image_format=row["image_format"],
        width=row["width"],
        height=row["height"],
        file_size=row["file_size"]
    )


def database_exists() -> bool:
    """Check if database file exists.

    Returns:
        True if database exists, False otherwise
    """
    return config.DATABASE_PATH.exists()


def get_database_info() -> dict:
    """Get database information and statistics.

    Returns:
        Dictionary with database info
    """
    if not database_exists():
        return {"exists": False}

    conn = get_connection()
    cursor = conn.cursor()

    # Check if table exists
    cursor.execute(f"""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='{config.TABLE_FIGURES}'
    """)

    if not cursor.fetchone():
        conn.close()
        return {
            "exists": True,
            "table_exists": False,
            "path": str(config.DATABASE_PATH)
        }

    # Get total count
    cursor.execute(f"SELECT COUNT(*) FROM {config.TABLE_FIGURES}")
    total_figures = cursor.fetchone()[0]

    # Get vintage stats
    cursor.execute(f"""
        SELECT vintage, COUNT(*) as count
        FROM {config.TABLE_FIGURES}
        GROUP BY vintage
    """)
    vintage_stats = {row["vintage"]: row["count"] for row in cursor.fetchall()}

    conn.close()

    return {
        "exists": True,
        "table_exists": True,
        "path": str(config.DATABASE_PATH),
        "total_figures": total_figures,
        "vintage_stats": vintage_stats,
    }
