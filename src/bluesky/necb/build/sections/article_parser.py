"""
Main orchestration pipeline for NECB article extraction.

Coordinates PDF extraction, cleaning, parsing, and storage.
"""

import argparse
import logging
import time
from pathlib import Path
from typing import List, Optional

from . import config
from .article_db import (
    init_database,
    insert_batch,
    get_article_count,
    get_vintage_stats,
    delete_vintage,
    get_database_info,
)
from .article_detector import parse_document_text
from .article_extractor import extract_document_text, extract_vintage_document
from .article_models import ParseResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================
# MAIN PARSING PIPELINE
# ============================================================

def parse_pdf(
    pdf_path: Path,
    vintage: str,
    apply_cleaning: bool = True,
    save_to_db: bool = True
) -> ParseResult:
    """Parse a single NECB PDF document.

    Args:
        pdf_path: Path to PDF file
        vintage: NECB vintage year
        apply_cleaning: Whether to apply header/footer cleaning
        save_to_db: Whether to save results to database

    Returns:
        ParseResult with extracted articles and statistics
    """
    logger.info(f"Starting parse: {pdf_path.name} (vintage {vintage})")
    start_time = time.time()

    try:
        # Step 1: Extract and clean text
        logger.info("Step 1/3: Extracting text from PDF...")
        cleaned_text, total_pages, extraction_stats = extract_document_text(
            pdf_path, vintage, apply_cleaning
        )

        # Step 2: Parse structure
        logger.info("Step 2/3: Parsing article structure...")
        articles = parse_document_text(cleaned_text, vintage)

        # Step 3: Save to database
        if save_to_db:
            logger.info("Step 3/3: Saving to database...")
            init_database()
            # Delete existing data for this vintage to prevent duplicates
            deleted_count = delete_vintage(vintage)
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} existing articles for vintage {vintage}")
            inserted_count = insert_batch(articles)
            logger.info(f"Saved {inserted_count}/{len(articles)} articles to database")
        else:
            logger.info("Step 3/3: Skipping database save (save_to_db=False)")

        # Calculate statistics
        total_sentences = sum(len(article.sentences) for article in articles)
        processing_time = time.time() - start_time

        # Build result
        result = ParseResult(
            vintage=vintage,
            total_pages=total_pages,
            total_articles=len(articles),
            total_sentences=total_sentences,
            articles=articles,
            processing_time_seconds=processing_time,
            success=True
        )

        logger.info(f"Parse complete: {len(articles)} articles, {total_sentences} sentences "
                   f"in {processing_time:.2f}s")

        return result

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Parse failed: {e}")

        result = ParseResult(
            vintage=vintage,
            total_pages=0,
            total_articles=0,
            total_sentences=0,
            errors=[str(e)],
            processing_time_seconds=processing_time,
            success=False
        )

        return result


def parse_vintage(
    vintage: str,
    apply_cleaning: bool = True,
    save_to_db: bool = True,
    replace_existing: bool = False
) -> ParseResult:
    """Parse NECB PDF by vintage year.

    Args:
        vintage: NECB vintage year (2020)
        apply_cleaning: Whether to apply header/footer cleaning
        save_to_db: Whether to save results to database
        replace_existing: Whether to delete existing articles before inserting

    Returns:
        ParseResult with extracted articles and statistics
    """
    # Validate vintage
    if not config.is_valid_vintage(vintage):
        raise ValueError(f"Invalid vintage: {vintage}. Must be one of {list(config.PDF_PATHS.keys())}")

    # Get PDF path
    pdf_path = config.get_pdf_path(vintage)

    # Delete existing articles if requested
    if replace_existing and save_to_db:
        logger.info(f"Deleting existing articles for vintage {vintage}...")
        deleted_count = delete_vintage(vintage)
        logger.info(f"Deleted {deleted_count} existing articles")

    # Parse PDF
    return parse_pdf(pdf_path, vintage, apply_cleaning, save_to_db)


