"""
Command-line interface for NECB parsers

Provides unified CLI for parsing NECB PDF documents:
- Tables: Extract tabular data with hybrid PyMuPDF+LLM pipeline
- Sections: Extract hierarchical article/clause text
- Figures: Extract diagrams, images, and schematics

Usage:
    python -m bluesky.necb.build tables --backend claude --vintages 2020
    python -m bluesky.necb.build sections --vintages 2020
    python -m bluesky.necb.build figures --vintage 2020
    python -m bluesky.necb.build all --backend ollama
"""

import sys
import time
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table as RichTable

from bluesky.necb import PDF_DIR, DB_PATH, FIGURES_DIR, CHROMA_PATH, LLM_CACHE_DIR

# Alias for backwards compatibility
FIGURE_OUTPUT_DIR = FIGURES_DIR

console = Console()


@click.group()
def cli():
    """NECB Parser CLI - Extract tables, sections, and figures from NECB PDFs"""
    pass


@cli.command()
@click.option(
    "--backend",
    type=click.Choice(["claude", "ollama"]),
    default="claude",
    show_default=True,
    help="LLM backend for table repair",
)
@click.option(
    "--db-path",
    type=click.Path(),
    default=str(DB_PATH),
    show_default=True,
    help="Output database path",
)
@click.option(
    "--vintages",
    multiple=True,
    type=click.Choice(["2011", "2015", "2017", "2020"]),
    help="Specific vintages to parse (default: all)",
)
@click.option(
    "--tables",
    multiple=True,
    help="Specific table numbers to parse (e.g., '3.2.2.2', '8.4.4.10')",
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
    help="Skip tables that already exist in database (incremental build)",
)
@click.option(
    "--cache-only",
    is_flag=True,
    default=False,
    help="Phase 1: Parse PDFs and build cache only (no database). Use --from-cache for Phase 2.",
)
@click.option(
    "--from-cache",
    is_flag=True,
    default=False,
    help="Phase 2: Build database from cached LLM outputs (no PDF parsing, no LLM calls)",
)
@click.option(
    "--cache-dir",
    type=click.Path(),
    default=str(LLM_CACHE_DIR),
    show_default=True,
    help="Directory for LLM output cache",
)
def tables(backend, db_path, vintages, tables, dry_run, skip_successful, cache_only, from_cache, cache_dir):
    """Parse NECB tables with hybrid PyMuPDF+LLM pipeline"""

    from bluesky.necb.build.tables.config import ParserConfig
    from bluesky.necb.build.tables.db_builder import NECBDatabaseBuilder
    from bluesky.necb.build.tables.table_specs import get_table_specs

    db_path = Path(db_path)
    cache_dir = Path(cache_dir)

    # Handle --from-cache mode (fast rebuild from cached LLM outputs)
    if from_cache:
        selected_vintages = list(vintages) if vintages else ["2011", "2015", "2017", "2020"]

        # Display info
        info_table = RichTable(show_header=False, box=None)
        info_table.add_column("Key", style="cyan")
        info_table.add_column("Value", style="white")

        info_table.add_row("Mode", "[green]FROM CACHE (no LLM calls)[/green]")
        info_table.add_row("Cache dir", str(cache_dir))
        info_table.add_row("Database", str(db_path))
        info_table.add_row("Vintages", ", ".join(selected_vintages))

        console.print(Panel(info_table, title="[bold]NECB Table Parser - Cache Mode[/bold]", border_style="green"))

        if dry_run:
            # Show cached tables
            from bluesky.necb.build.tables.cache import TableCacheManager
            cache = TableCacheManager(cache_dir)
            cached = cache.list_cached_tables()

            console.print(f"\n[cyan]Found {len(cached)} cached tables[/cyan]")
            for v in selected_vintages:
                v_cached = [(vintage, t) for vintage, t in cached if vintage == v]
                console.print(f"  • {v}: {len(v_cached)} tables")

            console.print("\n[green]DRY RUN COMPLETE[/green] (no changes made)\n")
            return

        if not click.confirm("\nProceed with cache-based rebuild?", default=True):
            console.print("[yellow]Aborted.[/yellow]")
            return

        # Clear existing table data
        if db_path.exists():
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS necb_table_rows")
            cursor.execute("DROP TABLE IF EXISTS necb_tables")
            cursor.execute("DROP TABLE IF EXISTS parser_metadata")
            conn.commit()
            conn.close()
            console.print(f"\n[yellow]⚠️  Cleared existing table data[/yellow]\n")

        # Build from cache
        config = ParserConfig()  # Minimal config for cache mode
        builder = NECBDatabaseBuilder(db_path=db_path, config=config, verbose=True)

        console.print(f"\n[bold cyan]Building from cache...[/bold cyan]\n")

        stats = builder.build_from_cache(
            cache_dir=cache_dir,
            vintages=selected_vintages,
        )

        # Summary
        summary_table = RichTable(show_header=False, box=None)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="white")

        summary_table.add_row("Success", f"{stats.successful_tables}/{stats.total_tables} tables")
        summary_table.add_row("Failed", str(stats.failed_tables))
        summary_table.add_row("Total rows", str(stats.total_rows))
        summary_table.add_row("Duration", f"{stats.total_duration:.1f}s")
        summary_table.add_row("Database", str(db_path.absolute()))

        console.print(Panel(summary_table, title="[bold green]CACHE BUILD COMPLETE[/bold green]", border_style="green"))
        return

    # Handle --cache-only mode (Phase 1: parse and cache, no database)
    if cache_only:
        from bluesky.necb.build.tables.hybrid_parser import HybridNECBParser
        from bluesky.necb.build.tables.cache import TableCacheManager

        selected_vintages = list(vintages) if vintages else ["2017", "2020"]

        # Get table specs
        all_table_specs = []
        for vintage in selected_vintages:
            vintage_specs = get_table_specs(vintage)
            if tables:
                vintage_specs = [s for s in vintage_specs if s['table_number'] in tables]
            all_table_specs.extend([(vintage, spec) for spec in vintage_specs])

        total_tables = len(all_table_specs)

        # Check for already-cached tables
        cache_manager = TableCacheManager(cache_dir)
        cached_tables = set(cache_manager.list_cached_tables())
        uncached_specs = [
            (v, s) for v, s in all_table_specs
            if (v, s['table_number']) not in cached_tables
        ]
        already_cached = total_tables - len(uncached_specs)

        # Display info
        info_table = RichTable(show_header=False, box=None)
        info_table.add_column("Key", style="cyan")
        info_table.add_column("Value", style="white")

        info_table.add_row("Mode", "[yellow]CACHE ONLY (Phase 1)[/yellow]")
        info_table.add_row("Backend", backend.upper())
        info_table.add_row("Cache dir", str(cache_dir))
        info_table.add_row("Vintages", ", ".join(selected_vintages))
        if already_cached > 0:
            info_table.add_row("Tables to parse", f"{len(uncached_specs)} ({already_cached} already cached)")
        else:
            info_table.add_row("Tables to parse", str(total_tables))

        if backend == "claude":
            est_cost = len(uncached_specs) * 0.0025
            est_time = len(uncached_specs) * 7
            info_table.add_row("Estimated cost", f"${est_cost:.3f}")
            info_table.add_row("Estimated time", f"{est_time/60:.1f} minutes")
        else:
            est_time = len(uncached_specs) * 10
            info_table.add_row("Estimated time", f"{est_time/60:.1f} minutes")

        console.print(Panel(info_table, title="[bold]NECB Table Parser - Cache Only Mode[/bold]", border_style="yellow"))

        # Show tables to be parsed
        for vintage in selected_vintages:
            specs = [s for v, s in uncached_specs if v == vintage]
            if specs:
                console.print(f"\n[bold cyan]{vintage}:[/bold cyan] {len(specs)} tables to cache")
                for spec in specs[:10]:
                    title = spec.get('table_description') or spec.get('title') or f"Table {spec['table_number']}"
                    console.print(f"  • [yellow]{spec['table_number']:15}[/yellow] page {spec['page_num']+1:3} - {title}")
                if len(specs) > 10:
                    console.print(f"  ... and {len(specs) - 10} more")

        if dry_run:
            console.print("\n[green]DRY RUN COMPLETE[/green] (no parsing performed)\n")
            return

        if len(uncached_specs) == 0:
            console.print("\n[green]✅ All tables already cached![/green]")
            console.print(f"[cyan]Run with --from-cache to build database from {len(cached_tables)} cached tables[/cyan]\n")
            return

        if not click.confirm("\nProceed with cache-only parsing?", default=True):
            console.print("[yellow]Aborted.[/yellow]")
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

        # Initialize parser with cache
        parser = HybridNECBParser(
            config=config,
            verbose=True,
            llm_cache_dir=cache_dir,
        )

        # Parse and cache tables
        console.print(f"\n[bold cyan]Phase 1: Parsing and caching tables...[/bold cyan]\n")

        overall_start = time.time()
        stats = {
            "total": len(uncached_specs),
            "success": 0,
            "failed": 0,
            "skipped": already_cached,
        }

        for i, (vintage, spec) in enumerate(uncached_specs, 1):
            table_number = spec['table_number']
            page_num = spec['page_num']
            pdf_path = PDF_DIR / f"NECB-{vintage}.pdf"

            console.print(f"\n[{i}/{len(uncached_specs)}] {vintage} - Table {table_number}")

            result = parser.parse_table(
                pdf_path=pdf_path,
                table_number=table_number,
                vintage=vintage,
                page_num=page_num,
            )

            if result.success:
                stats["success"] += 1
                console.print(f"  [green]✅ Cached successfully[/green]")
            else:
                stats["failed"] += 1
                console.print(f"  [red]❌ Failed: {result.errors}[/red]")

        overall_elapsed = time.time() - overall_start

        # Summary
        summary_table = RichTable(show_header=False, box=None)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="white")

        summary_table.add_row("Newly cached", f"{stats['success']}/{stats['total']}")
        summary_table.add_row("Failed", str(stats['failed']))
        summary_table.add_row("Previously cached", str(stats['skipped']))
        summary_table.add_row("Total in cache", str(stats['success'] + stats['skipped']))
        summary_table.add_row("Duration", f"{overall_elapsed/60:.1f} minutes")
        summary_table.add_row("Cache dir", str(cache_dir.absolute()))

        console.print(Panel(summary_table, title="[bold green]PHASE 1 COMPLETE - CACHE BUILT[/bold green]", border_style="green"))

        console.print("\n[bold cyan]Next step:[/bold cyan]")
        console.print(f"  python -m bluesky.necb.build tables --from-cache --vintages {' --vintages '.join(selected_vintages)}\n")
        return

    # Select vintages
    selected_vintages = list(vintages) if vintages else ["2011", "2015", "2017", "2020"]

    # Select tables
    if tables:
        # Specific tables requested
        if not vintages:
            console.print("[red]Error:[/red] --vintages required when using --tables")
            sys.exit(1)

        # Build table specs from requested tables
        all_table_specs = []
        for vintage in selected_vintages:
            vintage_specs = get_table_specs(vintage)
            requested_specs = [
                spec for spec in vintage_specs
                if spec['table_number'] in tables
            ]
            all_table_specs.extend([(vintage, spec) for spec in requested_specs])

        total_tables = len(all_table_specs)
        console.print(f"\n[cyan]Selected {total_tables} specific tables[/cyan]\n")
    else:
        # Use inventory if available
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

    # Display build info
    info_table = RichTable(show_header=False, box=None)
    info_table.add_column("Key", style="cyan")
    info_table.add_column("Value", style="white")

    info_table.add_row("Backend", backend.upper())
    info_table.add_row("Database", str(db_path))
    info_table.add_row("Vintages", ", ".join(selected_vintages))
    if skip_successful and skipped_count > 0:
        info_table.add_row("Total tables", f"{total_tables} (skipping {skipped_count} successful)")
    else:
        info_table.add_row("Total tables", str(total_tables))

    if backend == "claude":
        est_cost = total_tables * 0.0025
        est_time = total_tables * 7
        info_table.add_row("Estimated cost", f"${est_cost:.3f}")
        info_table.add_row("Estimated time", f"{est_time/60:.1f} minutes")
    else:
        est_time = total_tables * 10
        info_table.add_row("Estimated time", f"{est_time/60:.1f} minutes")

    console.print(Panel(info_table, title="[bold]NECB Table Parser[/bold]", border_style="cyan"))

    # Show what will be parsed
    for vintage in selected_vintages:
        specs = get_table_specs(vintage)
        if tables:
            specs = [s for s in specs if s['table_number'] in tables]

        console.print(f"\n[bold cyan]{vintage}:[/bold cyan] {len(specs)} tables")
        for spec in specs:
            title = spec.get('table_description') or spec.get('title') or f"Table {spec['table_number']}"
            console.print(f"  • [yellow]{spec['table_number']:15}[/yellow] page {spec['page_num']+1:3} - {title}")

    if dry_run:
        console.print("\n[green]DRY RUN COMPLETE[/green] (no parsing performed)\n")
        return

    # Confirm
    if not click.confirm("\nProceed with table parsing?", default=True):
        console.print("[yellow]Aborted.[/yellow]")
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

    # Handle existing database
    existing_tables = set()
    if db_path.exists() and skip_successful:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Check if necb_tables exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='necb_tables'")
        if cursor.fetchone():
            cursor.execute("SELECT vintage, table_number FROM necb_tables")
            for row in cursor.fetchall():
                vintage_val = row[0]
                table_num = row[1]
                if table_num.startswith("Table "):
                    table_num = table_num[6:]
                if table_num.endswith("."):
                    table_num = table_num[:-1]
                existing_tables.add((vintage_val, table_num))
            console.print(f"\n[green]✅ Found {len(existing_tables)} existing tables - will skip[/green]\n")
        conn.close()
    elif db_path.exists():
        # Only clear table-related tables, preserve articles and figures
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS necb_table_rows")
        cursor.execute("DROP TABLE IF EXISTS necb_tables")
        cursor.execute("DROP TABLE IF EXISTS parser_metadata")
        conn.commit()
        conn.close()
        console.print(f"\n[yellow]⚠️  Cleared existing table data (preserving articles/figures)[/yellow]\n")

    # Initialize builder (with LLM cache for saving outputs during parsing)
    builder = NECBDatabaseBuilder(
        db_path=db_path,
        config=config,
        verbose=True,
        llm_cache_dir=cache_dir,
    )
    builder.create_database_schema()

    # Build database
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
            console.print(f"[red]❌ PDF not found: {pdf_path}[/red]")
            continue

        console.print(f"\n[bold cyan]Building NECB {vintage}[/bold cyan]\n")

        # Load table specs
        table_specs = get_table_specs(vintage)

        # Filter by requested tables
        if tables:
            table_specs = [s for s in table_specs if s['table_number'] in tables]

        # Filter out existing successful tables
        if skip_successful:
            original_count = len(table_specs)
            table_specs = [
                spec for spec in table_specs
                if (vintage, spec['table_number']) not in existing_tables
            ]
            skipped = original_count - len(table_specs)
            if skipped > 0:
                console.print(f"[yellow]⏭️  Skipping {skipped} existing successful tables[/yellow]")

        stats = builder.build_document(pdf_path=pdf_path, vintage=vintage, table_specs=table_specs)

        overall_stats["total_tables"] += stats.total_tables
        overall_stats["successful_tables"] += stats.successful_tables
        overall_stats["failed_tables"] += stats.failed_tables
        overall_stats["total_rows"] += stats.total_rows

    overall_elapsed = time.time() - overall_start

    # Final summary
    summary_table = RichTable(show_header=False, box=None)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="white")

    summary_table.add_row("Success", f"{overall_stats['successful_tables']}/{overall_stats['total_tables']} tables")
    summary_table.add_row("Failed", str(overall_stats['failed_tables']))
    summary_table.add_row("Total rows", str(overall_stats['total_rows']))
    summary_table.add_row("Total time", f"{overall_elapsed/60:.1f} minutes")
    summary_table.add_row("Avg per table", f"{overall_elapsed/overall_stats['total_tables']:.1f}s")

    if backend == "claude":
        actual_cost = overall_stats["successful_tables"] * 0.0025
        summary_table.add_row("Actual cost", f"${actual_cost:.3f}")

    summary_table.add_row("Database", str(db_path.absolute()))

    console.print(Panel(summary_table, title="[bold green]BUILD COMPLETE[/bold green]", border_style="green"))


