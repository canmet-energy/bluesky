"""
NECB Database Builder

Builds SQLite database from parsed NECB data.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict

from rich.console import Console
from rich.progress import track

from .necb_pdf_parser import parse_all_necb_pdfs

console = Console()


class NECBDatabaseBuilder:
    """Builds SQLite database from NECB data"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def create_schema(self):
        """Create NECB database schema"""
        cursor = self.conn.cursor()

        # Metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS necb_metadata (
                vintage TEXT PRIMARY KEY,
                parsed_at TEXT NOT NULL,
                total_sections INTEGER,
                total_tables INTEGER,
                total_requirements INTEGER
            )
        """)

        # Sections
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS necb_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vintage TEXT NOT NULL,
                section_number TEXT NOT NULL,
                title TEXT,
                content TEXT,
                page_number INTEGER,
                UNIQUE(vintage, section_number)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_necb_sections_vintage ON necb_sections(vintage)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_necb_sections_number ON necb_sections(section_number)")

        # Tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS necb_tables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vintage TEXT NOT NULL,
                table_number TEXT NOT NULL,
                title TEXT,
                headers TEXT,  -- JSON array
                page_number INTEGER,
                UNIQUE(vintage, table_number, page_number)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_necb_tables_vintage ON necb_tables(vintage)")

        # Table rows
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS necb_table_rows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_id INTEGER NOT NULL,
                row_data TEXT,  -- JSON array
                FOREIGN KEY(table_id) REFERENCES necb_tables(id) ON DELETE CASCADE
            )
        """)

        # Requirements
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS necb_requirements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vintage TEXT NOT NULL,
                section TEXT,
                requirement_type TEXT,
                description TEXT,
                value TEXT,
                unit TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_necb_req_vintage ON necb_requirements(vintage)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_necb_req_type ON necb_requirements(requirement_type)")

        # Full-text search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS necb_search USING fts5(
                vintage,
                content_type,
                title,
                content
            )
        """)

        self.conn.commit()
        console.print("[green]NECB database schema created[/green]")

    def insert_data(self, parsed_data: Dict[str, Dict]):
        """Insert parsed NECB data into database"""
        cursor = self.conn.cursor()

        for vintage, data in parsed_data.items():
            console.print(f"[cyan]Inserting NECB {vintage} data...[/cyan]")

            # Insert sections
            for section in track(data["sections"], description=f"Sections {vintage}"):
                cursor.execute("""
                    INSERT OR REPLACE INTO necb_sections
                    (vintage, section_number, title, content, page_number)
                    VALUES (?, ?, ?, ?, ?)
                """, (vintage, section.section_number, section.title, section.content, section.page_number))

                # Add to search index
                cursor.execute("""
                    INSERT INTO necb_search (vintage, content_type, title, content)
                    VALUES (?, ?, ?, ?)
                """, (vintage, "section", section.title, section.content[:500]))

            # Insert tables
            for table in track(data["tables"], description=f"Tables {vintage}"):
                import json

                cursor.execute("""
                    INSERT OR REPLACE INTO necb_tables
                    (vintage, table_number, title, headers, page_number)
                    VALUES (?, ?, ?, ?, ?)
                """, (vintage, table.table_number, table.title, json.dumps(table.headers), table.page_number))

                table_id = cursor.lastrowid

                # Insert table rows
                for row in table.rows:
                    cursor.execute("""
                        INSERT INTO necb_table_rows (table_id, row_data)
                        VALUES (?, ?)
                    """, (table_id, json.dumps(row)))

                # Add to search index
                cursor.execute("""
                    INSERT INTO necb_search (vintage, content_type, title, content)
                    VALUES (?, ?, ?, ?)
                """, (vintage, "table", table.title, " ".join(table.headers)))

            # Insert requirements
            for req in track(data["requirements"], description=f"Requirements {vintage}"):
                cursor.execute("""
                    INSERT INTO necb_requirements
                    (vintage, section, requirement_type, description, value, unit)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (vintage, req.section, req.requirement_type, req.description, req.value, req.unit))

            # Insert metadata
            cursor.execute("""
                INSERT OR REPLACE INTO necb_metadata
                (vintage, parsed_at, total_sections, total_tables, total_requirements)
                VALUES (?, ?, ?, ?, ?)
            """, (
                vintage,
                datetime.now().isoformat(),
                len(data["sections"]),
                len(data["tables"]),
                len(data["requirements"]),
            ))

        self.conn.commit()
        console.print("[green]NECB data inserted successfully[/green]")

    def validate(self):
        """Validate database"""
        cursor = self.conn.cursor()

        console.print("\n[bold cyan]NECB Database Validation:[/bold cyan]")

        for vintage in ["2011", "2015", "2017", "2020"]:
            cursor.execute("SELECT COUNT(*) FROM necb_sections WHERE vintage = ?", (vintage,))
            sections = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM necb_tables WHERE vintage = ?", (vintage,))
            tables = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM necb_requirements WHERE vintage = ?", (vintage,))
            requirements = cursor.fetchone()[0]

            console.print(f"\nNECB {vintage}:")
            console.print(f"  Sections: {sections}")
            console.print(f"  Tables: {tables}")
            console.print(f"  Requirements: {requirements}")


def build_necb_database(pdf_dir: Path, db_path: Path):
    """Build NECB database from PDFs"""
    # Parse PDFs
    parsed_data = parse_all_necb_pdfs(pdf_dir)

    # Build database
    if db_path.exists():
        console.print(f"[yellow]Removing existing database: {db_path}[/yellow]")
        db_path.unlink()

    with NECBDatabaseBuilder(db_path) as builder:
        builder.create_schema()
        builder.insert_data(parsed_data)
        builder.validate()

    db_size_mb = db_path.stat().st_size / (1024 * 1024)
    console.print(f"\n[bold green]NECB database created: {db_path}[/bold green]")
    console.print(f"[bold green]Size: {db_size_mb:.2f} MB[/bold green]")


if __name__ == "__main__":
    pdf_dir = Path(__file__).parent / "pdfs"
    db_path = Path(__file__).parent.parent.parent / "data" / "necb.db"

    build_necb_database(pdf_dir, db_path)
