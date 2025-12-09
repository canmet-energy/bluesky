#!/usr/bin/env python3
"""Build Comprehensive NECB Production Database

Builds SQLite database with all 21 implemented table schemas across 4 vintages.

Usage:
    python scripts/build_necb_production_database.py --backend claude
    python scripts/build_necb_production_database.py --backend ollama
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import click
from bluesky.mcp.scrapers.necb.parsers.tables.config import ParserConfig
from bluesky.mcp.scrapers.necb.parsers.tables.db_builder import NECBDatabaseBuilder
from bluesky.mcp.scrapers.necb.parsers.tables.db_query import NECBDatabaseQuery
from bluesky.mcp.scrapers.necb.parsers.tables.table_specs import get_table_specs


# PDF directory
PDF_DIR = Path(__file__).parent.parent / "src/bluesky/mcp/resources/pdfs"


@click.command()
@click.option(
    "--backend",
    type=click.Choice(["claude", "ollama"]),
    default="claude",
    help="LLM backend to use (claude recommended for speed)",
)
@click.option(
    "--db-path",
    type=click.Path(),
    default="src/bluesky/mcp/resources/databases/necb_production.db",
    help="Output database path",
)
@click.option(
    "--vintages",
    multiple=True,
    type=click.Choice(["2011", "2015", "2017", "2020"]),
    help="Specific vintages to parse (default: all)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be parsed without actually parsing",
)
@click.option(
    "--skip-successful",
    is_flag=True,
    default=False,
    help="Skip tables that already exist and succeeded in the database (incremental build)",
)
def main(backend, db_path, vintages, dry_run, skip_successful):
    """Build comprehensive NECB production database"""

    db_path = Path(db_path)

    # Select vintages
    if vintages:
        selected_vintages = list(vintages)
    else:
        selected_vintages = ["2011", "2015", "2017", "2020"]

    # Count total tables
    total_tables = sum(len(get_table_specs(v)) for v in selected_vintages)

    # Check for existing tables if --skip-successful
    skipped_count = 0
    if skip_successful and db_path.exists():
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM necb_tables WHERE vintage IN ({})".format(
            ','.join('?' * len(selected_vintages))
        ), selected_vintages)
        skipped_count = cursor.fetchone()[0]
        conn.close()
        total_tables -= skipped_count

    print("=" * 80)
    print("NECB PRODUCTION DATABASE BUILD")
    print("=" * 80)
    print()
    print(f"Backend: {backend.upper()}")
    print(f"Database: {db_path}")
    print(f"Vintages: {', '.join(selected_vintages)}")
    if skip_successful and skipped_count > 0:
        print(f"Total tables: {total_tables} (skipping {skipped_count} successful)")
    else:
        print(f"Total tables: {total_tables}")
    print()

    if backend == "claude":
        est_cost = total_tables * 0.0025
        est_time = total_tables * 7  # 7s per table avg
        print(f"Estimated cost: ${est_cost:.3f}")
        print(f"Estimated time: {est_time/60:.1f} minutes")
    else:
        est_time = total_tables * 10  # 10s per table avg with Ollama
        print(f"Estimated time: {est_time/60:.1f} minutes")

    print()

    # Show what will be parsed
    for vintage in selected_vintages:
        tables = get_table_specs(vintage)
        print(f"{vintage}: {len(tables)} tables")
        for spec in tables:
            title = spec.get('table_description') or spec.get('title') or f"Table {spec['table_number']}"
            print(f"  • {spec['table_number']:15} page {spec['page_num']+1:3} - {title}")
        print()

    if dry_run:
        print("=" * 80)
        print("DRY RUN COMPLETE (no parsing performed)")
        print("=" * 80)
        return

    # Confirm before proceeding
    if not click.confirm("\nProceed with database build?", default=True):
        print("Aborted.")
        return

    # Configure parser
    if backend == "claude":
        config = ParserConfig(
            llm_backend="claude",
            llm_model="claude-haiku-4-5",
            llm_temperature=0.0,
        )
    else:
        config = ParserConfig(
            llm_backend="ollama",
            llm_model="qwen2.5:14b-instruct",
            llm_temperature=0.0,
        )

    # Initialize builder
    print("\n" + "=" * 80)
    print("INITIALIZING DATABASE BUILDER")
    print("=" * 80)
    print()

    # Handle existing database
    existing_tables = set()
    if db_path.exists() and skip_successful:
        # Query existing successful tables
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT vintage, table_number FROM necb_tables")
        # Normalize table numbers: remove "Table " prefix and trailing period
        # Database stores "Table 10.1.2.1." but inventory uses "10.1.2.1"
        existing_tables = set()
        for row in cursor.fetchall():
            vintage_val = row[0]
            table_num = row[1]
            # Strip "Table " prefix and trailing period
            if table_num.startswith("Table "):
                table_num = table_num[6:]  # Remove "Table " prefix
            if table_num.endswith("."):
                table_num = table_num[:-1]  # Remove trailing period
            existing_tables.add((vintage_val, table_num))
        conn.close()
        print(f"✅ Found {len(existing_tables)} existing successful tables - will skip")
        print()
    elif db_path.exists():
        print(f"⚠️  Removing existing database: {db_path}")
        db_path.unlink()
        print()

    builder = NECBDatabaseBuilder(
        db_path=db_path,
        config=config,
        verbose=True,
    )

    print("Creating database schema...")
    builder.create_database_schema()
    print()

    # Build database for each vintage
    overall_start = time.time()
    overall_stats = {
        "total_tables": 0,
        "successful_tables": 0,
        "failed_tables": 0,
        "total_rows": 0,
    }

    for vintage in selected_vintages:
        pdf_path = PDF_DIR / f"NECB-{vintage}.pdf"

        if not pdf_path.exists():
            print(f"❌ PDF not found: {pdf_path}")
            continue

        print("\n" + "=" * 80)
        print(f"BUILDING NECB {vintage}")
        print("=" * 80)
        print()

        # Load table specs
        table_specs = get_table_specs(vintage)
        print(f"Loaded {len(table_specs)} table specs")

        # Filter out existing successful tables if --skip-successful
        if skip_successful:
            original_count = len(table_specs)
            table_specs = [
                spec for spec in table_specs
                if (vintage, spec['table_number']) not in existing_tables
            ]
            skipped = original_count - len(table_specs)
            if skipped > 0:
                print(f"⏭️  Skipping {skipped} existing successful tables")
                print(f"📋 Will parse {len(table_specs)} failed/missing tables")
            print()

        stats = builder.build_document(
            pdf_path=pdf_path,
            vintage=vintage,
            table_specs=table_specs,
        )

        overall_stats["total_tables"] += stats.total_tables
        overall_stats["successful_tables"] += stats.successful_tables
        overall_stats["failed_tables"] += stats.failed_tables
        overall_stats["total_rows"] += stats.total_rows

    overall_elapsed = time.time() - overall_start

    # Final summary
    print("\n" + "=" * 80)
    print("BUILD COMPLETE")
    print("=" * 80)
    print()
    print(f"✅ Success: {overall_stats['successful_tables']}/{overall_stats['total_tables']} tables")
    print(f"❌ Failed: {overall_stats['failed_tables']}")
    print(f"📊 Total rows: {overall_stats['total_rows']}")
    print(f"⏱️  Total time: {overall_elapsed/60:.1f} minutes")
    print(f"⏱️  Avg per table: {overall_elapsed/overall_stats['total_tables']:.1f}s")

    if backend == "claude":
        actual_cost = overall_stats["successful_tables"] * 0.0025
        print(f"💰 Actual cost: ${actual_cost:.3f}")

    print()
    print(f"Database: {db_path.absolute()}")

    # Query database statistics
    if overall_stats["successful_tables"] > 0:
        print()
        print("=" * 80)
        print("DATABASE STATISTICS")
        print("=" * 80)
        print()

        query = NECBDatabaseQuery(db_path)
        db_stats = query.get_database_statistics()

        print(f"Total tables: {db_stats['total_tables']}")
        print(f"Total rows: {db_stats['total_rows']}")
        print()
        print("By vintage:")
        for vintage, vstats in sorted(db_stats["vintages"].items()):
            print(f"  {vintage}: {vstats['tables']:2} tables, {vstats['rows']:3} rows")
        print()
        print("By parser method:")
        for method, mstats in db_stats["methods"].items():
            print(f"  {method:10}: {mstats['count']:2} tables, "
                  f"avg confidence {mstats['avg_confidence']:.2f}, "
                  f"avg LLM time {mstats['avg_llm_time']:.1f}s")

    print()
    print("=" * 80)
    print("✅ PRODUCTION DATABASE READY")
    print("=" * 80)
    print()
    print("Query the database:")
    print(f"  python -c \"from bluesky.mcp.scrapers.necb.parsers.tables.db_query import NECBDatabaseQuery; q = NECBDatabaseQuery('{db_path}'); print(q.list_tables())\"")
    print()


if __name__ == "__main__":
    main()