@cli.command()
@click.option(
    "--db-path",
    type=click.Path(),
    default=str(DB_PATH),
    show_default=True,
    help="Output database path",
)
@click.option(
    "--vintages",
    multiple=True,
    type=click.Choice(["2011", "2015", "2017", "2020"]),
    help="Specific vintages to parse (default: all)",
)
@click.option(
    "--cache-only",
    is_flag=True,
    default=False,
    help="Phase 1: Parse PDFs and save to cache only (no database)",
)
@click.option(
    "--from-cache",
    is_flag=True,
    default=False,
    help="Phase 2: Build database from cached extractions (no PDF parsing)",
)
@click.option(
    "--cache-dir",
    type=click.Path(),
    default=str(LLM_CACHE_DIR),
    show_default=True,
    help="Directory for section cache",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be parsed without actually parsing",
)
@click.option(
    "--equations-only",
    is_flag=True,
    help="Re-extract equations only (updates existing cache files with improved LLM prompt)",
)
def sections(db_path, vintages, cache_only, from_cache, cache_dir, dry_run, equations_only):
    """Parse NECB sections/articles with hierarchical structure extraction"""

    from bluesky.necb.build.sections.article_parser import parse_vintage
    from bluesky.necb.build.sections.cache import SectionCacheManager, create_section_cache_entry
    from bluesky.necb.build.sections.article_db import init_database, insert_batch, delete_vintage

    db_path = Path(db_path)
    cache_dir = Path(cache_dir)
    selected_vintages = list(vintages) if vintages else ["2011", "2015", "2017", "2020"]

    # Handle --equations-only mode (re-extract equations in existing cache files)
    if equations_only:
        import re
        import json
        import fitz
        from bluesky.necb.build.sections.equation_extractor import (
            extract_equations_from_page,
            insert_equations_into_text,
            LLM_VISION_AVAILABLE,
        )

        if not LLM_VISION_AVAILABLE:
            console.print("[red]Error: ANTHROPIC_API_KEY not set - LLM vision required for equation extraction[/red]")
            sys.exit(1)

        info_table = RichTable(show_header=False, box=None)
        info_table.add_column("Key", style="cyan")
        info_table.add_column("Value", style="white")

        info_table.add_row("Mode", "[magenta]EQUATIONS ONLY (re-extract with improved prompt)[/magenta]")
        info_table.add_row("Cache dir", str(cache_dir))
        info_table.add_row("Vintages", ", ".join(selected_vintages))

        console.print(Panel(info_table, title="[bold]NECB Sections - Equations Only Mode[/bold]", border_style="magenta"))

        # Find cache files with equations
        cache = SectionCacheManager(cache_dir)

        articles_with_equations = []
        for vintage in selected_vintages:
            cached_sections = cache.list_cached_sections(vintage)
            for v, division, article_num in cached_sections:
                entry = cache.load(v, article_num, division)
                if entry and entry.full_text and "[Equation:" in entry.full_text:
                    articles_with_equations.append((v, division, article_num, entry))

        if not articles_with_equations:
            console.print("\n[yellow]No articles with equations found in cache[/yellow]")
            return

        console.print(f"\n[cyan]Found {len(articles_with_equations)} articles with equations[/cyan]")

        # Show which articles will be updated
        for v, div, art_num, entry in articles_with_equations[:10]:
            eq_count = entry.full_text.count("[Equation:")
            console.print(f"  - {v}/{div}/{art_num}: {eq_count} equation(s)")
        if len(articles_with_equations) > 10:
            console.print(f"  ... and {len(articles_with_equations) - 10} more")

        # Estimate cost
        total_equations = sum(e.full_text.count("[Equation:") for _, _, _, e in articles_with_equations)
        est_cost = total_equations * 0.002  # ~$0.002 per equation with Haiku
        console.print(f"\n[cyan]Total equations to re-extract: {total_equations}[/cyan]")
        console.print(f"[cyan]Estimated cost: ${est_cost:.3f}[/cyan]")

        if dry_run:
            console.print("\n[green]DRY RUN COMPLETE[/green] (no changes made)\n")
            return

        if not click.confirm("\nProceed with equation re-extraction?", default=True):
            console.print("[yellow]Aborted.[/yellow]")
            return

        # Re-extract equations by finding equation images in PDF and re-running LLM
        console.print(f"\n[bold cyan]Re-extracting equations with improved LLM prompt...[/bold cyan]\n")

        overall_start = time.time()
        stats = {"updated": 0, "failed": 0, "equations": 0}

        # For each article with equations, find the equation markers in full_text
        # and re-extract from the PDF at those locations
        from bluesky.necb.build.sections.equation_extractor import (
            render_region_to_image,
            extract_equation_with_llm,
            detect_equation_gaps,
        )

        # Group by vintage for PDF access
        by_vintage = {}
        for v, div, art_num, entry in articles_with_equations:
            if v not in by_vintage:
                by_vintage[v] = []
            by_vintage[v].append((div, art_num, entry))

        for vintage, articles in by_vintage.items():
            pdf_path = PDF_DIR / f"NECB-{vintage}.pdf"
            if not pdf_path.exists():
                console.print(f"[red]PDF not found: {pdf_path}[/red]")
                continue

            doc = fitz.open(pdf_path)
            console.print(f"\n[bold cyan]{vintage}:[/bold cyan] Processing {len(articles)} articles")

            # Scan all pages in the PDF for equation gaps
            # and build a mapping of context → extracted equation
            console.print(f"  Scanning PDF for equation regions...")
            all_pdf_equations = {}  # context_key → (page, y_start, y_end, extracted_latex)

            for page_num in range(doc.page_count):
                try:
                    gaps = detect_equation_gaps(doc[page_num])
                    for y_start, y_end, context_before, context_after in gaps:
                        # Render and extract with LLM
                        image_data = render_region_to_image(doc[page_num], y_start, y_end)
                        latex = extract_equation_with_llm(image_data)
                        if latex:
                            # Use context_before as key (first 50 chars)
                            key = context_before[-50:].lower().strip()
                            all_pdf_equations[key] = (page_num, y_start, y_end, latex)
                            console.print(f"    Page {page_num + 1}: Found equation after '{context_before[-30:]}...'")
                except Exception as e:
                    pass  # Skip problematic pages

            console.print(f"  Found {len(all_pdf_equations)} equations in PDF")

            # Now update each article's equations
            for div, art_num, entry in articles:
                try:
                    old_text = entry.full_text
                    old_eq_count = old_text.count("[Equation:")

                    # Find all equation markers and their context
                    pattern = r'(following equations?:?|calculated using one of the following equations?)\s*\n*\s*\[Equation:[^\]]+\]'
                    matches = list(re.finditer(pattern, old_text, re.IGNORECASE))

                    if not matches:
                        # Try simpler pattern
                        pattern = r'\[Equation:[^\]]+\]'
                        matches = list(re.finditer(pattern, old_text, re.IGNORECASE))

                    if not matches:
                        console.print(f"  ⚠️  {div}/{art_num}: Could not find equation patterns")
                        continue

                    new_text = old_text
                    updated_count = 0

                    # For each equation in the article, try to find matching PDF extraction
                    for match in matches:
                        # Get context before the equation
                        start_pos = max(0, match.start() - 100)
                        context = old_text[start_pos:match.start()].lower()

                        # Find matching PDF equation by context
                        best_match_key = None
                        best_match_score = 0
                        for key in all_pdf_equations:
                            # Score based on common words
                            key_words = set(key.split())
                            context_words = set(context.split())
                            score = len(key_words & context_words)
                            if score > best_match_score:
                                best_match_score = score
                                best_match_key = key

                        if best_match_key and best_match_score >= 2:
                            _, _, _, new_latex = all_pdf_equations[best_match_key]
                            # Replace old equation with new one
                            old_eq = match.group(0)
                            # Extract just the [Equation:...] part if match includes context
                            eq_match = re.search(r'\[Equation:[^\]]+\]', old_eq)
                            if eq_match:
                                old_eq_only = eq_match.group(0)
                                new_eq = f"[Equation: {new_latex}]"
                                new_text = new_text.replace(old_eq_only, new_eq, 1)
                                updated_count += 1

                    if updated_count > 0:
                        entry.full_text = new_text
                        cache.save(entry)
                        stats["updated"] += 1
                        stats["equations"] += updated_count
                        console.print(f"  ✅ {div}/{art_num}: {updated_count} equation(s) updated")
                    else:
                        console.print(f"  ⚠️  {div}/{art_num}: No matching PDF equations found")

                except Exception as e:
                    stats["failed"] += 1
                    console.print(f"  ❌ {div}/{art_num}: {e}")

            doc.close()

        overall_elapsed = time.time() - overall_start

        # Summary
        summary_table = RichTable(show_header=False, box=None)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="white")

        summary_table.add_row("Articles updated", str(stats['updated']))
        summary_table.add_row("Equations re-extracted", str(stats['equations']))
        summary_table.add_row("Failed", str(stats['failed']))
        summary_table.add_row("Duration", f"{overall_elapsed:.1f}s")
        summary_table.add_row("Cache dir", str(cache_dir.absolute()))

        console.print(Panel(summary_table, title="[bold green]EQUATION RE-EXTRACTION COMPLETE[/bold green]", border_style="green"))

        console.print("\n[bold cyan]Next step:[/bold cyan]")
        console.print(f"  python -m bluesky.necb.build sections --from-cache --vintages {' --vintages '.join(selected_vintages)}\n")
        return

    # Handle --from-cache mode (Phase 2: build database from cache)
    if from_cache:
        info_table = RichTable(show_header=False, box=None)
        info_table.add_column("Key", style="cyan")
        info_table.add_column("Value", style="white")

        info_table.add_row("Mode", "[green]FROM CACHE (no PDF parsing)[/green]")
        info_table.add_row("Cache dir", str(cache_dir))
        info_table.add_row("Database", str(db_path))
        info_table.add_row("Vintages", ", ".join(selected_vintages))

        console.print(Panel(info_table, title="[bold]NECB Sections - Cache Mode[/bold]", border_style="green"))

        # Check cached sections
        cache = SectionCacheManager(cache_dir)

        total_cached = 0
        for v in selected_vintages:
            cached = cache.list_cached_sections(v)
            total_cached += len(cached)
            if dry_run:
                console.print(f"  • {v}: {len(cached)} cached sections")

        if dry_run:
            console.print(f"\n[cyan]Total: {total_cached} cached sections[/cyan]")
            console.print("\n[green]DRY RUN COMPLETE[/green] (no changes made)\n")
            return

        if total_cached == 0:
            console.print(f"\n[yellow]No cached sections found[/yellow]")
            console.print(f"[cyan]Run --cache-only first to build the cache[/cyan]\n")
            return

        if not click.confirm(f"\nLoad {total_cached} sections from cache into database?", default=True):
            console.print("[yellow]Aborted.[/yellow]")
            return

        # Initialize database
        init_database()

        console.print(f"\n[bold cyan]Loading sections from cache...[/bold cyan]\n")

        overall_start = time.time()
        overall_stats = {"total_articles": 0, "total_clauses": 0}

        for vintage in selected_vintages:
            cached_sections = cache.list_cached_sections(vintage)
            if not cached_sections:
                continue

            console.print(f"[bold cyan]{vintage}:[/bold cyan] Loading {len(cached_sections)} sections")

            # Delete existing for this vintage
            deleted = delete_vintage(vintage)
            if deleted > 0:
                console.print(f"  Deleted {deleted} existing articles")

            # Load and insert each cached section
            from bluesky.necb.build.sections.article_models import Article, Sentence, Clause, Subclause

            articles = []
            for v, division, article_num in cached_sections:
                entry = cache.load(v, article_num, division)
                if entry and entry.success:
                    # Reconstruct Article from cache
                    # Note: entry.sentences is already a list (not JSON string)
                    sentences_data = entry.sentences if entry.sentences else []

                    # Convert sentence dicts to Sentence objects (using correct NECB terminology)
                    sentences = []
                    for s in sentences_data:
                        clauses = []
                        for c in s.get("clauses", []):
                            subclauses = [
                                Subclause(
                                    subclause_numeral=sc["subclause_numeral"],
                                    reference=sc.get("reference", ""),
                                    text=sc["text"]
                                )
                                for sc in c.get("subclauses", [])
                            ]
                            clauses.append(Clause(
                                clause_letter=c["clause_letter"],
                                reference=c.get("reference", ""),
                                text=c["text"],
                                subclauses=subclauses
                            ))
                        sentences.append(Sentence(
                            sentence_number=s["sentence_number"],
                            reference=s.get("reference", ""),
                            text=s["text"],
                            clauses=clauses
                        ))

                    article = Article(
                        article_number=entry.article_number,
                        reference=entry.article_number,  # Article reference is same as article_number
                        title=entry.title,
                        vintage=entry.vintage,
                        division=entry.division,
                        hierarchy_level=entry.hierarchy_level,
                        part_number=entry.part_number,
                        section_number=entry.section_number,
                        subsection_number=entry.subsection_number,
                        full_text=entry.full_text,
                        sentences=sentences,
                        page_start=entry.page_start,
                        page_end=entry.page_end,
                    )
                    articles.append(article)

            # Insert batch
            inserted = insert_batch(articles)
            total_sentences = sum(len(a.sentences) for a in articles)

            console.print(f"  ✅ Inserted {inserted} articles, {total_sentences} sentences")

            overall_stats["total_articles"] += inserted
            overall_stats["total_clauses"] += total_sentences

        overall_elapsed = time.time() - overall_start

        # Summary
        summary_table = RichTable(show_header=False, box=None)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="white")

        summary_table.add_row("Total articles", str(overall_stats['total_articles']))
        summary_table.add_row("Total clauses", str(overall_stats['total_clauses']))
        summary_table.add_row("Duration", f"{overall_elapsed:.1f}s")
        summary_table.add_row("Database", str(db_path.absolute()))

        console.print(Panel(summary_table, title="[bold green]CACHE LOAD COMPLETE[/bold green]", border_style="green"))
        return

    # Handle --cache-only mode (Phase 1: parse and cache, no database)
    if cache_only:
        info_table = RichTable(show_header=False, box=None)
        info_table.add_column("Key", style="cyan")
        info_table.add_column("Value", style="white")

        info_table.add_row("Mode", "[yellow]CACHE ONLY (Phase 1)[/yellow]")
        info_table.add_row("Cache dir", str(cache_dir))
        info_table.add_row("Vintages", ", ".join(selected_vintages))
        info_table.add_row("Estimated time", "2-4 minutes per vintage")

        console.print(Panel(info_table, title="[bold]NECB Section Parser - Cache Only Mode[/bold]", border_style="yellow"))

        if dry_run:
            console.print("\n[green]DRY RUN COMPLETE[/green] (no parsing performed)\n")
            return

        if not click.confirm("\nProceed with section parsing and caching?", default=True):
            console.print("[yellow]Aborted.[/yellow]")
            return

        cache = SectionCacheManager(cache_dir, verbose=True)

        console.print(f"\n[bold cyan]Phase 1: Parsing and caching sections...[/bold cyan]\n")

        overall_start = time.time()
        overall_stats = {"total_articles": 0, "total_clauses": 0}

        for vintage in selected_vintages:
            console.print(f"\n[bold cyan]Parsing NECB {vintage} sections[/bold cyan]\n")

            # Parse without saving to database
            result = parse_vintage(vintage=vintage, save_to_db=False)

            if result.success and result.articles:
                # Save each article to cache
                for article in result.articles:
                    # Convert sentences to JSON-serializable format (using correct NECB terminology)
                    sentences_list = []
                    for sentence in article.sentences:
                        sentence_dict = {
                            "sentence_number": sentence.sentence_number,
                            "reference": sentence.reference,
                            "text": sentence.text,
                            "clauses": []
                        }
                        for clause in sentence.clauses:
                            clause_dict = {
                                "clause_letter": clause.clause_letter,
                                "reference": clause.reference,
                                "text": clause.text,
                                "subclauses": [
                                    {
                                        "subclause_numeral": sc.subclause_numeral,
                                        "reference": sc.reference,
                                        "text": sc.text
                                    }
                                    for sc in clause.subclauses
                                ]
                            }
                            sentence_dict["clauses"].append(clause_dict)
                        sentences_list.append(sentence_dict)

                    entry = create_section_cache_entry(
                        vintage=article.vintage,
                        article_number=article.article_number,
                        title=article.title,
                        full_text=article.full_text,
                        sentences=sentences_list,
                        division=article.division,
                        hierarchy_level=article.hierarchy_level,
                        page_start=article.page_start,
                        page_end=article.page_end,
                        success=True,
                    )
                    cache.save(entry)

                console.print(f"[green]✅ Cached {result.total_articles} articles, {result.total_sentences} sentences[/green]")

                overall_stats["total_articles"] += result.total_articles
                overall_stats["total_clauses"] += result.total_sentences
            else:
                console.print(f"[red]❌ Failed to parse {vintage}[/red]")

        overall_elapsed = time.time() - overall_start

        # Summary
        summary_table = RichTable(show_header=False, box=None)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="white")

        summary_table.add_row("Total articles cached", str(overall_stats['total_articles']))
        summary_table.add_row("Total clauses", str(overall_stats['total_clauses']))
        summary_table.add_row("Duration", f"{overall_elapsed/60:.1f} minutes")
        summary_table.add_row("Cache dir", str(cache_dir.absolute()))

        console.print(Panel(summary_table, title="[bold green]PHASE 1 COMPLETE - CACHE BUILT[/bold green]", border_style="green"))

        console.print("\n[bold cyan]Next step:[/bold cyan]")
        console.print(f"  python -m bluesky.necb.build sections --from-cache --vintages {' --vintages '.join(selected_vintages)}\n")
        return

    # Normal mode: Parse and save directly to database
    # Display info
    info_table = RichTable(show_header=False, box=None)
    info_table.add_column("Key", style="cyan")
    info_table.add_column("Value", style="white")

    info_table.add_row("Database", str(db_path))
    info_table.add_row("Vintages", ", ".join(selected_vintages))
    info_table.add_row("Estimated time", "2-4 minutes per vintage")

    console.print(Panel(info_table, title="[bold]NECB Section Parser[/bold]", border_style="cyan"))

    if dry_run:
        console.print("\n[green]DRY RUN COMPLETE[/green] (no parsing performed)\n")
        return

    # Confirm
    if not click.confirm("\nProceed with section parsing?", default=True):
        console.print("[yellow]Aborted.[/yellow]")
        return

    # Parse vintages
    overall_start = time.time()
    overall_stats = {
        "total_articles": 0,
        "total_clauses": 0,
    }

    for vintage in selected_vintages:
        console.print(f"\n[bold cyan]Parsing NECB {vintage} sections[/bold cyan]\n")

        result = parse_vintage(vintage=vintage, save_to_db=True)

        console.print(f"[green]✅ Parsed {result.total_articles} articles, {result.total_clauses} clauses[/green]")

        overall_stats["total_articles"] += result.total_articles
        overall_stats["total_clauses"] += result.total_clauses

    overall_elapsed = time.time() - overall_start

    # Final summary
    summary_table = RichTable(show_header=False, box=None)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="white")

    summary_table.add_row("Total articles", str(overall_stats['total_articles']))
    summary_table.add_row("Total clauses", str(overall_stats['total_clauses']))
    summary_table.add_row("Total time", f"{overall_elapsed/60:.1f} minutes")
    summary_table.add_row("Database", str(db_path.absolute()))

    console.print(Panel(summary_table, title="[bold green]SECTION PARSING COMPLETE[/bold green]", border_style="green"))


