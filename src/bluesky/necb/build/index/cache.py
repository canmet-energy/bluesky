"""
NECB Index Cache Manager

JSON-based caching for the 2-phase workflow:
- Phase 1 (--cache-only): Parse PDF → JSON cache
- Phase 2 (--from-cache): JSON cache → Database
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .config import CACHE_DIR
from .index_models import IndexEntry, IndexParseResult

logger = logging.getLogger(__name__)


class IndexCacheManager:
    """Manage JSON cache for parsed index entries."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize cache manager.

        Args:
            cache_dir: Cache directory (default: data/necb/cache/index/)
        """
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_path(self, vintage: str) -> Path:
        """Get cache file path for a vintage."""
        return self.cache_dir / f"{vintage}.json"

    def cache_entries(
        self,
        entries: List[IndexEntry],
        vintage: str,
        metadata: Optional[dict] = None,
    ) -> Path:
        """
        Save parsed entries to JSON cache.

        Args:
            entries: List of IndexEntry objects
            vintage: NECB vintage
            metadata: Optional metadata to include

        Returns:
            Path to cache file
        """
        cache_file = self.get_cache_path(vintage)

        # Build cache data with metadata
        cache_data = {
            "vintage": vintage,
            "cached_at": datetime.now().isoformat(),
            "entry_count": len(entries),
            "metadata": metadata or {},
            "entries": [entry.model_dump() for entry in entries],
        }

        cache_file.write_text(json.dumps(cache_data, indent=2, ensure_ascii=False))
        logger.info(f"Cached {len(entries)} index entries to {cache_file}")

        return cache_file

    def load_cached_entries(self, vintage: str) -> List[IndexEntry]:
        """
        Load entries from cache.

        Args:
            vintage: NECB vintage

        Returns:
            List of IndexEntry objects

        Raises:
            FileNotFoundError: If cache doesn't exist
        """
        cache_file = self.get_cache_path(vintage)

        if not cache_file.exists():
            raise FileNotFoundError(f"No cache for vintage {vintage}: {cache_file}")

        cache_data = json.loads(cache_file.read_text())
        entries = [IndexEntry(**item) for item in cache_data["entries"]]

        logger.info(
            f"Loaded {len(entries)} index entries from cache "
            f"(cached at {cache_data.get('cached_at', 'unknown')})"
        )

        return entries

    def load_cached_result(self, vintage: str) -> IndexParseResult:
        """
        Load cached entries as IndexParseResult.

        Args:
            vintage: NECB vintage

        Returns:
            IndexParseResult with entries and stats
        """
        cache_file = self.get_cache_path(vintage)

        if not cache_file.exists():
            raise FileNotFoundError(f"No cache for vintage {vintage}: {cache_file}")

        cache_data = json.loads(cache_file.read_text())
        entries = [IndexEntry(**item) for item in cache_data["entries"]]

        # Get pages_parsed from metadata if available
        pages_parsed = cache_data.get("metadata", {}).get("pages_parsed", 0)

        return IndexParseResult.from_entries(
            entries=entries,
            vintage=vintage,
            pages_parsed=pages_parsed,
        )

    def has_cache(self, vintage: str) -> bool:
        """Check if cache exists for a vintage."""
        return self.get_cache_path(vintage).exists()

    def list_cached_vintages(self) -> List[str]:
        """List vintages with cached index data."""
        return sorted([f.stem for f in self.cache_dir.glob("*.json")])

    def get_cache_info(self, vintage: str) -> Optional[dict]:
        """
        Get cache metadata without loading all entries.

        Returns:
            Dict with vintage, cached_at, entry_count, or None if no cache
        """
        cache_file = self.get_cache_path(vintage)

        if not cache_file.exists():
            return None

        cache_data = json.loads(cache_file.read_text())

        return {
            "vintage": cache_data.get("vintage"),
            "cached_at": cache_data.get("cached_at"),
            "entry_count": cache_data.get("entry_count"),
            "file_size": cache_file.stat().st_size,
            "metadata": cache_data.get("metadata", {}),
        }

    def delete_cache(self, vintage: str) -> bool:
        """
        Delete cache for a vintage.

        Returns:
            True if deleted, False if didn't exist
        """
        cache_file = self.get_cache_path(vintage)

        if cache_file.exists():
            cache_file.unlink()
            logger.info(f"Deleted cache for {vintage}")
            return True

        return False

    def clear_all_caches(self) -> int:
        """
        Delete all cached vintages.

        Returns:
            Count of deleted cache files
        """
        deleted = 0
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            deleted += 1

        logger.info(f"Deleted {deleted} cache files")
        return deleted
