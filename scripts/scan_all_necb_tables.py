#!/usr/bin/env python3
"""Comprehensive NECB Table Scanner - CLI Wrapper

Scans entire NECB PDF and creates complete inventory of ALL tables.

Uses formatting-based detection (bold + centered titles) to find tables,
then verifies table presence and records metadata.

Usage:
    python scripts/scan_all_necb_tables.py --vintage 2020
    python scripts/scan_all_necb_tables.py --vintage 2020 --start-page 30 --end-page 250
    python scripts/scan_all_necb_tables.py --all-vintages
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import click
from bluesky.necb.build.tables.table_scanner import NECBTableScanner


PDF_DIR = Path(__file__).parent.parent / "data/necb/pdfs"


@click.command()
@click.option('--vintage', type=click.Choice(['2011', '2015', '2017', '2020']), help='NECB vintage')
@click.option('--all-vintages', is_flag=True, help='Scan all vintages')
@click.option('--start-page', type=int, default=30, help='Start scan from page (skip TOC)')
@click.option('--end-page', type=int, help='End scan at page')
@click.option('--output', type=click.Path(), help='Save results to JSON')
@click.option('--verbose', is_flag=True, help='Show detailed progress')
def main(vintage, all_vintages, start_page, end_page, output, verbose):
    """Scan NECB PDF for ALL tables and create comprehensive inventory"""

    results = {}

    # Determine what to scan
    if all_vintages:
        vintages = ['2011', '2015', '2017', '2020']
    elif vintage:
        vintages = [vintage]
    else:
        click.echo("Error: Specify --vintage or --all-vintages")
        return

    # Create scanner
    scanner = NECBTableScanner(verbose=verbose)

    click.echo("="*80)
    click.echo("COMPREHENSIVE NECB TABLE SCANNER")
    click.echo("="*80)
    click.echo(f"Method: Bold + Centered text detection")
    click.echo(f"Vintages: {', '.join(vintages)}")
    click.echo(f"Scan range: pages {start_page+1}-{end_page or 'end'}")
    click.echo()

    for vintage in vintages:
        pdf_path = PDF_DIR / f"NECB-{vintage}.pdf"

        if not pdf_path.exists():
            click.echo(f"⚠️  PDF not found: {pdf_path}")
            continue

        click.echo(f"\n{'='*80}")
        click.echo(f"NECB {vintage}")
        click.echo(f"{'='*80}\n")

        # Scan PDF using library
        tables = scanner.scan_pdf(pdf_path, start_page, end_page)

        # Show progress if verbose
        if verbose:
            for table in tables:
                forming = " (Forming Part ✓)" if table['has_forming_part'] else ""
                if table['has_continuation']:
                    page_range = f"Pages {table['all_pages'][0]+1}-{table['all_pages'][-1]+1} ({table['page_count']} pages)"
                    cont_indicator = f" ({table['page_count']} pages)"
                else:
                    page_range = f"Page {table['page_num']+1:3}"
                    cont_indicator = ""
                desc_preview = f" | {table['table_description'][:40]}..." if table.get('table_description') else ""
                click.echo(
                    f"  {page_range:20}: {table['table_number']:15} - "
                    f"{table['estimated_rows']}×{table['estimated_cols']}, "
                    f"score={table['score']}{forming}{cont_indicator}{desc_preview}"
                )

        # Remove duplicates (keep highest score for each table number)
        unique_tables = {}
        for table in tables:
            table_num = table['table_number']
            if table_num not in unique_tables or table['score'] > unique_tables[table_num]['score']:
                unique_tables[table_num] = table

        results[vintage] = {
            'total_found': len(unique_tables),
            'tables': dict(sorted(unique_tables.items()))
        }

        click.echo(f"\n✅ Found {len(unique_tables)} unique tables in NECB {vintage}")

        # Show summary by section
        sections = {}
        for table_num in unique_tables.keys():
            section = table_num.split('.')[0]
            sections[section] = sections.get(section, 0) + 1

        click.echo("\nTables by section:")
        for section, count in sorted(sections.items()):
            click.echo(f"  Section {section}: {count} tables")

    # Overall summary
    click.echo("\n" + "="*80)
    click.echo("SCAN SUMMARY")
    click.echo("="*80)

    for vintage in vintages:
        if vintage in results:
            click.echo(f"\n{vintage}: {results[vintage]['total_found']} tables found")

    # Save results
    if output:
        output_path = Path(output)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        click.echo(f"\n✅ Results saved to: {output_path}")

    # Show sample of found tables
    if vintages and not verbose:
        sample_vintage = vintages[0]
        if sample_vintage in results:
            click.echo(f"\n{'='*80}")
            click.echo(f"SAMPLE: First 10 tables from NECB {sample_vintage}")
            click.echo(f"{'='*80}\n")

            sample_tables = list(results[sample_vintage]['tables'].items())[:10]
            for table_num, info in sample_tables:
                forming = " (Forming Part ✓)" if info['has_forming_part'] else ""
                click.echo(
                    f"  {table_num:15} → page {info['page_display']:3} "
                    f"({info['estimated_rows']}×{info['estimated_cols']}, "
                    f"score={info['score']}){forming}"
                )

    click.echo()


if __name__ == "__main__":
    main()