@cli.command()
@click.option(
    "--vintage",
    type=click.Choice(["2011", "2015", "2017", "2020"]),
    required=True,
    help="NECB vintage to parse",
)
@click.option(
    "--output-dir",
    type=click.Path(),
    default=None,
    help="Output directory for figure images (default: resources/figures/{vintage})",
)
@click.option(
    "--db-path",
    type=click.Path(),
    default=str(DB_PATH),
    show_default=True,
    help="Output database path for metadata",
)
@click.option(
    "--enrich",
    is_flag=True,
    help="Enrich figures with AI-generated descriptions using Claude Vision",
)
@click.option(
    "--cache-only",
    is_flag=True,
    help="Phase 1: Call Vision API and cache results only (no database). Use --from-cache for Phase 2.",
)
@click.option(
    "--from-cache",
    is_flag=True,
    help="Phase 2: Build database from cached Vision API outputs (no API calls)",
)
@click.option(
    "--cache-dir",
    type=click.Path(),
    default=str(LLM_CACHE_DIR),
    show_default=True,
    help="Directory for Vision API output cache",
)
@click.option(
    "--anthropic-api-key",
    type=str,
    default=None,
    envvar="ANTHROPIC_API_KEY",
    help="Anthropic API key for vision enrichment (or set ANTHROPIC_API_KEY env var)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be parsed without actually parsing",
)
@click.option(
    "--extract",
    is_flag=True,
    help="Extract figures from PDF (WARNING: will overwrite manually cropped images)",
)
def figures(vintage, output_dir, db_path, enrich, cache_only, from_cache, cache_dir, anthropic_api_key, dry_run, extract):
    """Work with NECB figures - enrich existing figures or extract from PDF"""

    from bluesky.necb.build.figures.figure_parser import parse_figures
    from bluesky.necb.build.figures.cache import FigureCacheManager

    db_path = Path(db_path)
    cache_dir = Path(cache_dir)
    pdf_path = PDF_DIR / f"NECB-{vintage}.pdf"

    if not pdf_path.exists():
        console.print(f"[red]❌ PDF not found: {pdf_path}[/red]")
        sys.exit(1)

    # Handle --from-cache mode (Phase 2: build database from cache)
    if from_cache:
        info_table = RichTable(show_header=False, box=None)
        info_table.add_column("Key", style="cyan")
        info_table.add_column("Value", style="white")

        info_table.add_row("Mode", "[green]FROM CACHE (no Vision API calls)[/green]")
        info_table.add_row("Vintage", vintage)
        info_table.add_row("Cache dir", str(cache_dir))
        info_table.add_row("Database", str(db_path))

        console.print(Panel(info_table, title="[bold]NECB Figures - Cache Mode[/bold]", border_style="green"))

        # Check cached figures
        cache = FigureCacheManager(cache_dir)
        cached_figures = cache.list_cached_figures(vintage)

        if dry_run:
            console.print(f"\n[cyan]Found {len(cached_figures)} cached figures for {vintage}[/cyan]")
            for v, label in cached_figures[:10]:
                console.print(f"  • {label}")
            if len(cached_figures) > 10:
                console.print(f"  ... and {len(cached_figures) - 10} more")
            console.print("\n[green]DRY RUN COMPLETE[/green] (no changes made)\n")
            return

        if not cached_figures:
            console.print(f"\n[yellow]No cached figures found for {vintage}[/yellow]")
            console.print(f"[cyan]Run --cache-only first to build the cache[/cyan]\n")
            return

        if not click.confirm(f"\nUpdate database with {len(cached_figures)} cached figure descriptions?", default=True):
            console.print("[yellow]Aborted.[/yellow]")
            return

        # Load cache and update database
        console.print(f"\n[bold cyan]Loading figures from cache into database...[/bold cyan]\n")

        import sqlite3
        from PIL import Image as PILImage

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Ensure necb_figures table exists with correct schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS necb_figures (
                id INTEGER PRIMARY KEY,
                vintage TEXT NOT NULL,
                division TEXT,
                label TEXT NOT NULL,
                caption TEXT,
                page INTEGER NOT NULL,
                bbox_x0 REAL, bbox_y0 REAL, bbox_x1 REAL, bbox_y1 REAL,
                image_path TEXT NOT NULL,
                image_type TEXT NOT NULL,
                image_format TEXT,
                width INTEGER,
                height INTEGER,
                file_size INTEGER,
                ai_description TEXT,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(vintage, label)
            )
        """)
        conn.commit()

        # Step 1: Discover PNG files from filesystem and INSERT into database
        vintage_dir = FIGURE_OUTPUT_DIR / vintage
        if vintage_dir.exists():
            png_files = sorted(vintage_dir.glob("Figure_*.png"))
            console.print(f"[cyan]Step 1: Discovered {len(png_files)} PNG files in {vintage_dir}[/cyan]\n")

            inserted = 0
            for png_file in png_files:
                # Parse label from filename: "Figure_A-1.2.3.png" -> "Figure A-1.2.3"
                label = f"Figure {png_file.stem[7:]}"  # Remove "Figure_" prefix

                # Get image dimensions and file size
                try:
                    with PILImage.open(png_file) as img:
                        width, height = img.size
                    file_size = png_file.stat().st_size
                except Exception:
                    width, height = 0, 0
                    file_size = 0

                # Get relative image path
                image_path = f"{vintage}/{png_file.name}"

                # Try to get caption and page from cache if available
                cache_entry = cache.load(vintage, label)
                caption = cache_entry.caption if cache_entry else None
                page = cache_entry.page_number if cache_entry else 0

                # INSERT OR REPLACE to handle existing records
                cursor.execute("""
                    INSERT OR REPLACE INTO necb_figures
                    (vintage, label, caption, page, image_path, image_type, image_format, width, height, file_size)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (vintage, label, caption, page, image_path, "bitmap", "png", width, height, file_size))
                inserted += 1
                console.print(f"  ✅ Inserted {label}")

            conn.commit()
            console.print(f"\n[green]Inserted {inserted} figures into database[/green]\n")
        else:
            console.print(f"[yellow]⚠️  Figure directory not found: {vintage_dir}[/yellow]")
            inserted = 0

        # Step 2: UPDATE with AI descriptions from cache
        console.print(f"[cyan]Step 2: Updating {len(cached_figures)} figures with AI descriptions[/cyan]\n")

        updated = 0
        for v, figure_label in cached_figures:
            entry = cache.load(v, figure_label)
            if entry and entry.success and entry.ai_description:
                cursor.execute(
                    "UPDATE necb_figures SET ai_description = ? WHERE vintage = ? AND label = ?",
                    (entry.ai_description, v, entry.figure_label)
                )
                if cursor.rowcount > 0:
                    updated += 1
                    console.print(f"  ✅ {entry.figure_label}")

        conn.commit()
        conn.close()

        # Summary
        summary_table = RichTable(show_header=False, box=None)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="white")

        summary_table.add_row("Figures inserted", str(inserted))
        summary_table.add_row("AI descriptions added", f"{updated}/{len(cached_figures)}")
        summary_table.add_row("Database", str(db_path.absolute()))

        console.print(Panel(summary_table, title="[bold green]CACHE LOAD COMPLETE[/bold green]", border_style="green"))
        return

    # Handle --cache-only mode (Phase 1: call Vision API, save to cache, no database)
    if cache_only:
        import sqlite3
        from PIL import Image as PILImage
        from bluesky.necb.build.figures.figure_models import Figure
        from bluesky.necb.build.figures.vision_enrichment import VisionEnricher, VisionEnrichmentConfig

        vintage_dir = FIGURE_OUTPUT_DIR / vintage

        if not vintage_dir.exists():
            console.print(f"[red]❌ Figure directory not found: {vintage_dir}[/red]")
            sys.exit(1)

        # Find PNG files
        png_files = sorted(vintage_dir.glob("Figure_*.png"))
        if not png_files:
            console.print(f"[red]❌ No PNG files found in {vintage_dir}[/red]")
            sys.exit(1)

        # Check what's already cached
        cache = FigureCacheManager(cache_dir)
        cached_set = set(cache.list_cached_figures(vintage))

        # Build list of figures to process
        figures_to_process = []
        for png_file in png_files:
            label = f"Figure {png_file.stem[7:]}"  # "Figure_A-1.2.3" -> "Figure A-1.2.3"
            if (vintage, label) not in cached_set:
                figures_to_process.append((png_file, label))

        already_cached = len(png_files) - len(figures_to_process)

        # Display info
        info_table = RichTable(show_header=False, box=None)
        info_table.add_column("Key", style="cyan")
        info_table.add_column("Value", style="white")

        info_table.add_row("Mode", "[yellow]CACHE ONLY (Phase 1)[/yellow]")
        info_table.add_row("Vintage", vintage)
        info_table.add_row("Cache dir", str(cache_dir))
        if already_cached > 0:
            info_table.add_row("Figures to enrich", f"{len(figures_to_process)} ({already_cached} already cached)")
        else:
            info_table.add_row("Figures to enrich", str(len(figures_to_process)))

        est_cost = len(figures_to_process) * 0.005  # ~$0.005 per figure
        est_time = len(figures_to_process) * 3  # ~3 seconds per figure
        info_table.add_row("Estimated cost", f"${est_cost:.3f}")
        info_table.add_row("Estimated time", f"{est_time/60:.1f} minutes")

        console.print(Panel(info_table, title="[bold]NECB Figures - Cache Only Mode[/bold]", border_style="yellow"))

        if dry_run:
            console.print(f"\n[cyan]Figures to process:[/cyan]")
            for png_file, label in figures_to_process[:10]:
                console.print(f"  • {label}")
            if len(figures_to_process) > 10:
                console.print(f"  ... and {len(figures_to_process) - 10} more")
            console.print("\n[green]DRY RUN COMPLETE[/green] (no changes made)\n")
            return

        if len(figures_to_process) == 0:
            console.print("\n[green]✅ All figures already cached![/green]")
            console.print(f"[cyan]Run with --from-cache to update database[/cyan]\n")
            return

        if not click.confirm("\nProceed with Vision API caching?", default=True):
            console.print("[yellow]Aborted.[/yellow]")
            return

        # Initialize Vision enricher with cache
        enricher = VisionEnricher(
            api_key=anthropic_api_key,
            db_path=db_path,
            cache_dir=cache_dir,
            use_cache=True,
        )

        console.print(f"\n[bold cyan]Phase 1: Calling Vision API and caching results...[/bold cyan]\n")

        overall_start = time.time()
        stats = {"success": 0, "failed": 0, "skipped": already_cached}

        for i, (png_file, label) in enumerate(figures_to_process, 1):
            console.print(f"[{i}/{len(figures_to_process)}] {label}")

            # Create Figure object
            with PILImage.open(png_file) as img:
                width, height = img.size

            figure = Figure(
                label=label,
                caption=None,
                vintage=vintage,
                page=0,
                bbox=(0, 0, width, height),
                image_path=str(png_file),
                image_type="bitmap",
                width=width,
                height=height,
            )

            # Read image data
            with open(png_file, "rb") as f:
                image_data = f.read()

            # Call Vision API (will save to cache)
            result = enricher.enrich_figure(
                figure=figure,
                image_data_bytes=image_data,
                vintage=vintage,
            )

            if result.success:
                stats["success"] += 1
                console.print(f"  [green]✅ Cached ({result.tokens_used} tokens)[/green]")
            else:
                stats["failed"] += 1
                console.print(f"  [red]❌ Failed: {result.error}[/red]")

        overall_elapsed = time.time() - overall_start

        # Summary
        summary_table = RichTable(show_header=False, box=None)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="white")

        summary_table.add_row("Newly cached", f"{stats['success']}/{len(figures_to_process)}")
        summary_table.add_row("Failed", str(stats['failed']))
        summary_table.add_row("Previously cached", str(stats['skipped']))
        summary_table.add_row("Total in cache", str(stats['success'] + stats['skipped']))
        summary_table.add_row("Duration", f"{overall_elapsed/60:.1f} minutes")
        summary_table.add_row("Cache dir", str(cache_dir.absolute()))

        console.print(Panel(summary_table, title="[bold green]PHASE 1 COMPLETE - CACHE BUILT[/bold green]", border_style="green"))

        console.print("\n[bold cyan]Next step:[/bold cyan]")
        console.print(f"  python -m bluesky.necb.build figures --vintage {vintage} --from-cache\n")
        return

    # Display info for normal modes
    info_table = RichTable(show_header=False, box=None)
    info_table.add_column("Key", style="cyan")
    info_table.add_column("Value", style="white")

    info_table.add_row("Vintage", vintage)
    info_table.add_row("PDF", str(pdf_path))
    info_table.add_row("Database", str(db_path))
    if output_dir:
        info_table.add_row("Output dir", output_dir)

    if enrich:
        info_table.add_row("Vision enrichment", "Enabled")
        info_table.add_row("Estimated time", "10-20 minutes")
        info_table.add_row("Estimated cost", "~$0.10-0.15")
    else:
        info_table.add_row("Vision enrichment", "Disabled")
        info_table.add_row("Estimated time", "2-4 minutes")

    console.print(Panel(info_table, title="[bold]NECB Figure Parser[/bold]", border_style="cyan"))

    if dry_run:
        console.print("\n[green]DRY RUN COMPLETE[/green] (no parsing performed)\n")
        return

    # Validate usage
    if not extract and not enrich:
        console.print("[red]❌ Must specify --extract, --enrich, --cache-only, or --from-cache[/red]")
        console.print("[yellow]Examples:[/yellow]")
        console.print("  [cyan]--enrich[/cyan]                    # Enrich existing figures with AI descriptions")
        console.print("  [cyan]--extract[/cyan]                   # Extract figures from PDF (overwrites existing)")
        console.print("  [cyan]--cache-only[/cyan]                # Phase 1: Call Vision API, save to cache only")
        console.print("  [cyan]--from-cache[/cyan]                # Phase 2: Load cache into database")
        sys.exit(1)

    # Default mode: Discover figures from filesystem (no extraction)
    if not extract:
        console.print(f"\n[bold cyan]Discovering figures from filesystem[/bold cyan]\n")

        import sqlite3
        from PIL import Image as PILImage
        from bluesky.necb.build.figures.figure_models import Figure

        vintage_dir = Path(f"{FIGURE_OUTPUT_DIR}/{vintage}")

        if not vintage_dir.exists():
            console.print(f"[red]❌ Figure directory not found: {vintage_dir}[/red]")
            sys.exit(1)

        # Find all PNG files
        png_files = sorted(vintage_dir.glob("Figure_*.png"))

        if not png_files:
            console.print(f"[red]❌ No PNG files found in {vintage_dir}[/red]")
            sys.exit(1)

        # Load corresponding metadata from database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        figures = []
        for png_file in png_files:
            # Extract label from filename (remove "Figure_" prefix and ".png" suffix)
            filename_base = png_file.stem[7:]  # Remove "Figure_" prefix

            # Reverse sanitization to get original label (add back parentheses)
            # Note: This is imperfect but works for most cases
            label = filename_base

            # Try to find matching record in database
            cursor.execute(
                """SELECT label, caption, page FROM necb_figures
                   WHERE vintage = ? AND (label = ? OR label LIKE ?)
                   LIMIT 1""",
                (vintage, label, f"%{label}%")
            )
            row = cursor.fetchone()

            # Get image dimensions
            with PILImage.open(png_file) as img:
                width, height = img.size

            if row:
                # Use database metadata
                figures.append(Figure(
                    label=row[0],
                    caption=row[1],
                    vintage=vintage,
                    page=row[2],
                    bbox=(0, 0, width, height),  # Dummy bbox
                    image_path=str(png_file.relative_to(vintage_dir.parent)),
                    image_type="bitmap",
                    width=width,
                    height=height,
                ))
            else:
                # Create minimal Figure object without database metadata
                figures.append(Figure(
                    label=label,
                    caption=None,
                    vintage=vintage,
                    page=0,  # Unknown
                    bbox=(0, 0, width, height),
                    image_path=str(png_file.relative_to(vintage_dir.parent)),
                    image_type="bitmap",
                    width=width,
                    height=height,
                ))

        conn.close()

        console.print(f"[green]✅ Found {len(figures)} PNG files in {vintage_dir}[/green]\n")

        # Create mock result object for compatibility
        from dataclasses import dataclass
        from typing import List

        @dataclass
        class MockResult:
            success: bool = True
            figures: List[Figure] = None
            total_figures: int = 0

        result = MockResult(success=True, figures=figures, total_figures=len(figures))
        start = time.time()

    else:
        # Extraction mode - warn about overwriting
        console.print("\n[bold yellow]⚠️  WARNING: Extraction will overwrite manually cropped images![/bold yellow]")

        # Confirm
        if not click.confirm("\nProceed with figure extraction from PDF?", default=False):
            console.print("[yellow]Aborted.[/yellow]")
            return

        # Parse figures
        console.print(f"\n[bold cyan]Extracting NECB {vintage} figures from PDF[/bold cyan]\n")

        start = time.time()
        result = parse_figures(vintage=vintage, save_to_db=True)
        elapsed = time.time() - start

    # Vision enrichment (optional)
    if enrich and result.success and result.figures:
        console.print(f"\n[bold cyan]Enriching figures with AI descriptions[/bold cyan]\n")

        try:
            from bluesky.necb.build.figures.vision_enrichment import (
                VisionEnricher,
                save_enrichment_to_database,
            )
            from bluesky.necb.build.figures import figure_config

            enricher = VisionEnricher(api_key=anthropic_api_key, db_path=db_path)

            enrichment_results = enricher.enrich_figures(
                figures=result.figures,
                figure_output_dir=figure_config.FIGURE_OUTPUT_DIR,
                vintage=vintage,
            )

            # Save to database
            updated = save_enrichment_to_database(
                enrichment_results=enrichment_results,
                vintage=vintage,
                db_path=db_path,
            )

            # Export to markdown files for QA
            from bluesky.necb.build.figures.vision_enrichment import (
                save_descriptions_to_markdown
            )

            markdown_count = save_descriptions_to_markdown(
                enrichment_results=enrichment_results,
                figure_output_dir=Path(output_dir) if output_dir else Path(f"{FIGURE_OUTPUT_DIR}/{vintage}"),
                vintage=vintage,
            )

            # Calculate stats
            success_count = sum(1 for r in enrichment_results if r.success)
            total_tokens = sum(r.tokens_used for r in enrichment_results if r.tokens_used)

            console.print(f"\n[green]✅ Enriched {success_count}/{len(enrichment_results)} figures[/green]")
            console.print(f"[green]   Total tokens: {total_tokens:,}[/green]")
            console.print(f"[green]   Database records updated: {updated}[/green]")
            console.print(f"[green]   Markdown files exported: {markdown_count}[/green]")

        except Exception as e:
            console.print(f"\n[red]❌ Vision enrichment failed: {e}[/red]")
            console.print("[yellow]Figures were extracted but not enriched with AI descriptions[/yellow]")

    elapsed_total = time.time() - start

    # Summary
    summary_table = RichTable(show_header=False, box=None)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="white")

    summary_table.add_row("Total figures", str(result.total_figures))

    if extract:
        summary_table.add_row("Extraction time", f"{elapsed:.1f}s")

    if enrich:
        summary_table.add_row("Total time", f"{elapsed_total/60:.1f} minutes")

    summary_table.add_row("Database", str(db_path.absolute()))

    # Determine title based on operations performed
    if extract and enrich:
        title = "[bold green]EXTRACTION & ENRICHMENT COMPLETE[/bold green]"
    elif extract:
        title = "[bold green]FIGURE EXTRACTION COMPLETE[/bold green]"
    else:
        title = "[bold green]ENRICHMENT COMPLETE[/bold green]"

    console.print(Panel(summary_table, title=title, border_style="green"))


