"""
Section cache manager for NECB article extraction.

Caches extracted articles as JSON files to enable:
1. Database rebuilds without PDF re-parsing
2. Reviewable extraction results before database insert
3. Reproducible builds from cached text files
4. MCP server consumption for LLM-based code agents

Note: Sections use pure regex extraction (no LLM calls), but caching
provides consistency with tables/figures workflow and enables review.

NECB Hierarchy (cached in JSON):
    Division (A, B, C, D)
    └── Part (3)
        └── Section (3.5)
            └── Subsection (3.5.2)
                └── Article (3.5.2.1)
                    └── Sentence (3.5.2.1.(1))
                        └── Clause (3.5.2.1.(1)(a))
                            └── Subclause (3.5.2.1.(1)(a)(i))
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class SectionCacheEntry:
    """Represents a cached article extraction.

    Uses correct NECB terminology:
    - Sentences: numbered elements like 1), 2), 3)
    - Clauses: lettered elements like a), b), c)
    - Subclauses: roman numerals like i), ii), iii)

    Note: part_number, section_number, subsection_number are computed from
    article_number, not stored.
    """

    # Identification
    vintage: str
    article_number: str

    # Content
    title: Optional[str]
    full_text: str
    sentences: list  # List of sentence dicts with nested clauses/subclauses

    # Hierarchy
    division: Optional[str]
    hierarchy_level: str

    # Metadata
    timestamp: str
    page_start: Optional[int]
    page_end: Optional[int]
    success: bool
    equation_count: int = 0  # Number of [Equation:...] tags found in sentences

    @property
    def part_number(self) -> Optional[str]:
        """Extract part number from article number."""
        parts = self.article_number.split(".")
        return parts[0] if len(parts) >= 1 else None

    @property
    def section_number(self) -> Optional[str]:
        """Extract section number from article number."""
        parts = self.article_number.split(".")
        return ".".join(parts[:2]) if len(parts) >= 2 else None

    @property
    def subsection_number(self) -> Optional[str]:
        """Extract subsection number from article number."""
        parts = self.article_number.split(".")
        return ".".join(parts[:3]) if len(parts) >= 3 else None


class SectionCacheManager:
    """Manages caching of extracted articles/sections as JSON files."""

    SCHEMA_VERSION = "2.0.0"  # Bumped for JSON format change

    def __init__(self, cache_dir: Path | str, verbose: bool = False):
        self.cache_dir = Path(cache_dir) / "sections"
        self.verbose = verbose

    def _normalize_article_number(self, article_number: str) -> str:
        """Normalize article number for safe filename.

        Handles special characters like parentheses and slashes.
        """
        safe = article_number.replace("/", "_").replace("(", "").replace(")", "")
        safe = safe.replace(" ", "_")
        return safe

    def get_cache_path(self, vintage: str, article_number: str, division: Optional[str] = None) -> Path:
        """Get path to cache file for an article.

        Path format: cache/sections/{vintage}/{division}/{article_number}.json
        Division defaults to 'unknown' if not provided.
        """
        safe_name = self._normalize_article_number(article_number)
        div = division or "unknown"
        vintage_dir = self.cache_dir / vintage / div
        return vintage_dir / f"{safe_name}.json"

    def has_cache(self, vintage: str, article_number: str, division: Optional[str] = None) -> bool:
        """Check if cache exists for article."""
        return self.get_cache_path(vintage, article_number, division).exists()

    def load(self, vintage: str, article_number: str, division: Optional[str] = None) -> SectionCacheEntry | None:
        """Load cached entry if exists and valid."""
        cache_path = self.get_cache_path(vintage, article_number, division)
        if not cache_path.exists():
            return None

        try:
            return self._parse_cache_file(cache_path)
        except Exception as e:
            if self.verbose:
                print(f"Cache load failed for {vintage}/{division}/{article_number}: {e}")
            return None

    def save(self, entry: SectionCacheEntry) -> Path:
        """Save cache entry to disk as JSON."""
        cache_path = self.get_cache_path(entry.vintage, entry.article_number, entry.division)
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        content = self._format_cache_file(entry)
        cache_path.write_text(content, encoding="utf-8")

        if self.verbose:
            print(f"Cached: {cache_path}")

        return cache_path

    def _format_cache_file(self, entry: SectionCacheEntry) -> str:
        """Format cache entry as JSON.

        Schema designed for MCP server consumption:
        - full_text: for LLM context and semantic search embeddings
        - sentences: for precise reference lookups
        """
        data = {
            "schema_version": self.SCHEMA_VERSION,
            "vintage": entry.vintage,
            "article_number": entry.article_number,
            "title": entry.title,
            "division": entry.division,
            "hierarchy_level": entry.hierarchy_level,
            "full_text": entry.full_text,
            "sentences": entry.sentences,
            "equation_count": entry.equation_count,
            "page_start": entry.page_start,
            "page_end": entry.page_end,
            "timestamp": entry.timestamp,
            "success": entry.success,
        }

        return json.dumps(data, ensure_ascii=False, indent=2)

    def _parse_cache_file(self, path: Path) -> SectionCacheEntry:
        """Parse JSON cache file into SectionCacheEntry."""
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)

        return SectionCacheEntry(
            vintage=data["vintage"],
            article_number=data["article_number"],
            title=data.get("title"),
            full_text=data.get("full_text", ""),
            sentences=data.get("sentences", []),
            division=data.get("division"),
            hierarchy_level=data.get("hierarchy_level", "article"),
            page_start=data.get("page_start"),
            page_end=data.get("page_end"),
            timestamp=data.get("timestamp", ""),
            success=data.get("success", True),
            equation_count=data.get("equation_count", 0),
        )

    def list_cached_sections(self, vintage: str | None = None) -> list[tuple[str, str, str]]:
        """List all cached sections, optionally filtered by vintage.

        Returns:
            List of (vintage, division, article_number) tuples
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
            # Division subdirectories under vintage
            for div_dir in vdir.iterdir():
                if not div_dir.is_dir():
                    continue
                division = div_dir.name
                for cache_file in div_dir.glob("*.json"):
                    v = vdir.name
                    article_number = cache_file.stem
                    results.append((v, division, article_number))

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
                # Clear both .json and legacy .md files
                for pattern in ["**/*.json", "**/*.md"]:
                    for f in vintage_dir.glob(pattern):
                        f.unlink()
                        count += 1
        else:
            if self.cache_dir.exists():
                for vdir in self.cache_dir.iterdir():
                    if vdir.is_dir():
                        for pattern in ["**/*.json", "**/*.md"]:
                            for f in vdir.glob(pattern):
                                f.unlink()
                                count += 1

        return count