def parse_all_vintages(
    apply_cleaning: bool = True,
    save_to_db: bool = True,
    replace_existing: bool = False
) -> List[ParseResult]:
    """Parse all NECB vintages.

    Args:
        apply_cleaning: Whether to apply header/footer cleaning
        save_to_db: Whether to save results to database
        replace_existing: Whether to delete existing articles before inserting

    Returns:
        List of ParseResult objects, one per vintage
    """
    logger.info("Starting parse of all NECB vintages")
    start_time = time.time()

    results = []

    for vintage in ["2020"]:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing vintage {vintage}")
        logger.info(f"{'='*60}\n")

        try:
            result = parse_vintage(vintage, apply_cleaning, save_to_db, replace_existing)
            results.append(result)

            # Print summary
            print(result.get_summary())
            print()

        except Exception as e:
            logger.error(f"Failed to process vintage {vintage}: {e}")

            result = ParseResult(
                vintage=vintage,
                total_pages=0,
                total_articles=0,
                total_sentences=0,
                errors=[str(e)],
                success=False
            )
            results.append(result)

    # Overall summary
    total_time = time.time() - start_time
    total_articles = sum(r.total_articles for r in results)
    total_sentences = sum(r.total_sentences for r in results)
    successful = sum(1 for r in results if r.success)

    logger.info(f"\n{'='*60}")
    logger.info("OVERALL SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Vintages processed: {successful}/{len(results)}")
    logger.info(f"Total articles: {total_articles}")
    logger.info(f"Total sentences: {total_sentences}")
    logger.info(f"Total time: {total_time:.2f}s")
    logger.info(f"{'='*60}\n")

    return results


# ============================================================
# CLI INTERFACE
# ============================================================

def main():
    """CLI entry point for article parser."""
    parser = argparse.ArgumentParser(
        description="NECB Article Parser - Extract structured articles from NECB PDFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse single vintage
  python article_parser.py --vintage 2020

  # Parse all vintages
  python article_parser.py --all-vintages

  # Parse with custom PDF
  python article_parser.py --pdf-path NECB-2020.pdf --vintage 2020

  # Parse without saving to database
  python article_parser.py --vintage 2020 --no-save

  # Replace existing articles
  python article_parser.py --vintage 2020 --replace

  # Skip cleaning (no header/footer removal)
  python article_parser.py --vintage 2020 --no-cleaning

  # Show database statistics
  python article_parser.py --stats
        """
    )

    # Parsing options
    parser.add_argument(
        "--vintage",
        type=str,
        choices=["2020"],
        help="NECB vintage year to parse"
    )

    parser.add_argument(
        "--all-vintages",
        action="store_true",
        help="Parse all NECB vintages (2020)"
    )

    parser.add_argument(
        "--pdf-path",
        type=Path,
        help="Custom PDF path (requires --vintage)"
    )

    # Processing options
    parser.add_argument(
        "--no-cleaning",
        action="store_true",
        help="Skip header/footer cleaning"
    )

    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to database"
    )

    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing articles in database"
    )

    # Info options
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show database statistics"
    )

    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize database schema only (no parsing)"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose debug logging"
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Handle --stats
    if args.stats:
        print("\nDatabase Statistics")
        print("=" * 60)

        db_info = get_database_info()

        if not db_info["exists"]:
            print("Database does not exist yet.")
            print(f"Will be created at: {config.DATABASE_PATH}")
        else:
            print(f"Database: {db_info['path']}")
            print(f"Total articles: {db_info['total_articles']}")
            print(f"Total sentences: {db_info['total_sentences']}")
            print("\nArticles by vintage:")
            for vintage, count in sorted(db_info['vintage_stats'].items()):
                print(f"  {vintage}: {count}")

        print("=" * 60)
        return

    # Handle --init-db
    if args.init_db:
        print("Initializing database schema...")
        init_database()
        print(f"Database initialized at: {config.DATABASE_PATH}")
        return

    # Validate arguments
    if not args.vintage and not args.all_vintages:
        parser.error("Must specify either --vintage or --all-vintages")

    if args.pdf_path and not args.vintage:
        parser.error("--pdf-path requires --vintage")

    if args.vintage and args.all_vintages:
        parser.error("Cannot specify both --vintage and --all-vintages")

    # Set processing flags
    apply_cleaning = not args.no_cleaning
    save_to_db = not args.no_save
    replace_existing = args.replace

    # Parse
    if args.all_vintages:
        results = parse_all_vintages(apply_cleaning, save_to_db, replace_existing)

        # Print final summary
        print("\n" + "=" * 60)
        print("PARSING COMPLETE")
        print("=" * 60)

        for result in results:
            status = "✓" if result.success else "✗"
            print(f"{status} {result.vintage}: {result.total_articles} articles")

        print("=" * 60)

    else:
        # Parse single vintage
        if args.pdf_path:
            result = parse_pdf(args.pdf_path, args.vintage, apply_cleaning, save_to_db)
        else:
            result = parse_vintage(args.vintage, apply_cleaning, save_to_db, replace_existing)

        # Print summary
        print("\n" + result.get_summary())

        if result.success:
            print("\n✓ Parsing completed successfully")
        else:
            print("\n✗ Parsing failed")


if __name__ == "__main__":
    main()