@cli.command()
@click.option(
    "--db-path",
    type=click.Path(),
    default=str(DB_PATH),
    show_default=True,
    help="Path to NECB production database",
)
@click.option(
    "--chroma-path",
    type=click.Path(),
    default=str(CHROMA_PATH),
    show_default=True,
    help="Path to ChromaDB storage directory",
)
@click.option(
    "--vintages",
    multiple=True,
    type=click.Choice(["2011", "2015", "2017", "2020"]),
    help="Specific vintages to index (default: all)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force rebuild (delete existing collections)",
)
@click.option(
    "--stats",
    is_flag=True,
    help="Show index statistics only (no building)",
)
def index(db_path, chroma_path, vintages, force, stats):
    """Build ChromaDB vector index for semantic search"""

    from bluesky.necb.tools.vector_indexer import NECBVectorIndexer

    db_path = Path(db_path)
    chroma_path = Path(chroma_path)
    selected_vintages = list(vintages) if vintages else ["2011", "2015", "2017", "2020"]

    # Check database exists
    if not db_path.exists():
        console.print(f"[red]❌ Database not found: {db_path}[/red]")
        console.print("[yellow]Run parsers first to build the database[/yellow]")
        sys.exit(1)

    # Initialize indexer
    console.print(Panel(
        f"[bold]NECB Vector Index Builder[/bold]\n\n"
        f"Database: {db_path}\n"
        f"ChromaDB: {chroma_path}\n"
        f"Vintages: {', '.join(selected_vintages)}\n"
        f"Force rebuild: {force}",
        border_style="cyan"
    ))

    indexer = NECBVectorIndexer(db_path=db_path, chroma_path=chroma_path)

    if stats:
        # Show statistics
        index_stats = indexer.get_stats()

        stats_table = RichTable(show_header=False, box=None)
        stats_table.add_column("Property", style="cyan")
        stats_table.add_column("Value", style="white")

        stats_table.add_row("Model", str(index_stats['model']))
        stats_table.add_row("Device", str(index_stats['device']))
        stats_table.add_row("Dimensions", str(index_stats['dimensions']))
        stats_table.add_row("Storage", str(index_stats['chroma_path']))

        console.print(Panel(stats_table, title="[bold]Index Statistics[/bold]", border_style="cyan"))

        if index_stats["collections"]:
            console.print("\n[bold cyan]Collections:[/bold cyan]")
            for name, info in index_stats["collections"].items():
                console.print(f"  • [yellow]{name}[/yellow]: {info['count']:,} documents")
        else:
            console.print("\n[yellow]No collections found. Run without --stats to build.[/yellow]")

        return

    # Build index
    if not click.confirm("\nProceed with vector index build?", default=True):
        console.print("[yellow]Aborted.[/yellow]")
        return

    console.print(f"\n[bold cyan]Building vector index...[/bold cyan]\n")

    start = time.time()
    results = indexer.build_index(vintages=selected_vintages, force_rebuild=force)
    elapsed = time.time() - start

    # Summary
    summary_table = RichTable(show_header=False, box=None)
    summary_table.add_column("Vintage", style="cyan")
    summary_table.add_column("Documents", style="white")

    total_docs = 0
    for vintage, count in sorted(results.items()):
        summary_table.add_row(f"NECB {vintage}", f"{count:,}")
        total_docs += count

    summary_table.add_row("", "")  # Separator
    summary_table.add_row("[bold]Total[/bold]", f"[bold]{total_docs:,}[/bold]")
    summary_table.add_row("Build time", f"{elapsed/60:.1f} minutes")
    summary_table.add_row("Storage", str(chroma_path.absolute()))

    console.print(Panel(summary_table, title="[bold green]VECTOR INDEX COMPLETE[/bold green]", border_style="green"))

    # Show how to use
    console.print("\n[bold cyan]Usage:[/bold cyan]")
    console.print("  MCP Server will automatically use this index for semantic search")
    console.print(f"  Index stats: python -m bluesky.necb.build index --stats")