def create_section_cache_entry(
    vintage: str,
    article_number: str,
    title: Optional[str],
    full_text: str,
    sentences: list,
    division: Optional[str] = None,
    hierarchy_level: str = "article",
    page_start: Optional[int] = None,
    page_end: Optional[int] = None,
    success: bool = True,
    equation_count: int = 0,
) -> SectionCacheEntry:
    """Helper to create a cache entry with current timestamp.

    Args:
        vintage: NECB vintage year (2020)
        article_number: Article number (e.g., '3.5.2.1')
        title: Article title
        full_text: Complete article text
        sentences: List of sentence dictionaries with nested clauses/subclauses
        division: Division letter (A, B, C, D)
        hierarchy_level: Level in hierarchy
        page_start: Starting page in PDF
        page_end: Ending page in PDF
        success: Whether extraction succeeded

    Returns:
        SectionCacheEntry ready to be saved
    """
    return SectionCacheEntry(
        vintage=vintage,
        article_number=article_number,
        title=title,
        full_text=full_text,
        sentences=sentences,
        division=division,
        hierarchy_level=hierarchy_level,
        page_start=page_start,
        page_end=page_end,
        timestamp=datetime.now(timezone.utc).isoformat(),
        success=success,
        equation_count=equation_count,
    )


def count_equations_in_entry(entry: SectionCacheEntry) -> int:
    """Count [Equation:...] tags in all sentence texts.

    Useful for computing equation_count when it's not already set,
    or for verifying the count is accurate.

    Args:
        entry: The cache entry to count equations in

    Returns:
        Number of [Equation:...] tags found across all sentences
    """
    import re

    count = 0
    for sentence in entry.sentences:
        count += len(re.findall(r'\[Equation:[^\]]+\]', sentence.get("text", "")))
    return count


