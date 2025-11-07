"""
SQLite Database Builder for OpenStudio Documentation

Builds a searchable SQLite database from scraped OpenStudio documentation.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List

from rich.console import Console
from rich.progress import track

from .openstudio_docs_scraper import OpenStudioClass

console = Console()


class DatabaseBuilder:
    """Builds SQLite database from scraped OpenStudio classes"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None

    def __enter__(self):
        """Context manager entry"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.conn:
            self.conn.close()

    def create_schema(self):
        """Create database schema"""
        cursor = self.conn.cursor()

        # Metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                version TEXT PRIMARY KEY,
                scraped_at TEXT NOT NULL,
                source_url TEXT NOT NULL,
                total_classes INTEGER,
                total_methods INTEGER
            )
        """)

        # Classes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                namespace TEXT,
                full_name TEXT NOT NULL,
                description TEXT,
                parent_class TEXT,
                doc_url TEXT NOT NULL,
                UNIQUE(namespace, name)
            )
        """)

        # Create indexes on classes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_class_name ON classes(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_class_namespace ON classes(namespace)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_class_full_name ON classes(full_name)")

        # Methods table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS methods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                signature TEXT NOT NULL,
                return_type TEXT,
                description TEXT,
                is_static BOOLEAN DEFAULT 0,
                is_const BOOLEAN DEFAULT 0,
                FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE
            )
        """)

        # Create indexes on methods
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_method_class ON methods(class_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_method_name ON methods(name)")

        # Method parameters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS method_params (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                method_id INTEGER NOT NULL,
                param_order INTEGER NOT NULL,
                param_name TEXT,
                param_type TEXT NOT NULL,
                default_value TEXT,
                FOREIGN KEY(method_id) REFERENCES methods(id) ON DELETE CASCADE
            )
        """)

        # Create index on method_params
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_param_method ON method_params(method_id)"
        )

        # Full-text search virtual table
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
                content_type,
                name,
                description,
                content=''
            )
        """)

        self.conn.commit()
        console.print("[green]Database schema created[/green]")

    def insert_classes(self, classes: List[OpenStudioClass], version: str, source_url: str):
        """
        Insert classes and their methods into the database

        Args:
            classes: List of OpenStudioClass objects
            version: OpenStudio version (e.g., "3.9.0")
            source_url: Base URL of documentation
        """
        cursor = self.conn.cursor()

        console.print(f"[cyan]Inserting {len(classes)} classes into database...[/cyan]")

        total_methods = 0

        for cls in track(classes, description="Inserting classes..."):
            # Insert class
            cursor.execute(
                """
                INSERT INTO classes (name, namespace, full_name, description, parent_class, doc_url)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    cls.name,
                    cls.namespace,
                    cls.full_name,
                    cls.description,
                    cls.parent_class,
                    cls.doc_url,
                ),
            )

            class_id = cursor.lastrowid

            # Insert into full-text search
            cursor.execute(
                """
                INSERT INTO search_index (content_type, name, description)
                VALUES (?, ?, ?)
            """,
                ("class", cls.name, cls.description or ""),
            )

            # Insert methods
            for method in cls.methods:
                cursor.execute(
                    """
                    INSERT INTO methods (class_id, name, signature, return_type, description, is_static, is_const)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        class_id,
                        method.name,
                        method.signature,
                        method.return_type,
                        method.description,
                        method.is_static,
                        method.is_const,
                    ),
                )

                method_id = cursor.lastrowid
                total_methods += 1

                # Insert into full-text search
                cursor.execute(
                    """
                    INSERT INTO search_index (content_type, name, description)
                    VALUES (?, ?, ?)
                """,
                    ("method", method.name, method.description or ""),
                )

                # Insert parameters
                for idx, param in enumerate(method.parameters):
                    cursor.execute(
                        """
                        INSERT INTO method_params (method_id, param_order, param_name, param_type, default_value)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (method_id, idx, param.name, param.param_type, param.default_value),
                    )

        # Insert metadata
        cursor.execute(
            """
            INSERT OR REPLACE INTO metadata (version, scraped_at, source_url, total_classes, total_methods)
            VALUES (?, ?, ?, ?, ?)
        """,
            (version, datetime.now().isoformat(), source_url, len(classes), total_methods),
        )

        self.conn.commit()
        console.print(f"[green]Inserted {len(classes)} classes and {total_methods} methods[/green]")

    def validate_database(self):
        """Validate database contents"""
        cursor = self.conn.cursor()

        # Get counts
        cursor.execute("SELECT COUNT(*) FROM classes")
        class_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM methods")
        method_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM method_params")
        param_count = cursor.fetchone()[0]

        # Get metadata
        cursor.execute("SELECT * FROM metadata")
        metadata = cursor.fetchone()

        console.print("\n[bold cyan]Database Validation[/bold cyan]")
        console.print(f"Classes: {class_count}")
        console.print(f"Methods: {method_count}")
        console.print(f"Parameters: {param_count}")

        if metadata:
            console.print(f"Version: {metadata[0]}")
            console.print(f"Scraped at: {metadata[1]}")
            console.print(f"Source: {metadata[2]}")

        # Get average methods per class
        cursor.execute("SELECT AVG(method_count) FROM (SELECT COUNT(*) as method_count FROM methods GROUP BY class_id)")
        avg_methods = cursor.fetchone()[0]
        if avg_methods:
            console.print(f"Average methods per class: {avg_methods:.1f}")
        else:
            console.print("Average methods per class: N/A")

        # Check for classes with no methods (might indicate parsing issues)
        cursor.execute("SELECT COUNT(*) FROM classes WHERE id NOT IN (SELECT DISTINCT class_id FROM methods)")
        classes_without_methods = cursor.fetchone()[0]
        if classes_without_methods > 0:
            console.print(
                f"[yellow]Warning: {classes_without_methods} classes have no methods[/yellow]"
            )

        # Sample a few classes
        cursor.execute("""
            SELECT c.name, c.namespace, COUNT(m.id) as method_count
            FROM classes c
            LEFT JOIN methods m ON c.id = m.class_id
            GROUP BY c.id
            ORDER BY method_count DESC
            LIMIT 5
        """)

        console.print("\n[bold]Top 5 classes by method count:[/bold]")
        for row in cursor.fetchall():
            console.print(f"  {row[1]}::{row[0]} - {row[2]} methods")

    def optimize_database(self):
        """Optimize database for size and performance"""
        console.print("[cyan]Optimizing database...[/cyan]")

        cursor = self.conn.cursor()

        # Analyze tables for query optimization
        cursor.execute("ANALYZE")

        # Vacuum to reclaim space and defragment
        cursor.execute("VACUUM")

        self.conn.commit()
        console.print("[green]Database optimized[/green]")


def build_database(
    classes: List[OpenStudioClass],
    db_path: Path,
    version: str = "3.9.0",
    source_url: str = "https://s3.amazonaws.com/openstudio-sdk-documentation/cpp/OpenStudio-3.9.0-doc/model/html/",
):
    """
    Build SQLite database from scraped classes

    Args:
        classes: List of OpenStudioClass objects
        db_path: Path to output database file
        version: OpenStudio version
        source_url: Base URL of documentation
    """
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing database if it exists
    if db_path.exists():
        console.print(f"[yellow]Removing existing database: {db_path}[/yellow]")
        db_path.unlink()

    with DatabaseBuilder(db_path) as builder:
        builder.create_schema()
        builder.insert_classes(classes, version, source_url)
        builder.validate_database()
        builder.optimize_database()

    # Get final database size
    db_size_mb = db_path.stat().st_size / (1024 * 1024)
    console.print(f"\n[bold green]Database created: {db_path}[/bold green]")
    console.print(f"[bold green]Size: {db_size_mb:.2f} MB[/bold green]")
