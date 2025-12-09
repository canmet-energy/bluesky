"""
SQLite database operations for NECB article storage.

Extends the existing necb_production.db with article tables.

NECB Hierarchy (stored in database):
    Division (A, B, C, D)
    └── Part (3)
        └── Section (3.5)
            └── Subsection (3.5.2)
                └── Article (3.5.2.1)
                    └── Sentence (3.5.2.1.(1))
                        └── Clause (3.5.2.1.(1)(a))
                            └── Subclause (3.5.2.1.(1)(a)(i))

Tables:
    - necb_articles: Main articles with full_text
    - necb_sentences: Sentences within articles, with clauses_json for nested structure
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict

from . import config
from .article_models import Article, Sentence, Clause, Subclause

logger = logging.getLogger(__name__)


# ============================================================
# DATABASE INITIALIZATION
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


def init_database():
    """Initialize database schema for articles.

    Creates tables and indexes if they don't exist.
    Uses correct NECB terminology: Sentence → Clause → Subclause
    """
    logger.info(f"Initializing database: {config.DATABASE_PATH}")

    conn = get_connection()
    cursor = conn.cursor()

    # Create necb_articles table
    # Stores main article content with full reference (e.g., '3.5.2.1')
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS necb_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER,
            vintage TEXT NOT NULL,
            division TEXT,
            article_number TEXT NOT NULL,
            reference TEXT NOT NULL,
            title TEXT,
            hierarchy_level TEXT NOT NULL,
            part_number TEXT,
            section_number TEXT,
            subsection_number TEXT,
            full_text TEXT NOT NULL,
            page_start INTEGER,
            page_end INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES necb_articles(id)
        )
    """)

    # Create necb_sentences table (using correct NECB terminology)
    # Sentences are numbered elements like 1), 2), 3)
    # clauses_json stores nested Clauses (a, b, c) and Subclauses (i, ii, iii)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS necb_sentences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL,
            sentence_number TEXT NOT NULL,
            reference TEXT NOT NULL,
            sentence_text TEXT NOT NULL,
            clauses_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (article_id) REFERENCES necb_articles(id) ON DELETE CASCADE
        )
    """)

    # Create indexes
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_article_number
        ON necb_articles(article_number, vintage)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_article_reference
        ON necb_articles(reference)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_article_parent
        ON necb_articles(parent_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_article_vintage
        ON necb_articles(vintage)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_article_hierarchy
        ON necb_articles(hierarchy_level)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_article_division
        ON necb_articles(division)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sentence_article
        ON necb_sentences(article_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sentence_reference
        ON necb_sentences(reference)
    """)

    conn.commit()
    conn.close()

    logger.info("Database initialization complete")


# ============================================================
# INSERT OPERATIONS
# ============================================================