@cli.command()
@click.option(
    "--db-path",
    type=click.Path(),
    default=str(DB_PATH),
    show_default=True,
    help="Path to NECB production database",
)
@click.option(
    "--chroma-path",
    type=click.Path(),
    default=str(CHROMA_PATH),
    show_default=True,
    help="Path to ChromaDB storage directory",
)
@click.option(
    "--vintages",
    multiple=True,
    type=click.Choice(["2011", "2015", "2017", "2020"]),
    help="Specific vintages to check (default: all)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed per-table status",
)
def status(db_path, chroma_path, vintages, verbose):
    """Check database completeness for NECB vintages"""
    import sqlite3

    db_path = Path(db_path)
    chroma_path = Path(chroma_path)
    selected_vintages = list(vintages) if vintages else ["2011", "2015", "2017", "2020"]

    console.print(Panel(
        f"[bold]NECB Database Status Check[/bold]\n\n"
        f"Database: {db_path}\n"
        f"ChromaDB: {chroma_path}\n"
        f"Vintages: {', '.join(selected_vintages)}",
        border_style="cyan"
    ))

    # Check database file exists
    if not db_path.exists():
        console.print("\n[red]❌ Database file not found[/red]")
        console.print("[yellow]Run: python -m bluesky.necb.build all[/yellow]\n")
        sys.exit(1)

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check required tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = {row[0] for row in cursor.fetchall()}

    required_tables = {"necb_tables", "necb_table_rows", "necb_articles", "necb_figures"}
    missing_tables = required_tables - existing_tables

    if missing_tables:
        console.print(f"\n[yellow]⚠️  Missing tables: {', '.join(missing_tables)}[/yellow]\n")

    # Status for each vintage
    overall_status = {}

    for vintage in selected_vintages:
        console.print(f"\n[bold cyan]NECB {vintage}[/bold cyan]")
        console.print("─" * 80)

        vintage_status = {
            "tables": {"present": 0, "expected": 0, "complete": False},
            "sections": {"present": 0, "complete": False},
            "figures": {"present": 0, "complete": False},
            "vector_index": {"present": False, "documents": 0},
        }

        # Check tables
        if "necb_tables" in existing_tables:
            from bluesky.necb.build.tables.table_specs import get_table_specs

            expected_tables = get_table_specs(vintage)
            vintage_status["tables"]["expected"] = len(expected_tables)

            cursor.execute("SELECT COUNT(*) FROM necb_tables WHERE vintage = ?", (vintage,))
            tables_count = cursor.fetchone()[0]
            vintage_status["tables"]["present"] = tables_count
            vintage_status["tables"]["complete"] = tables_count >= len(expected_tables) * 0.9  # 90% threshold

            if verbose and tables_count > 0:
                # Show which tables are present
                cursor.execute("SELECT table_number FROM necb_tables WHERE vintage = ?", (vintage,))
                present_table_nums = {row[0] for row in cursor.fetchall()}

                expected_table_nums = {spec['table_number'] for spec in expected_tables}
                missing_table_nums = expected_table_nums - present_table_nums

                if missing_table_nums:
                    console.print(f"  [yellow]Missing tables ({len(missing_table_nums)}):[/yellow]")
                    for table_num in sorted(missing_table_nums)[:10]:  # Show first 10
                        console.print(f"    • {table_num}")
                    if len(missing_table_nums) > 10:
                        console.print(f"    ... and {len(missing_table_nums) - 10} more")

            # Display status
            status_emoji = "✅" if vintage_status["tables"]["complete"] else "⚠️" if tables_count > 0 else "❌"
            console.print(f"{status_emoji} Tables: {tables_count}/{len(expected_tables)}")

        # Check sections (stored in necb_articles table)
        if "necb_articles" in existing_tables:
            cursor.execute("SELECT COUNT(*) FROM necb_articles WHERE vintage = ?", (vintage,))
            sections_count = cursor.fetchone()[0]
            vintage_status["sections"]["present"] = sections_count
            vintage_status["sections"]["complete"] = sections_count > 0

            status_emoji = "✅" if sections_count > 0 else "❌"
            console.print(f"{status_emoji} Sections: {sections_count:,}")

        # Check figures
        if "necb_figures" in existing_tables:
            cursor.execute("SELECT COUNT(*) FROM necb_figures WHERE vintage = ?", (vintage,))
            figures_count = cursor.fetchone()[0]
            vintage_status["figures"]["present"] = figures_count
            vintage_status["figures"]["complete"] = figures_count > 0

            status_emoji = "✅" if figures_count > 0 else "❌"
            console.print(f"{status_emoji} Figures: {figures_count:,}")

        # Check vector index
        if chroma_path.exists():
            try:
                from bluesky.necb.tools.vector_indexer import NECBVectorIndexer

                indexer = NECBVectorIndexer(db_path=db_path, chroma_path=chroma_path)
                try:
                    collection = indexer.get_collection(vintage)
                    doc_count = collection.count()
                    vintage_status["vector_index"]["present"] = True
                    vintage_status["vector_index"]["documents"] = doc_count

                    status_emoji = "✅" if doc_count > 0 else "⚠️"
                    console.print(f"{status_emoji} Vector Index: {doc_count:,} documents")
                except Exception:
                    console.print("❌ Vector Index: Not found")
            except ImportError:
                console.print("⚠️  Vector Index: Cannot check (dependencies missing)")
        else:
            console.print("❌ Vector Index: ChromaDB directory not found")

        overall_status[vintage] = vintage_status

    conn.close()

    # Overall summary
    console.print("\n" + "=" * 80)
    console.print("[bold]Summary[/bold]")
    console.print("=" * 80 + "\n")

    summary_table = RichTable(show_header=True, box=None)
    summary_table.add_column("Vintage", style="cyan")
    summary_table.add_column("Tables", style="white")
    summary_table.add_column("Sections", style="white")
    summary_table.add_column("Figures", style="white")
    summary_table.add_column("Vector Index", style="white")
    summary_table.add_column("Status", style="white")

    for vintage in selected_vintages:
        status_data = overall_status[vintage]

        tables_str = f"{status_data['tables']['present']}/{status_data['tables']['expected']}"
        sections_str = f"{status_data['sections']['present']:,}"
        figures_str = f"{status_data['figures']['present']:,}"
        index_str = f"{status_data['vector_index']['documents']:,}" if status_data['vector_index']['present'] else "Missing"

        # Overall status for vintage
        all_complete = (
            status_data['tables']['complete'] and
            status_data['sections']['complete'] and
            status_data['figures']['complete'] and
            status_data['vector_index']['present']
        )

        some_complete = (
            status_data['tables']['present'] > 0 or
            status_data['sections']['present'] > 0 or
            status_data['figures']['present'] > 0
        )

        if all_complete:
            overall_str = "[green]✅ Complete[/green]"
        elif some_complete:
            overall_str = "[yellow]⚠️  Partial[/yellow]"
        else:
            overall_str = "[red]❌ Missing[/red]"

        summary_table.add_row(vintage, tables_str, sections_str, figures_str, index_str, overall_str)

    console.print(summary_table)

    # Recommendations
    console.print("\n[bold cyan]Recommendations:[/bold cyan]")

    any_missing = False
    for vintage, status_data in overall_status.items():
        if not status_data['tables']['complete']:
            console.print(f"  • Parse tables for {vintage}: [yellow]python -m bluesky.necb.build tables --vintages {vintage}[/yellow]")
            any_missing = True
        if not status_data['sections']['complete']:
            console.print(f"  • Parse sections for {vintage}: [yellow]python -m bluesky.necb.build sections --vintages {vintage}[/yellow]")
            any_missing = True
        if not status_data['figures']['complete']:
            console.print(f"  • Extract figures for {vintage}: [yellow]python -m bluesky.necb.build figures --vintage {vintage}[/yellow]")
            any_missing = True
        if not status_data['vector_index']['present']:
            console.print(f"  • Build vector index for {vintage}: [yellow]python -m bluesky.necb.build index --vintages {vintage}[/yellow]")
            any_missing = True

    if not any_missing:
        console.print("  [green]✅ All data is complete![/green]")
        console.print("\n  [bold]Quick rebuild all vintages:[/bold]")
        console.print("  [yellow]python -m bluesky.necb.build all --skip-successful[/yellow]")
    else:
        console.print("\n  [bold]Quick fix all missing data:[/bold]")
        console.print("  [yellow]python -m bluesky.necb.build all --skip-successful[/yellow]")

    console.print()


