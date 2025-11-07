"""
NECB Database Validation Script

Validates that all critical tables and data are present and correct in the NECB database.
Run this after building or updating the database.

Usage:
    python -m bluesky.mcp.validation.validate_necb_parsing
"""

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


@dataclass
class ValidationError:
    """Represents a validation error"""
    severity: str  # "ERROR", "WARNING", "INFO"
    vintage: str
    table_number: str
    page_number: Optional[int]
    message: str
    expected: Optional[str] = None
    actual: Optional[str] = None


@dataclass
class TableSchema:
    """Schema definition for a critical NECB table"""
    table_number: str
    name: str
    section_reference: str
    vintages: List[str]
    required_components: List[str]
    min_rows: int
    max_rows: Optional[int] = None
    required_headers: Optional[List[str]] = None


# Define schemas for critical tables
CRITICAL_TABLE_SCHEMAS = [
    TableSchema(
        table_number="Table 3.2.2.2.",
        name="Above-Ground Opaque Building Assemblies (Thermal Transmittance)",
        section_reference="3.2.2.2",
        vintages=["2011", "2015", "2017", "2020"],
        required_components=["Walls", "Roofs", "Floors"],
        min_rows=5,
        max_rows=20,
        required_headers=["Component", "Zone", "Heating"]
    ),
    TableSchema(
        table_number="Table 3.2.2.2.",
        name="Maximum FDWR",
        section_reference="3.2.2.2",
        vintages=["2011", "2015", "2017", "2020"],
        required_components=["HDD", "FDWR"],
        min_rows=10,  # Should have ~15 HDD ranges
        max_rows=20
    ),
    TableSchema(
        table_number="Table 3.2.2.3.",
        name="Fenestration Thermal Characteristics",
        section_reference="3.2.2.3",
        vintages=["2011", "2015", "2020"],
        required_components=["fenestration"],
        min_rows=2,
        max_rows=10
    ),
    TableSchema(
        table_number="Table 3.2.3.1.",
        name="Below-Grade Building Assemblies",
        section_reference="3.2.3.1",
        vintages=["2011", "2017", "2020"],
        required_components=["Walls", "Floors"],
        min_rows=3,
        max_rows=10
    ),
]


