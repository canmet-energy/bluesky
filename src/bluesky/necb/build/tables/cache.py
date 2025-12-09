"""
LLM output cache manager for NECB table parser.

Caches both raw extraction and LLM-repaired output as markdown files to enable:
1. Database rebuilds without LLM calls
2. Schema iteration without PDF re-parsing
3. Reproducible builds from cached text files
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml


@dataclass
class TableCacheEntry:
    """Represents a cached table extraction."""

    # Identification
    vintage: str
    table_number: str

    # Content
    raw_markdown: str
    repaired_json: str  # JSON string before Pydantic validation

    # Metadata
    schema_version: str
    schema_name: str
    timestamp: str
    confidence: float
    method_used: str
    llm_applied: bool
    llm_model: str
    llm_backend: str
    page_number: int
    extraction_time_s: float
    llm_time_s: float
    success: bool
    errors: list[str]


class TableCacheManager:
    """Manages caching of LLM repair outputs for tables."""

    SCHEMA_VERSION = "1.0.0"  # Bump when cache format changes

    def __init__(self, cache_dir: Path | str, verbose: bool = False):
        self.cache_dir = Path(cache_dir)
        self.verbose = verbose

    def _normalize_table_number(self, table_number: str) -> str:
        """Normalize table number for safe filename.

        Handles special characters like parentheses and slashes.
        """
        # Replace problematic characters
        safe = table_number.replace("/", "_").replace("(", "").replace(")", "")
        return safe

    def get_cache_path(self, vintage: str, table_number: str) -> Path:
        """Get path to cache file for a table."""
        safe_name = self._normalize_table_number(table_number)
        vintage_dir = self.cache_dir / vintage
        return vintage_dir / f"{safe_name}.md"

    def has_cache(self, vintage: str, table_number: str) -> bool:
        """Check if cache exists for table."""
        return self.get_cache_path(vintage, table_number).exists()

    def load(self, vintage: str, table_number: str) -> TableCacheEntry | None:
        """Load cached entry if exists and valid."""
        cache_path = self.get_cache_path(vintage, table_number)
        if not cache_path.exists():
            return None

        try:
            return self._parse_cache_file(cache_path)
        except Exception as e:
            if self.verbose:
                print(f"Cache load failed for {vintage}/{table_number}: {e}")
            return None

    def save(self, entry: TableCacheEntry) -> Path:
        """Save cache entry to disk."""
        cache_path = self.get_cache_path(entry.vintage, entry.table_number)
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        content = self._format_cache_file(entry)
        cache_path.write_text(content, encoding="utf-8")

        if self.verbose:
            print(f"Cached: {cache_path}")

        return cache_path

    def _format_cache_file(self, entry: TableCacheEntry) -> str:
        """Format cache entry as markdown with YAML frontmatter."""
        frontmatter = {
            "vintage": entry.vintage,
            "table_number": entry.table_number,
            "schema_version": self.SCHEMA_VERSION,
            "schema_name": entry.schema_name,
            "timestamp": entry.timestamp,
            "confidence": entry.confidence,
            "method_used": entry.method_used,
            "llm_applied": entry.llm_applied,
            "llm_model": entry.llm_model,
            "llm_backend": entry.llm_backend,
            "page_number": entry.page_number,
            "extraction_time_s": round(entry.extraction_time_s, 3),
            "llm_time_s": round(entry.llm_time_s, 3),
            "success": entry.success,
            "errors": entry.errors,
        }

        yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)

        # Escape any triple backticks in content
        raw_escaped = entry.raw_markdown.replace("```", "~~~")
        json_escaped = entry.repaired_json.replace("```", "~~~")

        return f"""---
{yaml_str}---

# Raw Extraction

```markdown
{raw_escaped}
```

# LLM Repaired Output