@cli.command("parse-index")
@click.option(
    "--db-path",
    type=click.Path(),
    default=str(DB_PATH),
    show_default=True,
    help="Output database path",
)
@click.option(
    "--vintages",
    multiple=True,
    type=click.Choice(["2020"]),  # Only 2020 supported initially
    help="Specific vintages to parse (default: 2020)",
)
@click.option(
    "--cache-only",
    is_flag=True,
    default=False,
    help="Phase 1: Parse PDF and save to cache only (no database)",
)
@click.option(
    "--from-cache",
    is_flag=True,
    default=False,
    help="Phase 2: Build database from cached entries (no PDF parsing)",
)
@click.option(
    "--cache-dir",
    type=click.Path(),
    default=str(LLM_CACHE_DIR),
    show_default=True,
    help="Directory for index cache",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be parsed without actually parsing",
)
def parse_index(db_path, vintages, cache_only, from_cache, cache_dir, dry_run):
    """Parse NECB alphabetical index for fast topic lookups

    Extracts the alphabetical index (e.g., pages 303-315 in NECB 2020) and
    stores it in the database for instant topic-to-article lookups.

    Examples:
        python -m bluesky.necb.build parse-index
        python -m bluesky.necb.build parse-index --cache-only
        python -m bluesky.necb.build parse-index --from-cache
    """
    from bluesky.necb.build.index import (
        parse_vintage,
        IndexCacheManager,
        init_database,
        get_entry_count,
        get_vintage_stats,
        VALID_VINTAGES,
        INDEX_PAGE_RANGES,
    )

    db_path = Path(db_path)
    cache_dir = Path(cache_dir)
    selected_vintages = list(vintages) if vintages else list(VALID_VINTAGES)

    # Display info panel
    info_table = RichTable(show_header=False, box=None)
    info_table.add_column("Key", style="cyan")
    info_table.add_column("Value", style="white")

    if cache_only:
        mode_str = "[yellow]CACHE ONLY (Phase 1)[/yellow]"
        mode_desc = "Parse PDF index pages and save to JSON cache"
    elif from_cache:
        mode_str = "[green]FROM CACHE (Phase 2)[/green]"
        mode_desc = "Build database from cached entries"
    else:
        mode_str = "[cyan]FULL BUILD[/cyan]"
        mode_desc = "Parse PDF and save to database"

    info_table.add_row("Mode", mode_str)
    info_table.add_row("Vintages", ", ".join(selected_vintages))
    info_table.add_row("Cache dir", str(cache_dir / "index"))
    info_table.add_row("Database", str(db_path))

    # Show page ranges
    for v in selected_vintages:
        if v in INDEX_PAGE_RANGES:
            start, end = INDEX_PAGE_RANGES[v]
            info_table.add_row(f"Pages ({v})", f"{start+1}-{end+1}")

    console.print(Panel(
        info_table,
        title="[bold]NECB Index Parser[/bold]",
        subtitle=mode_desc,
        border_style="cyan"
    ))

    if dry_run:
        # Show current status
        cache_manager = IndexCacheManager(cache_dir / "index")

        console.print("\n[bold]Current Status:[/bold]")
        for v in selected_vintages:
            cached = cache_manager.has_cache(v)
            try:
                db_count = get_entry_count(v, db_path)
            except Exception:
                db_count = 0

            status = []
            if cached:
                info = cache_manager.get_cache_info(v)
                status.append(f"[green]cached ({info.get('entry_count', '?')} entries)[/green]")
            else:
                status.append("[yellow]not cached[/yellow]")

            if db_count > 0:
                status.append(f"[green]in DB ({db_count} entries)[/green]")
            else:
                status.append("[yellow]not in DB[/yellow]")

            console.print(f"  • {v}: {', '.join(status)}")

        console.print("\n[green]DRY RUN COMPLETE[/green] (no changes made)\n")
        return

    if not click.confirm("\nProceed?", default=True):
        console.print("[yellow]Aborted.[/yellow]")
        return

    # Initialize cache manager
    cache_manager = IndexCacheManager(cache_dir / "index")

    # Process each vintage
    start_time = time.time()
    total_entries = 0
    results = []

    for vintage in selected_vintages:
        console.print(f"\n[bold cyan]Processing {vintage}...[/bold cyan]")

        result = parse_vintage(
            vintage=vintage,
            save_to_db=not cache_only,
            save_to_cache=not from_cache,
            from_cache=from_cache,
            db_path=db_path,
            cache_manager=cache_manager,
        )

        results.append(result)

        if result.success:
            console.print(
                f"  [green]✓[/green] {result.total_entries} entries "
                f"({result.total_main_terms} main, {result.total_sub_terms} sub, "
                f"{result.total_cross_references} cross-refs)"
            )
            total_entries += result.total_entries
        else:
            console.print(f"  [red]✗[/red] Failed: {result.error}")

    elapsed = time.time() - start_time

    # Summary
    console.print("\n" + "="*60)
    summary_table = RichTable(show_header=False, box=None)
    summary_table.add_column("", style="cyan")
    summary_table.add_column("", style="white")

    summary_table.add_row("Total entries", str(total_entries))
    summary_table.add_row("Time", f"{elapsed:.1f}s")
    summary_table.add_row("Vintages", ", ".join(selected_vintages))

    if cache_only:
        summary_table.add_row("Cache", str(cache_dir / "index"))
    else:
        summary_table.add_row("Database", str(db_path))

    console.print(Panel(
        summary_table,
        title="[bold green]Index Parsing Complete[/bold green]",
        border_style="green"
    ))
    console.print("="*60 + "\n")