class NECBDatabaseValidator:
    """Validates NECB database for completeness and correctness"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.errors: List[ValidationError] = []

    def validate_all(self) -> Dict:
        """Run all validation checks"""
        console.print("[bold cyan]NECB Database Validation[/bold cyan]\n")
        console.print(f"Database: {self.db_path}\n")

        # 1. Check critical tables exist and are complete
        self.validate_critical_tables()

        # 2. Check for empty rows
        self.validate_empty_rows()

        # 3. Compare row counts across vintages
        self.validate_row_count_consistency()

        # 4. Check for duplicate table entries
        self.validate_duplicate_tables()

        # 5. Validate section references
        self.validate_section_references()

        # Print results
        self.print_results()

        return {
            "total_errors": len([e for e in self.errors if e.severity == "ERROR"]),
            "total_warnings": len([e for e in self.errors if e.severity == "WARNING"]),
            "errors": self.errors,
        }

    def validate_critical_tables(self):
        """Validate that all critical tables are present with expected content"""
        console.print("[bold]1. Validating Critical Tables[/bold]")

        cursor = self.conn.cursor()

        for schema in CRITICAL_TABLE_SCHEMAS:
            for vintage in schema.vintages:
                console.print(f"  Checking {vintage} {schema.table_number}...", end=" ")

                # Get all entries for this table
                cursor.execute("""
                    SELECT t.id, t.page_number, t.headers,
                           GROUP_CONCAT(r.row_data, '|||') as all_rows
                    FROM necb_tables t
                    LEFT JOIN necb_table_rows r ON t.id = r.table_id
                    WHERE t.vintage = ? AND t.table_number = ?
                    GROUP BY t.id
                """, (vintage, schema.table_number))

                results = cursor.fetchall()

                if not results:
                    self.errors.append(ValidationError(
                        severity="ERROR",
                        vintage=vintage,
                        table_number=schema.table_number,
                        page_number=None,
                        message=f"Table not found: {schema.name}",
                        expected="Table should exist",
                        actual="Not found in database"
                    ))
                    console.print("[red]❌ NOT FOUND[/red]")
                    continue

                # Combine all table entries (for multi-page tables)
                all_row_data = []
                total_rows = 0
                for table_id, page, headers, rows_concat in results:
                    if rows_concat:
                        rows = rows_concat.split('|||')
                        total_rows += len(rows)
                        all_row_data.extend(rows)

                # Check row count
                if total_rows < schema.min_rows:
                    self.errors.append(ValidationError(
                        severity="ERROR",
                        vintage=vintage,
                        table_number=schema.table_number,
                        page_number=results[0][1],
                        message=f"Too few rows in {schema.name}",
                        expected=f">= {schema.min_rows} rows",
                        actual=f"{total_rows} rows"
                    ))
                    console.print(f"[red]❌ TOO FEW ROWS ({total_rows})[/red]")
                    continue

                if schema.max_rows and total_rows > schema.max_rows:
                    self.errors.append(ValidationError(
                        severity="WARNING",
                        vintage=vintage,
                        table_number=schema.table_number,
                        page_number=results[0][1],
                        message=f"Unusually many rows in {schema.name}",
                        expected=f"<= {schema.max_rows} rows",
                        actual=f"{total_rows} rows"
                    ))

                # Check for required components
                all_data_str = " ".join(all_row_data).lower()
                missing_components = []
                for component in schema.required_components:
                    if component.lower() not in all_data_str:
                        missing_components.append(component)

                if missing_components:
                    self.errors.append(ValidationError(
                        severity="ERROR",
                        vintage=vintage,
                        table_number=schema.table_number,
                        page_number=results[0][1],
                        message=f"Missing required components in {schema.name}",
                        expected=", ".join(schema.required_components),
                        actual=f"Missing: {', '.join(missing_components)}"
                    ))
                    console.print(f"[red]❌ MISSING: {', '.join(missing_components)}[/red]")
                    continue

                console.print(f"[green]✓ OK ({total_rows} rows)[/green]")

        console.print()

    def validate_empty_rows(self):
        """Check for tables with excessive empty rows"""
        console.print("[bold]2. Checking for Empty Rows[/bold]")

        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT t.vintage, t.table_number, t.id, t.page_number,
                   COUNT(r.id) as total_rows,
                   SUM(CASE WHEN r.row_data = '["", "", ""]'
                             OR r.row_data = '[""]'
                             OR r.row_data = '["", ""]'
                             OR r.row_data LIKE '%["", "", "", ""]%'
                        THEN 1 ELSE 0 END) as empty_rows
            FROM necb_tables t
            LEFT JOIN necb_table_rows r ON t.id = r.table_id
            GROUP BY t.id
            HAVING empty_rows > 5
            ORDER BY empty_rows DESC
        """)

        results = cursor.fetchall()

        if results:
            console.print(f"  Found {len(results)} tables with >5 empty rows:\n")
            for vintage, table_num, table_id, page, total_rows, empty_rows in results:
                empty_pct = (empty_rows / total_rows * 100) if total_rows > 0 else 0

                self.errors.append(ValidationError(
                    severity="WARNING" if empty_pct < 50 else "ERROR",
                    vintage=vintage,
                    table_number=table_num,
                    page_number=page,
                    message=f"Table has {empty_pct:.0f}% empty rows",
                    expected="< 10% empty rows",
                    actual=f"{empty_rows}/{total_rows} empty"
                ))

                if empty_pct >= 50:
                    status_color = "red"
                    status = "❌"
                else:
                    status_color = "yellow"
                    status = "⚠️"

                console.print(f"  [{status_color}]{status} {vintage} {table_num} (ID {table_id}, Page {page}): "
                             f"{empty_rows}/{total_rows} empty ({empty_pct:.0f}%)[/{status_color}]")
        else:
            console.print("  [green]✓ No tables with excessive empty rows[/green]")

        console.print()

    def validate_row_count_consistency(self):
        """Check that similar tables have consistent row counts across vintages"""
        console.print("[bold]3. Checking Row Count Consistency Across Vintages[/bold]")

        cursor = self.conn.cursor()

        # Group by table number and compare row counts
        cursor.execute("""
            SELECT t.table_number,
                   t.vintage,
                   COUNT(DISTINCT t.id) as num_entries,
                   SUM((SELECT COUNT(*) FROM necb_table_rows WHERE table_id = t.id)) as total_rows
            FROM necb_tables t
            WHERE t.table_number LIKE 'Table 3.2.%'
               OR t.table_number LIKE 'Table 4.2.%'
               OR t.table_number LIKE 'Table 5.2.%'
            GROUP BY t.table_number, t.vintage
            ORDER BY t.table_number, t.vintage
        """)

        results = cursor.fetchall()

        # Group by table number
        table_groups = defaultdict(list)
        for table_num, vintage, num_entries, total_rows in results:
            table_groups[table_num].append((vintage, num_entries, total_rows))

        # Check variance
        issues_found = 0
        for table_num, vintage_data in table_groups.items():
            if len(vintage_data) < 2:
                continue  # Need at least 2 vintages to compare

            row_counts = [rows for _, _, rows in vintage_data if rows is not None and rows > 0]
            if not row_counts:
                continue

            max_rows = max(row_counts)
            min_rows = min(row_counts)

            # Flag if variance > 50%
            if max_rows > 0 and (max_rows - min_rows) / max_rows > 0.5:
                issues_found += 1
                if issues_found == 1:
                    console.print()  # First issue, add newline

                console.print(f"  [yellow]⚠️  {table_num}:[/yellow]")
                for vintage, entries, rows in vintage_data:
                    rows_display = rows if rows else 0
                    console.print(f"      {vintage}: {entries} entries, {rows_display} rows")

                # Add warning for largest variance
                vintages_str = ", ".join([v for v, _, _ in vintage_data])
                self.errors.append(ValidationError(
                    severity="WARNING",
                    vintage=vintages_str,
                    table_number=table_num,
                    page_number=None,
                    message=f"Large row count variance across vintages",
                    expected=f"Similar row counts (±50%)",
                    actual=f"Range: {min_rows} to {max_rows} rows"
                ))

        if issues_found == 0:
            console.print("  [green]✓ No significant row count variances found[/green]")

        console.print()

    def validate_duplicate_tables(self):
        """Report duplicate table numbers (expected for multi-page tables)"""
        console.print("[bold]4. Checking Duplicate Table Numbers[/bold]")

        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT vintage, table_number, COUNT(*) as count
            FROM necb_tables
            GROUP BY vintage, table_number
            HAVING COUNT(*) > 1
            ORDER BY count DESC
            LIMIT 10
        """)

        results = cursor.fetchall()

        if results:
            console.print(f"  Found {len(results)} table numbers with multiple entries (showing top 10):")
            console.print("  [dim]Note: Multiple entries are expected for tables spanning pages[/dim]\n")

            for vintage, table_num, count in results:
                # Check if entries are sequential pages (expected)
                cursor.execute("""
                    SELECT page_number FROM necb_tables
                    WHERE vintage = ? AND table_number = ?
                    ORDER BY page_number
                """, (vintage, table_num))

                pages = [row[0] for row in cursor.fetchall()]
                sequential = all(pages[i+1] - pages[i] == 1 for i in range(len(pages) - 1))

                if sequential:
                    status_color = "green"
                    status = "✓"
                else:
                    status_color = "yellow"
                    status = "⚠️"

                pages_str = ", ".join(map(str, pages))
                console.print(f"  [{status_color}]{status} {vintage} {table_num}: {count} entries (pages: {pages_str})[/{status_color}]")

                if not sequential:
                    self.errors.append(ValidationError(
                        severity="INFO",
                        vintage=vintage,
                        table_number=table_num,
                        page_number=None,
                        message="Non-sequential page numbers for duplicate table",
                        expected="Sequential pages",
                        actual=f"Pages: {pages_str}"
                    ))
        else:
            console.print("  [green]✓ No duplicate table numbers found[/green]")

        console.print()

    def validate_section_references(self):
        """Check that section text references match table numbers"""
        console.print("[bold]5. Validating Section References[/bold]")
        console.print("  [dim]Checking that tables referenced in sections exist...[/dim]\n")

        cursor = self.conn.cursor()

        # Get all sections
        cursor.execute("""
            SELECT vintage, section_number, content
            FROM necb_sections
            WHERE content LIKE '%Table%'
        """)

        sections = cursor.fetchall()

        issues = 0
        for vintage, section_num, content in sections:
            # Find table references like "Table 3.2.2.2"
            import re
            table_refs = re.findall(r'Table\s+(\d+(?:\.\d+)*\.)', content)

            for table_ref in set(table_refs):  # Unique refs only
                table_num = f"Table {table_ref}"

                # Check if table exists
                cursor.execute("""
                    SELECT COUNT(*) FROM necb_tables
                    WHERE vintage = ? AND table_number = ?
                """, (vintage, table_num))

                count = cursor.fetchone()[0]

                if count == 0:
                    issues += 1
                    if issues <= 5:  # Only show first 5
                        console.print(f"  [yellow]⚠️  {vintage} Section {section_num} references "
                                    f"{table_num} but table not found[/yellow]")

                    self.errors.append(ValidationError(
                        severity="WARNING",
                        vintage=vintage,
                        table_number=table_num,
                        page_number=None,
                        message=f"Section {section_num} references table but table not in database",
                        expected="Table should exist",
                        actual="Not found"
                    ))

        if issues == 0:
            console.print("  [green]✓ All section table references found in database[/green]")
        elif issues > 5:
            console.print(f"  [dim]... and {issues - 5} more missing references[/dim]")

        console.print()

    def print_results(self):
        """Print validation summary"""
        errors = [e for e in self.errors if e.severity == "ERROR"]
        warnings = [e for e in self.errors if e.severity == "WARNING"]
        info = [e for e in self.errors if e.severity == "INFO"]

        # Summary panel
        summary_text = f"""