```json
{json_escaped}
```
"""

    def _parse_cache_file(self, path: Path) -> TableCacheEntry:
        """Parse cache file into TableCacheEntry."""
        content = path.read_text(encoding="utf-8")

        # Split frontmatter and content
        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError("Invalid cache file format: missing frontmatter")

        frontmatter = yaml.safe_load(parts[1])
        body = parts[2]

        # Extract raw markdown (between ```markdown and ```)
        raw_match = re.search(r"```markdown\n(.*?)\n```", body, re.DOTALL)
        raw_markdown = raw_match.group(1) if raw_match else ""
        # Unescape
        raw_markdown = raw_markdown.replace("~~~", "```")

        # Extract repaired JSON (between ```json and ```)
        json_match = re.search(r"```json\n(.*?)\n```", body, re.DOTALL)
        repaired_json = json_match.group(1) if json_match else ""
        # Unescape
        repaired_json = repaired_json.replace("~~~", "```")

        return TableCacheEntry(
            vintage=frontmatter["vintage"],
            table_number=frontmatter["table_number"],
            raw_markdown=raw_markdown,
            repaired_json=repaired_json,
            schema_version=frontmatter.get("schema_version", "unknown"),
            schema_name=frontmatter.get("schema_name", "unknown"),
            timestamp=frontmatter.get("timestamp", ""),
            confidence=frontmatter.get("confidence", 0.0),
            method_used=frontmatter.get("method_used", "unknown"),
            llm_applied=frontmatter.get("llm_applied", False),
            llm_model=frontmatter.get("llm_model", ""),
            llm_backend=frontmatter.get("llm_backend", ""),
            page_number=frontmatter.get("page_number", 0),
            extraction_time_s=frontmatter.get("extraction_time_s", 0.0),
            llm_time_s=frontmatter.get("llm_time_s", 0.0),
            success=frontmatter.get("success", False),
            errors=frontmatter.get("errors", []),
        )

    def list_cached_tables(self, vintage: str | None = None) -> list[tuple[str, str]]:
        """List all cached tables, optionally filtered by vintage.

        Returns:
            List of (vintage, table_number) tuples
        """
        results = []

        if vintage:
            vintage_dirs = [self.cache_dir / vintage]
        else:
            if not self.cache_dir.exists():
                return []
            vintage_dirs = [d for d in self.cache_dir.iterdir() if d.is_dir()]

        for vdir in vintage_dirs:
            if not vdir.exists():
                continue
            for cache_file in vdir.glob("*.md"):
                v = vdir.name
                # The table number is the filename stem
                # Note: some normalization was applied, but we store original in frontmatter
                table_num = cache_file.stem
                results.append((v, table_num))

        return results

    def clear_cache(self, vintage: str | None = None) -> int:
        """Clear cached files, optionally for a specific vintage.

        Returns:
            Number of files deleted
        """
        count = 0

        if vintage:
            vintage_dir = self.cache_dir / vintage
            if vintage_dir.exists():
                for f in vintage_dir.glob("*.md"):
                    f.unlink()
                    count += 1
        else:
            if self.cache_dir.exists():
                for vdir in self.cache_dir.iterdir():
                    if vdir.is_dir():
                        for f in vdir.glob("*.md"):
                            f.unlink()
                            count += 1

        return count


def create_cache_entry(
    vintage: str,
    table_number: str,
    raw_markdown: str,
    repaired_json: str,
    schema_name: str,
    confidence: float,
    method_used: str,
    llm_model: str,
    llm_backend: str,
    page_number: int,
    extraction_time_s: float,
    llm_time_s: float,
    success: bool = True,
    errors: list[str] | None = None,
) -> TableCacheEntry:
    """Helper to create a cache entry with current timestamp."""
    return TableCacheEntry(
        vintage=vintage,
        table_number=table_number,
        raw_markdown=raw_markdown,
        repaired_json=repaired_json,
        schema_version=TableCacheManager.SCHEMA_VERSION,
        schema_name=schema_name,
        timestamp=datetime.now(timezone.utc).isoformat(),
        confidence=confidence,
        method_used=method_used,
        llm_applied=True,
        llm_model=llm_model,
        llm_backend=llm_backend,
        page_number=page_number,
        extraction_time_s=extraction_time_s,
        llm_time_s=llm_time_s,
        success=success,
        errors=errors or [],
    )
