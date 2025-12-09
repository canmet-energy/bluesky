"""NECB Database Query Interface - V2 Parser

Query interface for cached NECB table data in SQLite database.
Retrieves parsed tables without expensive PDF re-parsing.

Usage:
    query = NECBDatabaseQuery(db_path="necb.db")

    # Get specific table as Pydantic model
    table = query.get_table(vintage="2020", table_number="3.2.2.2")

    # List available tables
    tables = query.list_tables(vintage="2020")

    # Get raw metadata
    metadata = query.get_table_metadata(vintage="2020", table_number="3.2.2.2")
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from .schemas import get_schema_for_table


class NECBDatabaseQuery:
    """Query interface for NECB database (cached table data)"""

    def __init__(self, db_path: str | Path):
        """
        Initialize database query interface

        Args:
            db_path: Path to SQLite database file

        Raises:
            FileNotFoundError: If database doesn't exist
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

    def get_table(
        self, vintage: str, table_number: str, return_raw: bool = False
    ) -> BaseModel | dict | None:
        """
        Get parsed table as Pydantic model

        Args:
            vintage: NECB vintage (e.g., "2020")
            table_number: Table number (e.g., "3.2.2.2")
            return_raw: If True, return raw dict instead of Pydantic model

        Returns:
            Pydantic model instance or dict if return_raw=True, None if not found

        Example:
            >>> query = NECBDatabaseQuery("necb.db")
            >>> table = query.get_table("2020", "3.2.2.2")
            >>> print(table.vintage)
            '2020'
            >>> print(len(table.assemblies))
            3
        """
        # Normalize table number
        normalized_table = table_number.replace("Table ", "").strip()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get table metadata
        cursor.execute(
            """
            SELECT id, table_number, title, headers
            FROM necb_tables
            WHERE vintage = ? AND (
                table_number = ? OR
                table_number = ? OR
                table_number = ?
            )
        """,
            (
                vintage,
                f"Table {normalized_table}.",
                f"Table {normalized_table}",
                normalized_table,
            ),
        )

        table_row = cursor.fetchone()
        if not table_row:
            conn.close()
            return None

        table_id = table_row[0]

        # Get table rows
        cursor.execute(
            """
            SELECT row_data FROM necb_table_rows
            WHERE table_id = ?
        """,
            (table_id,),
        )

        rows = [json.loads(row[0]) for row in cursor.fetchall()]
        conn.close()

        if not rows:
            return None

        # Reconstruct table data
        reconstructed = self._reconstruct_table_data(
            vintage=vintage,
            table_number=normalized_table,
            rows=rows,
        )

        if return_raw:
            return reconstructed

        # Convert to Pydantic model
        schema = get_schema_for_table(normalized_table)
        if schema is None:
            # No schema registered - return raw dict
            return reconstructed

        try:
            return schema(**reconstructed)
        except ValidationError as e:
            print(f"Warning: Failed to validate cached data: {e}")
            return reconstructed if return_raw else None

    def _reconstruct_table_data(
        self, vintage: str, table_number: str, rows: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Reconstruct table data from database rows

        Args:
            vintage: NECB vintage
            table_number: Table number
            rows: List of row data dicts

        Returns:
            Reconstructed table data dict (ready for Pydantic validation)
        """
        # Detect table structure based on row keys
        if len(rows) > 0:
            first_row = rows[0]

            # EnvelopeTable format (3.2.2.2, 3.2.2.3)
            if "assembly_type" in first_row and "zone_4_max_u" in first_row:
                return {
                    "vintage": vintage,
                    "table_number": table_number,
                    "assemblies": rows,
                }

            # LightingTable format (4.2.1.3, 4.2.1.5)
            if "building_type" in first_row and "max_lpd" in first_row:
                return {
                    "vintage": vintage,
                    "table_number": table_number,
                    "requirements": rows,
                }

            # PumpPowerTable format (5.2.6.3)
            if "hydronic_system_type" in first_row and "max_total_pump_power" in first_row:
                return {
                    "vintage": vintage,
                    "table_number": table_number,
                    "requirements": rows,
                }

            # SWHEquipmentTable format (6.2.2.1)
            if "equipment_type" in first_row and "efficiency_metric" in first_row:
                return {
                    "vintage": vintage,
                    "table_number": table_number,
                    "equipment": rows,
                }

            # OccupancySensorTable format (8.4.4.6(3))
            if "space_type" in first_row and "sensor_required" in first_row:
                return {
                    "vintage": vintage,
                    "table_number": table_number,
                    "requirements": rows,
                }

            # HVACTable format (8.4.4.8, 8.4.4.13, 8.4.4.14)
            if "equipment_type" in first_row and "performance_metric" in first_row:
                return {
                    "vintage": vintage,
                    "table_number": table_number,
                    "equipment": rows,
                }

            # Generic format for other tables
            # Try to detect list-based structure
            if len(rows) > 1:
                # Multiple rows - likely a list field
                # Try common field names
                for list_field in ["requirements", "equipment", "assemblies", "sensors"]:
                    return {
                        "vintage": vintage,
                        "table_number": table_number,
                        list_field: rows,
                    }

        # Fallback: single row with all fields
        result = {
            "vintage": vintage,
            "table_number": table_number,
        }
        if rows:
            result.update(rows[0])
        return result

    def list_tables(self, vintage: str | None = None) -> list[dict[str, Any]]:
        """
        List available tables in database

        Args:
            vintage: Filter by vintage (e.g., "2020"), or None for all

        Returns:
            List of table metadata dicts:
            [
                {
                    "vintage": "2020",
                    "table_number": "3.2.2.2",
                    "title": "...",
                    "page_number": 73,
                    "row_count": 3
                },
                ...
            ]

        Example:
            >>> query = NECBDatabaseQuery("necb.db")
            >>> tables = query.list_tables(vintage="2020")
            >>> print(f"Found {len(tables)} tables for NECB 2020")
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if vintage:
            cursor.execute(
                """
                SELECT
                    t.vintage,
                    t.table_number,
                    t.title,
                    t.page_number,
                    COUNT(r.id) as row_count
                FROM necb_tables t
                LEFT JOIN necb_table_rows r ON t.id = r.table_id
                WHERE t.vintage = ?
                GROUP BY t.id
                ORDER BY t.table_number
            """,
                (vintage,),
            )
        else:
            cursor.execute(
                """
                SELECT
                    t.vintage,
                    t.table_number,
                    t.title,
                    t.page_number,
                    COUNT(r.id) as row_count
                FROM necb_tables t
                LEFT JOIN necb_table_rows r ON t.id = r.table_id
                GROUP BY t.id
                ORDER BY t.vintage, t.table_number
            """
            )

        tables = []
        for row in cursor.fetchall():
            tables.append({
                "vintage": row[0],
                "table_number": row[1],
                "title": row[2],
                "page_number": row[3],
                "row_count": row[4],
            })

        conn.close()
        return tables

    def get_table_metadata(
        self, vintage: str, table_number: str
    ) -> dict[str, Any] | None:
        """
        Get table metadata without loading data

        Args:
            vintage: NECB vintage (e.g., "2020")
            table_number: Table number (e.g., "3.2.2.2")

        Returns:
            Metadata dict or None if not found:
            {
                "vintage": "2020",
                "table_number": "3.2.2.2",
                "title": "...",
                "headers": [...],
                "page_number": 73,
                "row_count": 3,
                "parser_method": "pymupdf",
                "llm_applied": True,
                "confidence": 0.95,
                "extraction_time": 4.73,
                "llm_time": 2.42
            }

        Example:
            >>> query = NECBDatabaseQuery("necb.db")
            >>> meta = query.get_table_metadata("2020", "3.2.2.2")
            >>> print(f"Confidence: {meta['confidence']:.2f}")
        """
        # Normalize table number
        normalized_table = table_number.replace("Table ", "").strip()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                t.vintage,
                t.table_number,
                t.title,
                t.headers,
                t.page_number,
                COUNT(r.id) as row_count,
                p.method_used,
                p.llm_applied,
                p.confidence,
                p.extraction_time,
                p.llm_time
            FROM necb_tables t
            LEFT JOIN necb_table_rows r ON t.id = r.table_id
            LEFT JOIN parser_metadata p ON t.id = p.table_id
            WHERE t.vintage = ? AND (
                t.table_number = ? OR
                t.table_number = ? OR
                t.table_number = ?
            )
            GROUP BY t.id
        """,
            (
                vintage,
                f"Table {normalized_table}.",
                f"Table {normalized_table}",
                normalized_table,
            ),
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "vintage": row[0],
            "table_number": row[1],
            "title": row[2],
            "headers": json.loads(row[3]),
            "page_number": row[4],
            "row_count": row[5],
            "parser_method": row[6],
            "llm_applied": bool(row[7]),
            "confidence": row[8],
            "extraction_time": row[9],
            "llm_time": row[10],
        }

    def get_database_statistics(self) -> dict[str, Any]:
        """
        Get overall database statistics

        Returns:
            Statistics dict:
            {
                "database_path": "/path/to/necb.db",
                "total_tables": 80,
                "total_rows": 450,
                "vintages": {
                    "2011": {"tables": 20, "rows": 110},
                    "2015": {"tables": 20, "rows": 112},
                    "2017": {"tables": 20, "rows": 115},
                    "2020": {"tables": 20, "rows": 113}
                },
                "methods": {
                    "pymupdf": {"count": 75, "avg_confidence": 0.92},
                    "marker": {"count": 5, "avg_confidence": 0.88}
                }
            }

        Example:
            >>> query = NECBDatabaseQuery("necb.db")
            >>> stats = query.get_database_statistics()
            >>> print(f"Total tables: {stats['total_tables']}")
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total tables and rows
        cursor.execute("SELECT COUNT(*) FROM necb_tables")
        total_tables = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM necb_table_rows")
        total_rows = cursor.fetchone()[0]

        # By vintage
        cursor.execute(
            """
            SELECT
                t.vintage,
                COUNT(DISTINCT t.id) as table_count,
                COUNT(r.id) as row_count
            FROM necb_tables t
            LEFT JOIN necb_table_rows r ON t.id = r.table_id
            GROUP BY t.vintage
            ORDER BY t.vintage
        """
        )

        vintages = {}
        for row in cursor.fetchall():
            vintages[row[0]] = {
                "tables": row[1],
                "rows": row[2],
            }

        # By parser method
        cursor.execute(
            """
            SELECT
                method_used,
                COUNT(*) as count,
                AVG(confidence) as avg_confidence,
                AVG(extraction_time) as avg_extraction_time,
                AVG(llm_time) as avg_llm_time
            FROM parser_metadata
            GROUP BY method_used
        """
        )

        methods = {}
        for row in cursor.fetchall():
            methods[row[0]] = {
                "count": row[1],
                "avg_confidence": round(row[2], 3),
                "avg_extraction_time": round(row[3], 2),
                "avg_llm_time": round(row[4], 2),
            }

        conn.close()

        return {
            "database_path": str(self.db_path),
            "total_tables": total_tables,
            "total_rows": total_rows,
            "vintages": vintages,
            "methods": methods,
        }

    def table_exists(self, vintage: str, table_number: str) -> bool:
        """
        Check if table exists in database (fast check)

        Args:
            vintage: NECB vintage (e.g., "2020")
            table_number: Table number (e.g., "3.2.2.2")

        Returns:
            True if table exists, False otherwise

        Example:
            >>> query = NECBDatabaseQuery("necb.db")
            >>> if query.table_exists("2020", "3.2.2.2"):
            ...     table = query.get_table("2020", "3.2.2.2")
        """
        normalized_table = table_number.replace("Table ", "").strip()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) FROM necb_tables
            WHERE vintage = ? AND (
                table_number = ? OR
                table_number = ? OR
                table_number = ?
            )
        """,
            (
                vintage,
                f"Table {normalized_table}.",
                f"Table {normalized_table}",
                normalized_table,
            ),
        )

        count = cursor.fetchone()[0]
        conn.close()

        return count > 0