[bold]Validation Summary[/bold]

Total Issues: {len(self.errors)}
  • [red]Errors: {len(errors)}[/red]
  • [yellow]Warnings: {len(warnings)}[/yellow]
  • [cyan]Info: {len(info)}[/cyan]
"""

        if errors:
            summary_text += "\n[red]⚠️  CRITICAL ISSUES FOUND - Database needs repair[/red]"
        elif warnings:
            summary_text += "\n[yellow]⚠️  Warnings found - Review recommended[/yellow]"
        else:
            summary_text += "\n[green]✅ All validation checks passed![/green]"

        console.print(Panel(summary_text, border_style="cyan"))

        # Detailed errors
        if errors:
            console.print("\n[bold red]ERRORS:[/bold red]")
            for error in errors[:20]:  # Show first 20
                console.print(f"  • [{error.vintage}] {error.table_number}: {error.message}")
                if error.expected and error.actual:
                    console.print(f"    Expected: {error.expected}")
                    console.print(f"    Actual: {error.actual}")

            if len(errors) > 20:
                console.print(f"  [dim]... and {len(errors) - 20} more errors[/dim]")

        # Detailed warnings
        if warnings and not errors:  # Only show if no errors
            console.print("\n[bold yellow]WARNINGS:[/bold yellow]")
            for warning in warnings[:10]:  # Show first 10
                console.print(f"  • [{warning.vintage}] {warning.table_number}: {warning.message}")

            if len(warnings) > 10:
                console.print(f"  [dim]... and {len(warnings) - 10} more warnings[/dim]")

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Run NECB database validation"""
    db_path = Path(__file__).parent.parent / "data" / "necb.db"

    if not db_path.exists():
        console.print(f"[red]Error: Database not found at {db_path}[/red]")
        console.print("[yellow]Run the database builder first:[/yellow]")
        console.print("  python -m bluesky.mcp.scrapers.necb.necb_db_builder")
        return

    validator = NECBDatabaseValidator(db_path)

    try:
        results = validator.validate_all()

        # Exit with error code if critical errors found
        if results["total_errors"] > 0:
            console.print("\n[red]Validation failed with errors[/red]")
            return 1
        else:
            console.print("\n[green]Validation passed![/green]")
            return 0

    finally:
        validator.close()


if __name__ == "__main__":
    exit(main() or 0)
