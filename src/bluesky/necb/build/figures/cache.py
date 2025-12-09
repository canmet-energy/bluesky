"""
LLM output cache manager for NECB figure vision enrichment.

Caches Vision API descriptions as markdown files to enable:
1. Database rebuilds without Vision API calls
2. Reproducible builds from cached text files
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml


@dataclass
class FigureCacheEntry:
    """Represents a cached figure vision enrichment."""

    # Identification
    vintage: str
    figure_label: str

    # Content
    ai_description: str

    # Metadata
    caption: str
    page_number: int
    timestamp: str
    llm_model: str
    tokens_used: int
    duration_s: float
    success: bool


class FigureCacheManager:
    """Manages caching of Vision API outputs for figures."""

    SCHEMA_VERSION = "1.0.0"  # Bump when cache format changes

    def __init__(self, cache_dir: Path | str, verbose: bool = False):
        self.cache_dir = Path(cache_dir) / "figures"
        self.verbose = verbose

    def _normalize_label(self, label: str) -> str:
        """Normalize figure label for safe filename.

        Handles special characters like parentheses and slashes.
        """
        # Replace problematic characters
        safe = label.replace("/", "_").replace("(", "").replace(")", "")
        # Remove "Figure " prefix if present
        if safe.lower().startswith("figure "):
            safe = safe[7:]
        return safe

    def get_cache_path(self, vintage: str, figure_label: str) -> Path:
        """Get path to cache file for a figure."""
        safe_name = self._normalize_label(figure_label)
        vintage_dir = self.cache_dir / vintage
        return vintage_dir / f"{safe_name}.md"

    def has_cache(self, vintage: str, figure_label: str) -> bool:
        """Check if cache exists for figure."""
        return self.get_cache_path(vintage, figure_label).exists()

    def load(self, vintage: str, figure_label: str) -> FigureCacheEntry | None:
        """Load cached entry if exists and valid."""
        cache_path = self.get_cache_path(vintage, figure_label)
        if not cache_path.exists():
            return None

        try:
            return self._parse_cache_file(cache_path)
        except Exception as e:
            if self.verbose:
                print(f"Cache load failed for {vintage}/{figure_label}: {e}")
            return None

    def save(self, entry: FigureCacheEntry) -> Path:
        """Save cache entry to disk."""
        cache_path = self.get_cache_path(entry.vintage, entry.figure_label)
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        content = self._format_cache_file(entry)
        cache_path.write_text(content, encoding="utf-8")

        if self.verbose:
            print(f"Cached: {cache_path}")

        return cache_path

    def _format_cache_file(self, entry: FigureCacheEntry) -> str:
        """Format cache entry as markdown with YAML frontmatter."""
        frontmatter = {
            "vintage": entry.vintage,
            "figure_label": entry.figure_label,
            "schema_version": self.SCHEMA_VERSION,
            "caption": entry.caption,
            "page_number": entry.page_number,
            "timestamp": entry.timestamp,
            "llm_model": entry.llm_model,
            "tokens_used": entry.tokens_used,
            "duration_s": round(entry.duration_s, 3),
            "success": entry.success,
        }

        yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)

        return f"""---
{yaml_str}---

# AI Description

{entry.ai_description}
"""

    def _parse_cache_file(self, path: Path) -> FigureCacheEntry:
        """Parse cache file into FigureCacheEntry."""
        content = path.read_text(encoding="utf-8")

        # Split frontmatter and content
        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError("Invalid cache file format: missing frontmatter")

        frontmatter = yaml.safe_load(parts[1])
        body = parts[2]

        # Extract AI description (everything after "# AI Description")
        ai_start = body.find("# AI Description")
        if ai_start != -1:
            ai_description = body[ai_start + len("# AI Description"):].strip()
        else:
            ai_description = body.strip()

        return FigureCacheEntry(
            vintage=frontmatter["vintage"],
            figure_label=frontmatter["figure_label"],
            ai_description=ai_description,
            caption=frontmatter.get("caption", ""),
            page_number=frontmatter.get("page_number", 0),
            timestamp=frontmatter.get("timestamp", ""),
            llm_model=frontmatter.get("llm_model", ""),
            tokens_used=frontmatter.get("tokens_used", 0),
            duration_s=frontmatter.get("duration_s", 0.0),
            success=frontmatter.get("success", False),
        )

    def list_cached_figures(self, vintage: str | None = None) -> list[tuple[str, str]]:
        """List all cached figures, optionally filtered by vintage.

        Returns:
            List of (vintage, figure_label) tuples
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
                # The figure label is stored in frontmatter, but filename is normalized
                figure_label = cache_file.stem
                results.append((v, figure_label))

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


def create_figure_cache_entry(
    vintage: str,
    figure_label: str,
    ai_description: str,
    caption: str,
    page_number: int,
    llm_model: str,
    tokens_used: int,
    duration_s: float,
    success: bool = True,
) -> FigureCacheEntry:
    """Helper to create a cache entry with current timestamp."""
    return FigureCacheEntry(
        vintage=vintage,
        figure_label=figure_label,
        ai_description=ai_description,
        caption=caption,
        page_number=page_number,
        timestamp=datetime.now(timezone.utc).isoformat(),
        llm_model=llm_model,
        tokens_used=tokens_used,
        duration_s=duration_s,
        success=success,
    )
