"""
NECB Index Parser

Extracts the alphabetical index from NECB PDF documents for fast topic lookups.

Usage:
    from bluesky.necb.build.index import parse_vintage, IndexEntry

    # Parse NECB 2020 index
    result = parse_vintage("2020")
    print(f"Parsed {result.total_entries} entries")

    # Query the index
    from bluesky.necb.build.index import get_entries_by_term
    entries = get_entries_by_term("fenestration", "2020")

CLI:
    python -m bluesky.necb.build parse-index --vintage 2020
    python -m bluesky.necb.build parse-index --vintage 2020 --cache-only
    python -m bluesky.necb.build parse-index --vintage 2020 --from-cache
"""

from .index_models import IndexEntry, IndexParseResult, ArticleReference
from .index_parser import (
    parse_pdf,
    parse_vintage,
    parse_all_vintages,
    get_parse_status,
)
from .index_db import (
    init_database,
    get_entry_by_term,
    get_entries_by_term,
    search_entries,
    list_terms,
    get_entries_by_vintage,
    get_entry_count,
    get_vintage_stats,
    delete_vintage,
)
from .cache import IndexCacheManager
from .config import VALID_VINTAGES, INDEX_PAGE_RANGES

__all__ = [
    # Models
    "IndexEntry",
    "IndexParseResult",
    "ArticleReference",
    # Parser functions
    "parse_pdf",
    "parse_vintage",
    "parse_all_vintages",
    "get_parse_status",
    # Database functions
    "init_database",
    "get_entry_by_term",
    "get_entries_by_term",
    "search_entries",
    "list_terms",
    "get_entries_by_vintage",
    "get_entry_count",
    "get_vintage_stats",
    "delete_vintage",
    # Cache
    "IndexCacheManager",
    # Config
    "VALID_VINTAGES",
    "INDEX_PAGE_RANGES",
]
