"""NECB Database Builder - V2 Parser

Builds SQLite database from NECB PDFs using the hybrid parser (PyMuPDF → LLM).

Database Schema:
- necb_tables: Table metadata (vintage, number, title, headers, page)
- necb_table_rows: Table data rows (JSON format)
- parser_metadata: Parser statistics and quality metrics
"""

import json
import re
import sqlite3
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .cache import TableCacheManager
from .config import ParserConfig
from .hybrid_parser import DocumentParseResult, HybridNECBParser, ParseResult
from .schemas import get_schema_for_table
from bluesky.necb.build import get_division_for_page


@dataclass
class BuildStats:
    """Statistics for database build"""

    total_tables: int = 0
    successful_tables: int = 0
    failed_tables: int = 0
    total_rows: int = 0
    total_duration: float = 0.0
    average_confidence: float = 0.0


class NECBDatabaseBuilder:
    """Builds NECB database from PDF using v2 hybrid parser"""

    def __init__(
        self,
        db_path: str | Path,
        config: ParserConfig | None = None,
        verbose: bool = False,
        llm_cache_dir: str | Path | None = None,
    ):
        """
        Initialize database builder

        Args:
            db_path: Path to SQLite database file
            config: Parser configuration (uses defaults if None)
            verbose: Enable verbose logging
            llm_cache_dir: Directory for caching LLM outputs (enables fast rebuilds)
        """
        self.db_path = Path(db_path)
        self.config = config or ParserConfig()
        self.verbose = verbose
        self.llm_cache_dir = Path(llm_cache_dir) if llm_cache_dir else None
        self.parser = HybridNECBParser(
            config=self.config,
            verbose=verbose,
            llm_cache_dir=self.llm_cache_dir,
        )

        if self.verbose:
            print(f"Database builder initialized")
            print(f"  Database: {self.db_path}")
            print(f"  Parser: Hybrid (PyMuPDF → LLM)")
            print(f"  LLM model: {self.config.llm_model}")

    def create_database_schema(self):
        """Create database tables"""
        if self.verbose:
            print("\nCreating database schema...")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tables metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS necb_tables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vintage TEXT NOT NULL,
                division TEXT,
                table_number TEXT NOT NULL,
                title TEXT,
                headers TEXT NOT NULL,  -- JSON array
                page_number INTEGER,
                UNIQUE(vintage, division, table_number)
            )
        """)

        # Table rows table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS necb_table_rows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_id INTEGER NOT NULL,
                row_data TEXT NOT NULL,  -- JSON object
                FOREIGN KEY (table_id) REFERENCES necb_tables(id)
            )
        """)

        # Parser metadata table (v2 specific)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parser_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_id INTEGER NOT NULL,
                method_used TEXT,  -- "pymupdf" or "marker"
                llm_applied INTEGER,  -- boolean
                confidence REAL,
                extraction_time REAL,  -- seconds
                llm_time REAL,  -- seconds
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (table_id) REFERENCES necb_tables(id)
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_necb_tables_vintage
            ON necb_tables(vintage)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_necb_tables_number
            ON necb_tables(table_number)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_necb_tables_division
            ON necb_tables(division)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_necb_table_rows_table_id
            ON necb_table_rows(table_id)
        """)

        conn.commit()
        conn.close()

        if self.verbose:
            print("✅ Database schema created")

    def insert_table(
        self,
        conn: sqlite3.Connection,
        result: ParseResult,
        table_title: str | None = None,
    ) -> int | None:
        """
        Insert parsed table into database

        Args:
            conn: Database connection
            result: ParseResult from hybrid parser
            table_title: Optional table title/caption

        Returns:
            Table ID if successful, None if failed
        """
        if not result.success or result.data is None:
            return None

        cursor = conn.cursor()

        # Extract headers and rows from Pydantic model
        headers, rows = self._extract_table_data(result.data)

        # Determine division from page number
        division = get_division_for_page(result.page_number, result.vintage)

        # Insert table metadata
        cursor.execute(
            """
            INSERT OR REPLACE INTO necb_tables
            (vintage, division, table_number, title, headers, page_number)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                result.vintage,
                division,
                f"Table {result.table_number}.",  # Normalize format
                table_title or f"Table {result.table_number}",
                json.dumps(headers),
                result.page_number + 1,  # Convert 0-indexed to 1-indexed
            ),
        )

        table_id = cursor.lastrowid

        # Insert table rows
        for row in rows:
            cursor.execute(
                """
                INSERT INTO necb_table_rows (table_id, row_data)
                VALUES (?, ?)
            """,
                (table_id, json.dumps(row)),
            )

        # Insert parser metadata
        cursor.execute(
            """
            INSERT INTO parser_metadata
            (table_id, method_used, llm_applied, confidence, extraction_time, llm_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                table_id,
                result.method_used,
                1 if result.llm_applied else 0,
                result.confidence,
                result.timing.get("pymupdf_extraction", 0.0),
                result.timing.get("llm_repair", 0.0),
            ),
        )

        conn.commit()

        if self.verbose:
            print(f"  ✅ Inserted table {result.table_number} ({len(rows)} rows)")

        return table_id

    def _extract_table_data(self, data: BaseModel) -> tuple[list[str], list[dict[str, Any]]]:
        """
        Extract headers and rows from Pydantic model

        Args:
            data: Validated Pydantic model (e.g., EnvelopeTable)

        Returns:
            (headers, rows) tuple
        """
        # Convert Pydantic model to dict
        data_dict = data.model_dump()

        # Determine table type and extract accordingly
        if "assemblies" in data_dict:
            # EnvelopeTable format (3.2.2.2, 3.2.2.3)
            headers = [
                "Assembly Type",
                "Zone 4 (< 3000)",
                "Zone 5 (3000-3999)",
                "Zone 6 (4000-4999)",
                "Zone 7A (5000-5999)",
                "Zone 7B (6000-6999)",
                "Zone 8 (≥ 7000)",
            ]

            rows = []
            for assembly in data_dict["assemblies"]:
                rows.append({
                    "assembly_type": assembly["assembly_type"],
                    "zone_4_max_u": assembly["zone_4_max_u"],
                    "zone_5_max_u": assembly["zone_5_max_u"],
                    "zone_6_max_u": assembly["zone_6_max_u"],
                    "zone_7a_max_u": assembly["zone_7a_max_u"],
                    "zone_7b_max_u": assembly["zone_7b_max_u"],
                    "zone_8_max_u": assembly["zone_8_max_u"],
                })

            return headers, rows

        # HVACCoefficientTable format (5.3.2.8.-A through -AA)
        if "coefficients" in data_dict and "hvac_system_type" in data_dict:
            headers = [
                "Curve Name",
                "Description",
                "Coefficient A",
                "Coefficient B",
                "Coefficient C",
                "Coefficient D",
                "Coefficient E",
                "Coefficient F",
                "Min Value",
                "Max Value",
            ]

            rows = []
            for coef in data_dict["coefficients"]:
                rows.append({
                    "curve_name": coef["curve_name"],
                    "description": coef.get("description"),
                    "coefficient_a": coef.get("coefficient_a"),
                    "coefficient_b": coef.get("coefficient_b"),
                    "coefficient_c": coef.get("coefficient_c"),
                    "coefficient_d": coef.get("coefficient_d"),
                    "coefficient_e": coef.get("coefficient_e"),
                    "coefficient_f": coef.get("coefficient_f"),
                    "minimum_value": coef.get("minimum_value"),
                    "maximum_value": coef.get("maximum_value"),
                })

            return headers, rows

        # ObjectivesTable format (x.5.1.1)
        if "objectives" in data_dict and "section_name" in data_dict:
            headers = [
                "Section Reference",
                "Objectives",
                "Functional Statements",
            ]

            rows = []
            for obj in data_dict["objectives"]:
                rows.append({
                    "section_reference": obj["section_reference"],
                    "objectives": obj.get("objectives"),
                    "functional_statements": obj.get("functional_statements"),
                })

            return headers, rows

        # OperatingScheduleTable format (A-8.4.3.2.(1)x)
        if "systems" in data_dict and "building_type" in data_dict:
            headers = [
                "System Type",
                "Day Type",
                "Hour",
                "Value",
            ]

            rows = []
            for system in data_dict["systems"]:
                system_type = system["system_type"]
                for schedule in system["schedules"]:
                    day_type = schedule["day_type"]
                    for hour_entry in schedule["hours"]:
                        rows.append({
                            "system_type": system_type,
                            "day_type": day_type,
                            "hour": hour_entry["hour"],
                            "value": hour_entry["value"],
                        })

            return headers, rows

        # ModelingGuidanceTable format (A-8.4.3.2.(2)x, A-8.4.3.3.(1)x)
        if "entries" in data_dict and "guidance_type" in data_dict:
            headers = [
                "Building/Space Type",
                "Occupancy Density",
                "Lighting Power Density",
                "Equipment Power Density",
                "Ventilation Rate",
                "Hot Water Usage",
                "Schedule Reference",
            ]

            rows = []
            for entry in data_dict["entries"]:
                rows.append({
                    "building_or_space_type": entry["building_or_space_type"],
                    "occupancy_density": entry.get("occupancy_density"),
                    "lighting_power_density": entry.get("lighting_power_density"),
                    "equipment_power_density": entry.get("equipment_power_density"),
                    "ventilation_rate": entry.get("ventilation_rate"),
                    "hot_water_usage": entry.get("hot_water_usage"),
                    "schedule_reference": entry.get("schedule_reference"),
                })

            return headers, rows

        # PartLoadPerformanceTable format (8.4.4.21.-A through -G)
        if "performance_curves" in data_dict and "equipment_category" in data_dict:
            headers = [
                "Equipment Type",
                "Performance Curve",
                "Coefficient A",
                "Coefficient B",
                "Coefficient C",
                "Coefficient D",
                "Coefficient E",
                "Coefficient F",
                "Min Output",
                "Max Output",
            ]

            rows = []
            for curve in data_dict["performance_curves"]:
                rows.append({
                    "equipment_type": curve["equipment_type"],
                    "performance_curve": curve["performance_curve"],
                    "coefficient_a": curve.get("coefficient_a"),
                    "coefficient_b": curve.get("coefficient_b"),
                    "coefficient_c": curve.get("coefficient_c"),
                    "coefficient_d": curve.get("coefficient_d"),
                    "coefficient_e": curve.get("coefficient_e"),
                    "coefficient_f": curve.get("coefficient_f"),
                    "minimum_output": curve.get("minimum_output"),
                    "maximum_output": curve.get("maximum_output"),
                })

            return headers, rows

        # HVACSystemTypesTable format (5.3.1.1.-A)
        if "systems" in data_dict and data_dict.get("table_number") == "5.3.1.1.-A":
            headers = [
                "System Number",
                "System Name",
                "Heating Type",
                "Cooling Type",
                "Distribution Type",
                "Terminal Type",
                "Description",
            ]

            rows = []
            for system in data_dict["systems"]:
                rows.append({
                    "system_number": system["system_number"],
                    "system_name": system["system_name"],
                    "heating_type": system.get("heating_type"),
                    "cooling_type": system.get("cooling_type"),
                    "distribution_type": system.get("distribution_type"),
                    "terminal_type": system.get("terminal_type"),
                    "description": system.get("description"),
                })

            return headers, rows

        # SWHSystemTypesTable format (6.3.1.1)
        if "systems" in data_dict and data_dict.get("table_number") == "6.3.1.1":
            headers = [
                "System Number",
                "System Name",
                "Heater Type",
                "Fuel Type",
                "Distribution Type",
                "Description",
            ]

            rows = []
            for system in data_dict["systems"]:
                rows.append({
                    "system_number": system["system_number"],
                    "system_name": system["system_name"],
                    "heater_type": system.get("heater_type"),
                    "fuel_type": system.get("fuel_type"),
                    "distribution_type": system.get("distribution_type"),
                    "description": system.get("description"),
                })

            return headers, rows

        # ComponentFactorTable format (5.3.2.2, 5.3.2.3, 5.3.2.7, 6.3.2.5)
        if "factors" in data_dict and "table_type" in data_dict:
            headers = [
                "Component Type",
                "Parameter Name",
                "Factor Value",
                "Base Value",
                "Units",
                "Applicability",
                "Notes",
            ]

            rows = []
            for factor in data_dict["factors"]:
                rows.append({
                    "component_type": factor["component_type"],
                    "parameter_name": factor.get("parameter_name"),
                    "factor_value": factor.get("factor_value"),
                    "base_value": factor.get("base_value"),
                    "units": factor.get("units"),
                    "applicability": factor.get("applicability"),
                    "notes": factor.get("notes"),
                })

            return headers, rows

        # ReferenceTable format (1-1, 2-1, 1.3.1.2, etc.) - Phase 4
        if "rows" in data_dict and "content_type" in data_dict:
            headers = [
                "Key",
                "Description",
                "Reference",
                "Notes",
            ]

            rows = []
            for row in data_dict["rows"]:
                rows.append({
                    "key": row["key"],
                    "description": row["description"],
                    "reference": row.get("reference"),
                    "notes": row.get("notes"),
                })

            return headers, rows

        # HVACSystemSelectionTable format (8.4.4.7.-A, 8.4.4.8.A/B) - Phase 4 fix
        if "selections" in data_dict:
            headers = [
                "Building Type",
                "System Number",
                "Conditions",
            ]

            rows = []
            for selection in data_dict["selections"]:
                rows.append({
                    "building_type": selection["building_type"],
                    "system_number": selection["system_number"],
                    "conditions": selection.get("conditions"),
                })

            return headers, rows

        # HeatPumpSystemTable format (8.4.4.13, 8.4.4.14) - Phase 4 fix
        if "systems" in data_dict and data_dict.get("table_number", "").startswith("8.4.4.1"):
            headers = [
                "System Number",
                "Type of System",
                "Fan Control",
                "Terminal Heating Type",
            ]

            rows = []
            for system in data_dict["systems"]:
                rows.append({
                    "system_number": system["system_number"],
                    "type_of_system": system.get("type_of_system"),
                    "fan_control": system.get("fan_control"),
                    "terminal_heating_type": system.get("terminal_heating_type"),
                })

            return headers, rows

        # ClimateDesignDataTable format (C-1) - Phase 16
        if "rows" in data_dict and data_dict.get("table_number") == "C-1":
            headers = [
                "Location",
                "Elevation (m)",
                "January 2.5% (°C)",
                "January 1% (°C)",
                "July Dry (°C)",
                "July Wet (°C)",
                "Degree-Days Below 18°C",
                "Degree-Days Below 15°C",
                "Wind 1/10 (kPa)",
                "Wind 1/50 (kPa)",
            ]

            rows = []
            for row in data_dict["rows"]:
                rows.append({
                    "location": row["location"],
                    "elevation_m": row.get("elevation_m"),
                    "design_temp_jan_2_5_pct": row.get("design_temp_jan_2_5_pct"),
                    "design_temp_jan_1_pct": row.get("design_temp_jan_1_pct"),
                    "design_temp_july_dry": row.get("design_temp_july_dry"),
                    "design_temp_july_wet": row.get("design_temp_july_wet"),
                    "degree_days_below_18c": row.get("degree_days_below_18c"),
                    "degree_days_below_15c": row.get("degree_days_below_15c"),
                    "wind_pressure_1_10": row.get("wind_pressure_1_10"),
                    "wind_pressure_1_50": row.get("wind_pressure_1_50"),
                })

            return headers, rows

        # Generic fallback for other table types
        # Extract field names as headers
        headers = list(data_dict.keys())
        rows = [data_dict]  # Single row with all fields

        return headers, rows

    def build_document(
        self,
        pdf_path: str | Path,
        vintage: str,
        table_specs: list[dict[str, Any]],
    ) -> BuildStats:
        """
        Parse NECB document and populate database

        Args:
            pdf_path: Path to NECB PDF
            vintage: NECB vintage (e.g., "2020")
            table_specs: List of table specifications:
                [{"table_number": "3.2.2.2", "page_num": 72, "title": "..."}]

        Returns:
            BuildStats with parsing and insertion statistics
        """
        if self.verbose:
            print(f"\n{'='*80}")
            print(f"Building database from NECB {vintage}")
            print(f"PDF: {Path(pdf_path).name}")
            print(f"Tables to parse: {len(table_specs)}")
            print(f"{'='*80}\n")

        start_time = time.time()

        # Parse document
        doc_result = self.parser.parse_document(
            pdf_path=pdf_path, vintage=vintage, table_specs=table_specs
        )

        # Insert into database
        conn = sqlite3.connect(self.db_path)

        stats = BuildStats()
        stats.total_tables = len(doc_result.tables)
        total_confidence = 0.0

        for i, result in enumerate(doc_result.tables, 1):
            spec = table_specs[i - 1] if i <= len(table_specs) else {}
            table_title = spec.get("title")

            if result.success:
                table_id = self.insert_table(conn, result, table_title)
                if table_id:
                    stats.successful_tables += 1
                    stats.total_rows += len(result.data.assemblies) if hasattr(result.data, "assemblies") else 1
                    total_confidence += result.confidence
                else:
                    stats.failed_tables += 1
            else:
                stats.failed_tables += 1
                if self.verbose:
                    print(f"  ❌ Failed table {result.table_number}: {result.errors}")

        conn.close()

        stats.total_duration = time.time() - start_time
        stats.average_confidence = (
            total_confidence / stats.successful_tables if stats.successful_tables > 0 else 0.0
        )

        if self.verbose:
            print(f"\n{'='*80}")
            print(f"Database build complete")
            print(f"  Success: {stats.successful_tables}/{stats.total_tables} tables")
            print(f"  Failed: {stats.failed_tables}")
            print(f"  Total rows: {stats.total_rows}")
            print(f"  Average confidence: {stats.average_confidence:.2f}")
            print(f"  Duration: {stats.total_duration:.1f}s")
            print(f"{'='*80}\n")

        return stats

    def get_build_statistics(self) -> dict[str, Any]:
        """Get statistics about current database"""
        if not self.db_path.exists():
            return {"error": "Database does not exist"}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count tables by vintage
        cursor.execute("""
            SELECT vintage, COUNT(*) as count
            FROM necb_tables
            GROUP BY vintage
            ORDER BY vintage
        """)

        vintage_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # Count total rows
        cursor.execute("SELECT COUNT(*) FROM necb_table_rows")
        total_rows = cursor.fetchone()[0]

        # Average confidence by method
        cursor.execute("""
            SELECT method_used, AVG(confidence) as avg_conf, COUNT(*) as count
            FROM parser_metadata
            GROUP BY method_used
        """)

        method_stats = []
        for row in cursor.fetchall():
            method_stats.append({
                "method": row[0],
                "average_confidence": round(row[1], 3),
                "count": row[2],
            })

        conn.close()

        return {
            "database_path": str(self.db_path),
            "vintage_counts": vintage_counts,
            "total_tables": sum(vintage_counts.values()),
            "total_rows": total_rows,
            "method_statistics": method_stats,
        }

    def build_from_cache(
        self,
        cache_dir: str | Path,
        vintages: list[str] | None = None,
    ) -> BuildStats:
        """
        Build database from cached LLM outputs only (no PDF parsing, no LLM calls).

        This enables fast database rebuilds after schema changes without expensive
        LLM API calls.

        Args:
            cache_dir: Path to cache directory containing {vintage}/{table}.md files
            vintages: List of vintages to process (default: all cached)

        Returns:
            BuildStats with results
        """
        if self.verbose:
            print(f"\n{'='*80}")
            print("Building database from cache (no LLM calls)")
            print(f"Cache directory: {cache_dir}")
            print(f"{'='*80}\n")

        start_time = time.time()

        # Initialize cache manager
        cache = TableCacheManager(cache_dir, verbose=self.verbose)

        # Get all cached tables
        cached_tables = cache.list_cached_tables()
        if vintages:
            cached_tables = [(v, t) for v, t in cached_tables if v in vintages]

        if self.verbose:
            print(f"Found {len(cached_tables)} cached tables")
            if vintages:
                print(f"Filtering to vintages: {vintages}")

        # Create database schema
        self.create_database_schema()

        # Connect to database
        conn = sqlite3.connect(self.db_path)

        stats = BuildStats()
        stats.total_tables = len(cached_tables)
        total_confidence = 0.0

        for vintage, table_number in cached_tables:
            entry = cache.load(vintage, table_number)
            if not entry or not entry.success:
                stats.failed_tables += 1
                if self.verbose:
                    print(f"  ❌ Cache entry invalid: {vintage}/{table_number}")
                continue

            # Get schema for this table
            schema = get_schema_for_table(entry.table_number)
            if not schema:
                stats.failed_tables += 1
                if self.verbose:
                    print(f"  ❌ No schema for: {entry.table_number}")
                continue

            # Validate cached JSON against schema
            try:
                # Extract JSON from markdown code fences if present
                json_str = entry.repaired_json
                if json_str.strip().startswith("```"):
                    # Remove markdown code fences
                    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", json_str)
                    if json_match:
                        json_str = json_match.group(1)

                data = json.loads(json_str)
                validated = schema(**data)

                # Create ParseResult for insert_table
                result = ParseResult(
                    success=True,
                    data=validated,
                    table_number=entry.table_number,
                    vintage=entry.vintage,
                    page_number=entry.page_number,
                    method_used=f"cached_{entry.method_used}",
                    llm_applied=False,
                    errors=[],
                    timing={"cache_load": 0.01},
                    confidence=entry.confidence,
                    validation_passed=True,
                    raw_markdown=entry.raw_markdown,
                    repaired_markdown=entry.repaired_json,
                )

                # Insert into database
                table_id = self.insert_table(conn, result)
                if table_id:
                    stats.successful_tables += 1
                    total_confidence += entry.confidence
                    # Count rows if possible
                    if hasattr(validated, "assemblies"):
                        stats.total_rows += len(validated.assemblies)
                    elif hasattr(validated, "coefficients"):
                        stats.total_rows += len(validated.coefficients)
                    elif hasattr(validated, "objectives"):
                        stats.total_rows += len(validated.objectives)
                    else:
                        stats.total_rows += 1
                else:
                    stats.failed_tables += 1

            except Exception as e:
                stats.failed_tables += 1
                if self.verbose:
                    print(f"  ❌ Failed to load {vintage}/{table_number}: {e}")

        conn.close()

        stats.total_duration = time.time() - start_time
        stats.average_confidence = (
            total_confidence / stats.successful_tables if stats.successful_tables > 0 else 0.0
        )

        if self.verbose:
            print(f"\n{'='*80}")
            print("Cache-based build complete")
            print(f"  Success: {stats.successful_tables}/{stats.total_tables} tables")
            print(f"  Failed: {stats.failed_tables}")
            print(f"  Total rows: {stats.total_rows}")
            print(f"  Average confidence: {stats.average_confidence:.2f}")
            print(f"  Duration: {stats.total_duration:.1f}s")
            print(f"{'='*80}\n")

        return stats