@cli.command()
@click.option(
    "--backend",
    type=click.Choice(["claude", "ollama"]),
    default="claude",
    show_default=True,
    help="LLM backend for table repair",
)
@click.option(
    "--db-path",
    type=click.Path(),
    default=str(DB_PATH),
    show_default=True,
    help="Output database path",
)
@click.option(
    "--vintages",
    multiple=True,
    type=click.Choice(["2011", "2015", "2017", "2020"]),
    help="Specific vintages to parse (default: 2017, 2020)",
)
@click.option(
    "--skip-successful",
    is_flag=True,
    default=False,
    help="Skip tables that already exist in database (incremental build)",
)
@click.option(
    "--cache-only",
    is_flag=True,
    default=False,
    help="Phase 1: Parse and cache LLM/Vision outputs only (no database)",
)
@click.option(
    "--from-cache",
    is_flag=True,
    default=False,
    help="Phase 2: Build database from cached outputs (no API calls)",
)
@click.option(
    "--cache-dir",
    type=click.Path(),
    default=str(LLM_CACHE_DIR),
    show_default=True,
    help="Directory for LLM/Vision output cache",
)
@click.option(
    "--build-index",
    is_flag=True,
    default=True,
    show_default=True,
    help="Build vector index after parsing (for semantic search)",
)
def all(backend, db_path, vintages, skip_successful, cache_only, from_cache, cache_dir, build_index):
    """Parse everything: sections + tables + figures"""

    selected_vintages = list(vintages) if vintages else ["2017", "2020"]

    # Determine mode
    if cache_only:
        mode_str = "[yellow]CACHE ONLY (Phase 1)[/yellow]"
        mode_desc = "Parse PDFs and call LLM/Vision APIs, save to cache (no database)"
    elif from_cache:
        mode_str = "[green]FROM CACHE (Phase 2)[/green]"
        mode_desc = "Build database from cached outputs (no API calls)"
    else:
        mode_str = "[cyan]FULL BUILD[/cyan]"
        mode_desc = "Parse, call APIs, and build database in one step"

    console.print(Panel(
        f"[bold]Parsing all NECB content[/bold]\n\n"
        f"Mode: {mode_str}\n"
        f"Vintages: {', '.join(selected_vintages)}\n"
        f"Backend: {backend.upper()}\n"
        f"Cache dir: {cache_dir}\n"
        f"Database: {db_path}\n\n"
        f"{mode_desc}",
        border_style="cyan"
    ))

    if not click.confirm("\nProceed?", default=True):
        console.print("[yellow]Aborted.[/yellow]")
        return

    overall_start = time.time()

    from click.testing import CliRunner
    runner = CliRunner()

    # Phase 1: Cache only mode
    if cache_only:
        # 1. Cache sections (no LLM, but save to cache for consistency)
        console.print("\n" + "="*80)
        console.print("[bold cyan]STEP 1/3: CACHING SECTIONS[/bold cyan]")
        console.print("="*80 + "\n")

        args = ['sections', '--cache-only', '--cache-dir', cache_dir]
        for v in selected_vintages:
            args.extend(['--vintages', v])

        result = runner.invoke(cli, args, input='y\n')
        if result.exit_code != 0:
            console.print(f"[red]Section caching failed: {result.output}[/red]")
            sys.exit(1)

        # 2. Cache tables (LLM calls, no database)
        console.print("\n" + "="*80)
        console.print("[bold cyan]STEP 2/3: CACHING TABLES (LLM)[/bold cyan]")
        console.print("="*80 + "\n")

        args = ['tables', '--backend', backend, '--cache-only', '--cache-dir', cache_dir]
        for v in selected_vintages:
            args.extend(['--vintages', v])

        result = runner.invoke(cli, args, input='y\n')
        if result.exit_code != 0:
            console.print(f"[red]Table caching failed: {result.output}[/red]")
            sys.exit(1)

        # 3. Cache figures (Vision API calls, no database)
        console.print("\n" + "="*80)
        console.print("[bold cyan]STEP 3/3: CACHING FIGURES (Vision API)[/bold cyan]")
        console.print("="*80 + "\n")

        for vintage in selected_vintages:
            args = ['figures', '--vintage', vintage, '--cache-only', '--cache-dir', cache_dir]
            result = runner.invoke(cli, args, input='y\n')
            if result.exit_code != 0:
                console.print(f"[yellow]⚠️  Figure caching failed for {vintage}[/yellow]")

        overall_elapsed = time.time() - overall_start

        console.print(Panel(
            f"[bold green]PHASE 1 COMPLETE - CACHE BUILT[/bold green]\n\n"
            f"Total time: {overall_elapsed/60:.1f} minutes\n"
            f"Cache dir: {cache_dir}\n\n"
            f"[bold cyan]Next step:[/bold cyan]\n"
            f"python -m bluesky.necb.build all --from-cache --vintages {' --vintages '.join(selected_vintages)}",
            border_style="green"
        ))
        return

    # Phase 2: From cache mode
    if from_cache:
        # 1. Load sections from cache
        console.print("\n" + "="*80)
        console.print("[bold cyan]STEP 1/3: LOADING SECTIONS FROM CACHE[/bold cyan]")
        console.print("="*80 + "\n")

        args = ['sections', '--from-cache', '--cache-dir', cache_dir, '--db-path', db_path]
        for v in selected_vintages:
            args.extend(['--vintages', v])

        result = runner.invoke(cli, args, input='y\n')
        if result.exit_code != 0:
            console.print(f"[red]Section load from cache failed: {result.output}[/red]")
            sys.exit(1)

        # 2. Build tables from cache
        console.print("\n" + "="*80)
        console.print("[bold cyan]STEP 2/3: BUILDING TABLES FROM CACHE[/bold cyan]")
        console.print("="*80 + "\n")

        args = ['tables', '--from-cache', '--cache-dir', cache_dir, '--db-path', db_path]
        for v in selected_vintages:
            args.extend(['--vintages', v])

        result = runner.invoke(cli, args, input='y\n')
        if result.exit_code != 0:
            console.print(f"[red]Table build from cache failed: {result.output}[/red]")
            sys.exit(1)

        # 3. Build figures from cache
        console.print("\n" + "="*80)
        console.print("[bold cyan]STEP 3/3: BUILDING FIGURES FROM CACHE[/bold cyan]")
        console.print("="*80 + "\n")

        for vintage in selected_vintages:
            args = ['figures', '--vintage', vintage, '--from-cache', '--cache-dir', cache_dir, '--db-path', db_path]
            result = runner.invoke(cli, args, input='y\n')
            if result.exit_code != 0:
                console.print(f"[yellow]⚠️  Figure build from cache failed for {vintage}[/yellow]")

        # 4. Build vector index (optional)
        chroma_path = Path(db_path).parent / "chroma"

        if build_index:
            console.print("\n" + "="*80)
            console.print("[bold cyan]STEP 4/4: BUILDING VECTOR INDEX[/bold cyan]")
            console.print("="*80 + "\n")

            args = ['index', '--db-path', db_path, '--chroma-path', str(chroma_path)]
            for v in selected_vintages:
                args.extend(['--vintages', v])

            result = runner.invoke(cli, args, input='y\n')
            if result.exit_code != 0:
                console.print(f"[yellow]⚠️  Vector index build failed[/yellow]")

        overall_elapsed = time.time() - overall_start

        console.print(Panel(
            f"[bold green]PHASE 2 COMPLETE - DATABASE BUILT[/bold green]\n\n"
            f"Total time: {overall_elapsed/60:.1f} minutes\n"
            f"Database: {db_path}",
            border_style="green"
        ))
        return

    # Full build mode (original behavior)
    # 1. Parse sections (fast, no LLM required)
    console.print("\n" + "="*80)
    console.print("[bold cyan]STEP 1/3: PARSING SECTIONS[/bold cyan]")
    console.print("="*80 + "\n")

    args = ['sections', '--db-path', db_path]
    for v in selected_vintages:
        args.extend(['--vintages', v])

    result = runner.invoke(cli, args, input='y\n')
    if result.exit_code != 0:
        console.print(f"[red]Section parsing failed: {result.output}[/red]")
        sys.exit(1)

    # 2. Parse tables (slow, requires LLM for repair)
    console.print("\n" + "="*80)
    console.print("[bold cyan]STEP 2/3: PARSING TABLES[/bold cyan]")
    console.print("="*80 + "\n")

    args = ['tables', '--backend', backend, '--db-path', db_path, '--cache-dir', cache_dir]
    if skip_successful:
        args.append('--skip-successful')
    for v in selected_vintages:
        args.extend(['--vintages', v])

    result = runner.invoke(cli, args, input='y\n')
    if result.exit_code != 0:
        console.print(f"[red]Table parsing failed: {result.output}[/red]")
        sys.exit(1)

    # 3. Enrich figures (uses existing manually-cropped PNG files)
    console.print("\n" + "="*80)
    console.print("[bold cyan]STEP 3/3: ENRICHING FIGURES[/bold cyan]")
    console.print("="*80 + "\n")

    for vintage in selected_vintages:
        args = ['figures', '--vintage', vintage, '--db-path', db_path, '--enrich', '--cache-dir', cache_dir]
        result = runner.invoke(cli, args, input='y\n')
        if result.exit_code != 0:
            console.print(f"[red]Figure enrichment failed for {vintage}: {result.output}[/red]")
            # Continue with other vintages

    # 4. Build vector index (optional)
    chroma_path = Path(db_path).parent / "chroma"

    if build_index:
        console.print("\n" + "="*80)
        console.print("[bold cyan]STEP 4/4: BUILDING VECTOR INDEX[/bold cyan]")
        console.print("="*80 + "\n")

        args = ['index', '--db-path', db_path, '--chroma-path', str(chroma_path)]
        for v in selected_vintages:
            args.extend(['--vintages', v])

        result = runner.invoke(cli, args, input='y\n')
        if result.exit_code != 0:
            console.print(f"[yellow]⚠️  Vector index build failed: {result.output}[/yellow]")
            console.print("[yellow]You can build it later with: python -m bluesky.necb.build index[/yellow]")

    overall_elapsed = time.time() - overall_start

    # Final summary
    console.print("\n" + "="*80)

    if build_index:
        console.print(Panel(
            f"[bold green]ALL PARSING + INDEXING COMPLETE[/bold green]\n\n"
            f"Total time: {overall_elapsed/60:.1f} minutes\n"
            f"Database: {db_path}\n"
            f"Vector index: {chroma_path}",
            border_style="green"
        ))
    else:
        console.print(Panel(
            f"[bold green]ALL PARSING COMPLETE[/bold green]\n\n"
            f"Total time: {overall_elapsed/60:.1f} minutes\n"
            f"Database: {db_path}\n\n"
            f"[yellow]Note: Vector index not built (use --build-index)[/yellow]",
            border_style="green"
        ))
    console.print("="*80 + "\n")


if __name__ == "__main__":
    cli()
