"""
NECB Index Parser Orchestrator

Main entry point for parsing NECB alphabetical indexes.
Coordinates extraction, caching, and database storage.
"""

import logging
from pathlib import Path
from typing import List, Optional

from .config import (
    get_pdf_path,
    get_index_page_range,
    is_valid_vintage,
    VALID_VINTAGES,
)
from .index_models import IndexEntry, IndexParseResult
from .index_extractor import extract_index
from .index_db import init_database, insert_batch, delete_vintage, get_entry_count
from .cache import IndexCacheManager

logger = logging.getLogger(__name__)


def parse_pdf(
    pdf_path: Path,
    vintage: str,
    save_to_cache: bool = True,
    cache_manager: Optional[IndexCacheManager] = None,
) -> IndexParseResult:
    """
    Parse index from a PDF file.

    Args:
        pdf_path: Path to NECB PDF
        vintage: NECB vintage (for metadata)
        save_to_cache: Whether to save to cache
        cache_manager: Optional pre-configured cache manager

    Returns:
        IndexParseResult with parsed entries
    """
    logger.info(f"Parsing index from {pdf_path.name}")

    try:
        # Get page range
        start_page, end_page = get_index_page_range(vintage)
        pages_parsed = end_page - start_page + 1

        # Extract entries
        entries = extract_index(vintage, pdf_path)

        # Create result
        result = IndexParseResult.from_entries(
            entries=entries,
            vintage=vintage,
            pages_parsed=pages_parsed,
        )

        # Save to cache if requested
        if save_to_cache:
            cm = cache_manager or IndexCacheManager()
            cm.cache_entries(
                entries=entries,
                vintage=vintage,
                metadata={
                    "pages_parsed": pages_parsed,
                    "page_range": [start_page + 1, end_page + 1],
                    "pdf_name": pdf_path.name,
                },
            )

        logger.info(
            f"Parsed {result.total_entries} entries "
            f"({result.total_main_terms} main, {result.total_sub_terms} sub, "
            f"{result.total_cross_references} cross-refs)"
        )

        return result

    except Exception as e:
        logger.error(f"Failed to parse {pdf_path}: {e}")
        return IndexParseResult.failure(vintage, str(e))


def parse_vintage(
    vintage: str,
    save_to_db: bool = True,
    save_to_cache: bool = True,
    from_cache: bool = False,
    db_path: Optional[Path] = None,
    cache_manager: Optional[IndexCacheManager] = None,
) -> IndexParseResult:
    """
    Parse index for a specific NECB vintage.

    Args:
        vintage: NECB vintage (e.g., "2020")
        save_to_db: Save to database
        save_to_cache: Save to JSON cache
        from_cache: Load from cache instead of parsing PDF
        db_path: Custom database path
        cache_manager: Pre-configured cache manager

    Returns:
        IndexParseResult
    """
    if not is_valid_vintage(vintage):
        return IndexParseResult.failure(
            vintage,
            f"Invalid vintage: {vintage}. Valid: {VALID_VINTAGES}"
        )

    cm = cache_manager or IndexCacheManager()

    try:
        if from_cache:
            # Load from cache
            logger.info(f"Loading {vintage} index from cache")
            result = cm.load_cached_result(vintage)
        else:
            # Parse from PDF
            pdf_path = get_pdf_path(vintage)
            result = parse_pdf(
                pdf_path=pdf_path,
                vintage=vintage,
                save_to_cache=save_to_cache,
                cache_manager=cm,
            )

        if not result.success:
            return result

        # Save to database if requested
        if save_to_db:
            logger.info(f"Saving {vintage} index to database")
            init_database(db_path)

            # Delete existing entries for this vintage
            deleted = delete_vintage(vintage, db_path)
            if deleted > 0:
                logger.info(f"Deleted {deleted} existing entries for {vintage}")

            # Insert new entries
            inserted = insert_batch(result.entries, db_path)
            logger.info(f"Inserted {inserted} entries for {vintage}")

        return result

    except Exception as e:
        logger.error(f"Failed to parse vintage {vintage}: {e}")
        return IndexParseResult.failure(vintage, str(e))


def parse_all_vintages(
    save_to_db: bool = True,
    save_to_cache: bool = True,
    db_path: Optional[Path] = None,
) -> List[IndexParseResult]:
    """
    Parse index for all valid vintages.

    Args:
        save_to_db: Save to database
        save_to_cache: Save to JSON cache
        db_path: Custom database path

    Returns:
        List of IndexParseResult for each vintage
    """
    results = []
    cm = IndexCacheManager()

    for vintage in sorted(VALID_VINTAGES):
        logger.info(f"Processing vintage {vintage}")
        result = parse_vintage(
            vintage=vintage,
            save_to_db=save_to_db,
            save_to_cache=save_to_cache,
            db_path=db_path,
            cache_manager=cm,
        )
        results.append(result)

    # Summary
    total_entries = sum(r.total_entries for r in results if r.success)
    failed = [r.vintage for r in results if not r.success]

    logger.info(f"Completed: {total_entries} total entries across {len(results)} vintages")
    if failed:
        logger.warning(f"Failed vintages: {failed}")

    return results


def get_parse_status(db_path: Optional[Path] = None) -> dict:
    """
    Get current parsing status.

    Returns:
        Dict with database stats and cache status per vintage
    """
    cm = IndexCacheManager()

    status = {
        "vintages": {},
        "total_entries": 0,
    }

    for vintage in sorted(VALID_VINTAGES):
        vintage_status = {
            "valid": True,
            "db_count": 0,
            "cached": False,
            "cache_info": None,
        }

        # Check database
        try:
            vintage_status["db_count"] = get_entry_count(vintage, db_path)
        except Exception:
            pass

        # Check cache
        vintage_status["cached"] = cm.has_cache(vintage)
        if vintage_status["cached"]:
            vintage_status["cache_info"] = cm.get_cache_info(vintage)

        status["vintages"][vintage] = vintage_status
        status["total_entries"] += vintage_status["db_count"]

    return status