def insert_article(article: Article) -> int:
    """Insert a single article into database.

    Args:
        article: Article object to insert

    Returns:
        Database ID of inserted article
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Insert article
        # Note: reference defaults to article_number; part/section/subsection computed from article_number
        cursor.execute("""
            INSERT INTO necb_articles (
                parent_id, vintage, division, article_number, reference, title, hierarchy_level,
                part_number, section_number, subsection_number,
                full_text, page_start, page_end
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            article.parent_id,
            article.vintage,
            article.division,
            article.article_number,
            article.article_number,  # reference = article_number
            article.title,
            article.hierarchy_level,
            article.part_number,  # Computed property
            article.section_number,  # Computed property
            article.subsection_number,  # Computed property
            article.full_text,
            article.page_start,
            article.page_end
        ))

        article_id = cursor.lastrowid

        # Insert sentences (using correct NECB terminology)
        for sentence in article.sentences:
            # Convert clauses to JSON (with nested subclauses)
            clauses_json = json.dumps([
                {
                    "clause_letter": clause.clause_letter,
                    "reference": clause.reference,
                    "text": clause.text,
                    "subclauses": [
                        {
                            "subclause_numeral": subclause.subclause_numeral,
                            "reference": subclause.reference,
                            "text": subclause.text
                        }
                        for subclause in clause.subclauses
                    ]
                }
                for clause in sentence.clauses
            ])

            cursor.execute("""
                INSERT INTO necb_sentences (
                    article_id, sentence_number, reference, sentence_text, clauses_json
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                article_id,
                sentence.sentence_number,
                sentence.reference,
                sentence.text,
                clauses_json
            ))

        conn.commit()
        logger.debug(f"Inserted article {article.article_number} with ID {article_id}")
        return article_id

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to insert article {article.article_number}: {e}")
        raise

    finally:
        conn.close()


def insert_batch(articles: List[Article], batch_size: int = None) -> int:
    """Insert multiple articles in batches.

    Args:
        articles: List of Article objects to insert
        batch_size: Number of articles per batch (default from config)

    Returns:
        Number of articles successfully inserted
    """
    if batch_size is None:
        batch_size = config.BATCH_INSERT_SIZE

    logger.info(f"Inserting {len(articles)} articles in batches of {batch_size}")

    inserted_count = 0

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]

        try:
            for article in batch:
                insert_article(article)
                inserted_count += 1

            if (inserted_count % batch_size) == 0:
                logger.info(f"Inserted {inserted_count}/{len(articles)} articles")

        except Exception as e:
            logger.error(f"Failed to insert batch starting at index {i}: {e}")
            # Continue with next batch

    logger.info(f"Batch insert complete: {inserted_count}/{len(articles)} articles inserted")
    return inserted_count


# ============================================================
# QUERY OPERATIONS
# ============================================================

def get_article_by_number(article_number: str, vintage: str) -> Optional[Article]:
    """Get article by article number and vintage.

    Args:
        article_number: Article number (e.g., '8.1.1.2')
        vintage: NECB vintage year

    Returns:
        Article object if found, None otherwise
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM necb_articles
        WHERE article_number = ? AND vintage = ?
    """, (article_number, vintage))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    # Convert row to Article
    article = _row_to_article(row)
    return article


def get_articles_by_vintage(vintage: str) -> List[Article]:
    """Get all articles for a specific vintage.

    Args:
        vintage: NECB vintage year

    Returns:
        List of Article objects
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM necb_articles
        WHERE vintage = ?
        ORDER BY article_number
    """, (vintage,))

    rows = cursor.fetchall()
    conn.close()

    articles = [_row_to_article(row) for row in rows]
    logger.info(f"Retrieved {len(articles)} articles for vintage {vintage}")
    return articles


def get_children(parent_id: int) -> List[Article]:
    """Get child articles of a parent.

    Args:
        parent_id: Database ID of parent article

    Returns:
        List of child Article objects
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM necb_articles
        WHERE parent_id = ?
        ORDER BY article_number
    """, (parent_id,))

    rows = cursor.fetchall()
    conn.close()

    return [_row_to_article(row) for row in rows]


def get_article_count(vintage: Optional[str] = None) -> int:
    """Get count of articles in database.

    Args:
        vintage: Optional vintage to filter by

    Returns:
        Number of articles
    """
    conn = get_connection()
    cursor = conn.cursor()

    if vintage:
        cursor.execute("SELECT COUNT(*) FROM necb_articles WHERE vintage = ?", (vintage,))
    else:
        cursor.execute("SELECT COUNT(*) FROM necb_articles")

    count = cursor.fetchone()[0]
    conn.close()

    return count


def get_vintage_stats() -> Dict[str, int]:
    """Get article counts by vintage.

    Returns:
        Dictionary mapping vintage to article count
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT vintage, COUNT(*) as count
        FROM necb_articles
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
    """Delete all articles for a specific vintage.

    Args:
        vintage: NECB vintage year to delete

    Returns:
        Number of articles deleted
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Count before delete
    cursor.execute("SELECT COUNT(*) FROM necb_articles WHERE vintage = ?", (vintage,))
    count = cursor.fetchone()[0]

    # Delete (clauses deleted automatically via CASCADE)
    cursor.execute("DELETE FROM necb_articles WHERE vintage = ?", (vintage,))

    conn.commit()
    conn.close()

    logger.info(f"Deleted {count} articles for vintage {vintage}")
    return count


def clear_all_articles():
    """Delete all articles from database.

    Use with caution!
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Count before delete
    cursor.execute("SELECT COUNT(*) FROM necb_articles")
    count = cursor.fetchone()[0]

    # Delete all
    cursor.execute("DELETE FROM necb_articles")
    cursor.execute("DELETE FROM necb_clauses")

    conn.commit()
    conn.close()

    logger.warning(f"Deleted ALL {count} articles from database")
    return count


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def _row_to_article(row: sqlite3.Row) -> Article:
    """Convert database row to Article object.

    Args:
        row: SQLite row object

    Returns:
        Article object with sentences, clauses, and subclauses loaded

    Note:
        part_number, section_number, subsection_number are computed properties
        in the Article model (derived from article_number), so they are not
        passed during construction even though they exist in the database.
    """
    # Get article data
    # Note: part_number, section_number, subsection_number are computed from article_number
    article = Article(
        id=row["id"],
        parent_id=row["parent_id"],
        vintage=row["vintage"],
        division=row["division"] if "division" in row.keys() else None,
        article_number=row["article_number"],
        reference=row["reference"] if "reference" in row.keys() else row["article_number"],
        title=row["title"],
        hierarchy_level=row["hierarchy_level"],
        full_text=row["full_text"],
        page_start=row["page_start"],
        page_end=row["page_end"],
    )

    # Load sentences (using correct NECB terminology)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM necb_sentences
        WHERE article_id = ?
        ORDER BY sentence_number
    """, (row["id"],))

    sentence_rows = cursor.fetchall()
    conn.close()

    for sentence_row in sentence_rows:
        # Parse clauses from JSON (with nested subclauses)
        clauses_data = json.loads(sentence_row["clauses_json"]) if sentence_row["clauses_json"] else []

        clauses = []
        for clause_data in clauses_data:
            subclauses = [
                Subclause(
                    subclause_numeral=sc["subclause_numeral"],
                    reference=sc.get("reference", ""),
                    text=sc["text"]
                )
                for sc in clause_data.get("subclauses", [])
            ]

            clause = Clause(
                clause_letter=clause_data["clause_letter"],
                reference=clause_data.get("reference", ""),
                text=clause_data["text"],
                subclauses=subclauses
            )
            clauses.append(clause)

        sentence = Sentence(
            sentence_number=sentence_row["sentence_number"],
            reference=sentence_row["reference"],
            text=sentence_row["sentence_text"],
            clauses=clauses
        )

        article.sentences.append(sentence)

    return article


def database_exists() -> bool:
    """Check if database file exists.

    Returns:
        True if database exists, False otherwise
    """
    return config.DATABASE_PATH.exists()


def get_database_info() -> dict:
    """Get database information and statistics.

    Returns:
        Dictionary with database info using correct NECB terminology
    """
    if not database_exists():
        return {"exists": False}

    conn = get_connection()
    cursor = conn.cursor()

    # Get table info
    cursor.execute("SELECT COUNT(*) FROM necb_articles")
    total_articles = cursor.fetchone()[0]

    # Check if necb_sentences table exists (new schema)
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='necb_sentences'
    """)
    has_sentences_table = cursor.fetchone() is not None

    total_sentences = 0
    if has_sentences_table:
        cursor.execute("SELECT COUNT(*) FROM necb_sentences")
        total_sentences = cursor.fetchone()[0]

    # Get vintage stats
    cursor.execute("""
        SELECT vintage, COUNT(*) as count
        FROM necb_articles
        GROUP BY vintage
    """)
    vintage_stats = {row["vintage"]: row["count"] for row in cursor.fetchall()}

    conn.close()

    return {
        "exists": True,
        "path": str(config.DATABASE_PATH),
        "total_articles": total_articles,
        "total_sentences": total_sentences,  # Renamed from total_clauses
        "vintage_stats": vintage_stats,
    }