def rebuild_full_text_from_sentences(entry: SectionCacheEntry) -> str:
    """Rebuild full_text from sentence text to ensure equations are synchronized.

    This function reconstructs the full_text field from the sentence texts,
    which contain the correctly extracted equations from LLM vision processing.
    The original full_text may contain placeholder equations that weren't updated.

    Args:
        entry: The cache entry with sentences to rebuild from

    Returns:
        Rebuilt full_text string with correct equations from sentences
    """
    if not entry.sentences:
        return entry.full_text

    parts = []

    # Add article header
    if entry.article_number:
        header = entry.article_number
        if entry.title:
            header += f" {entry.title}"
        parts.append(header)
        # Add title on its own line (NECB format)
        if entry.title:
            parts.append(entry.title)

    # Add each sentence
    for sentence in entry.sentences:
        # Add sentence number and text
        sent_num = sentence.get("sentence_number", "")
        sent_text = sentence.get("text", "")

        if sent_num and sent_text:
            parts.append(f"{sent_num}) {sent_text}")
        elif sent_text:
            parts.append(sent_text)

        # Add clauses if present
        for clause in sentence.get("clauses", []):
            clause_letter = clause.get("clause_letter", "")
            clause_text = clause.get("text", "")

            if clause_letter and clause_text:
                parts.append(f"{clause_letter}) {clause_text}")
            elif clause_text:
                parts.append(clause_text)

            # Add subclauses if present
            for subclause in clause.get("subclauses", []):
                sub_numeral = subclause.get("subclause_numeral", "")
                sub_text = subclause.get("text", "")

                if sub_numeral and sub_text:
                    parts.append(f"{sub_numeral}) {sub_text}")
                elif sub_text:
                    parts.append(sub_text)

    return "\n".join(parts)


def sync_full_text_with_sentences(entry: SectionCacheEntry) -> bool:
    """Sync the full_text field with sentence texts if equations differ.

    Checks if the equations in full_text match those in sentences.
    If they differ (e.g., full_text has placeholder equations), rebuilds
    full_text from sentences.

    Args:
        entry: The cache entry to check and potentially update

    Returns:
        True if full_text was updated, False if no changes needed
    """
    import re

    # Extract equations from full_text
    full_text_equations = re.findall(r'\[Equation:[^\]]+\]', entry.full_text)

    # Extract equations from sentences
    sentence_equations = []
    for sentence in entry.sentences:
        sent_text = sentence.get("text", "")
        sentence_equations.extend(re.findall(r'\[Equation:[^\]]+\]', sent_text))

    # If no equations in either, no sync needed
    if not full_text_equations and not sentence_equations:
        return False

    # Check if any full_text equation looks like a placeholder
    # Placeholder pattern: contains generic/wrong equation like "FIR.FT2"
    has_placeholder = any("FIR.FT2" in eq or "a_2 + (b_2" in eq for eq in full_text_equations)

    # Check if sentence equations look correct (contain real LaTeX like P_{partload})
    has_real_equations = any(
        "_{" in eq or "\\frac" in eq or "\\times" in eq
        for eq in sentence_equations
    )

    if has_placeholder and has_real_equations:
        # Rebuild full_text from sentences
        entry.full_text = rebuild_full_text_from_sentences(entry)
        return True

    return False
