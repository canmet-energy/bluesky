"""
NECB Index Parser Configuration

Defines page ranges, regex patterns, and utilities for parsing the
alphabetical index from NECB PDF documents.
"""

import re
from pathlib import Path
from typing import Dict, Tuple, Optional

from bluesky.necb import DB_PATH, PDF_DIR, LLM_CACHE_DIR

# Database configuration
DATABASE_PATH = DB_PATH
TABLE_INDEX = "necb_index"
TABLE_INDEX_FTS = "necb_index_fts"

# Cache configuration
CACHE_DIR = LLM_CACHE_DIR / "index"

# PDF paths per vintage
PDF_PATHS: Dict[str, Path] = {
    "2020": PDF_DIR / "NECB-2020.pdf",
    "2017": PDF_DIR / "NECB-2017.pdf",
    "2015": PDF_DIR / "NECB-2015.pdf",
    "2011": PDF_DIR / "NECB-2011.pdf",
}

# Index page ranges per vintage (0-indexed for PyMuPDF)
# These are the pages containing the alphabetical index
# Note: Excludes the unit conversions table on the last page
INDEX_PAGE_RANGES: Dict[str, Tuple[int, int]] = {
    "2020": (302, 313),  # Pages 303-314 in PDF (0-indexed: 302-313), excludes conversions on p.315
    # TODO: Verify page ranges for other vintages
    # "2017": (TBD, TBD),
    # "2015": (TBD, TBD),
    # "2011": (TBD, TBD),
}

# Valid vintages for index parsing
VALID_VINTAGES = {"2020"}  # Expand as other vintages are verified

# =============================================================================
# Regex Patterns
# =============================================================================

# Main term: Starts with uppercase letter, may contain spaces, hyphens, parentheses
# Examples: "Fenestration", "Air-conditioning systems", "Building additions"
MAIN_TERM_PATTERN = re.compile(
    r'^([A-Z][A-Za-z\s\-\(\),/\']+?)(?:\s*\(see\s|,\s*[\d\.]|\s*$)'
)

# Sub-term: Indented with 2+ spaces, followed by description and article refs
# Examples: "  air leakage, 3.2.4.3."
#           "  definition, 1.4.1.2.[A]"
SUB_TERM_PATTERN = re.compile(
    r'^\s{2,}(.+?)(?:,\s*)([\d\.\[\]A-Za-z\s,\-]+)$'
)

# Reference pattern: 2, 3, or 4-level numbering with optional division marker
# Examples:
#   4-level (article): "3.2.4.3", "1.4.1.2.[A]", "8.4.4.21.-G"
#   3-level (subsection): "3.2.2", "5.2.12"
#   2-level (section): "3.2", "5.4"
# Division markers: [A] = Division A, [C] = Division C, no marker = Division B (implied)
ARTICLE_REF_PATTERN = re.compile(
    r'(\d+\.\d+(?:\.\d+)?(?:\.\d+)?)(?:\.-([A-Z]))?(?:\.\[([A-C])\])?'
)

# Cross-reference: "(see ...)" or "(see also ...)"
# Examples: "(see Doors; Windows)", "(see Heating, ventilating...)"
SEE_ALSO_PATTERN = re.compile(
    r'\(see\s+(?:also\s+)?([^)]+)\)',
    re.IGNORECASE
)

# Division marker in article reference: [A], [B], [C]
DIVISION_MARKER_PATTERN = re.compile(r'\[([A-C])\]')

# Line continuation: Entry that continues on next line (no trailing period/reference)
LINE_CONTINUATION_PATTERN = re.compile(
    r'^[A-Za-z\s\-\(\),/\']+$'  # Text only, no article refs
)

# =============================================================================
# Utility Functions
# =============================================================================


def get_pdf_path(vintage: str) -> Path:
    """Get PDF path for a vintage."""
    if vintage not in PDF_PATHS:
        raise ValueError(f"Unknown vintage: {vintage}. Valid: {list(PDF_PATHS.keys())}")
    path = PDF_PATHS[vintage]
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    return path


def get_index_page_range(vintage: str) -> Tuple[int, int]:
    """Get index page range for a vintage (0-indexed)."""
    if vintage not in INDEX_PAGE_RANGES:
        raise ValueError(
            f"Index page range not defined for vintage {vintage}. "
            f"Available: {list(INDEX_PAGE_RANGES.keys())}"
        )
    return INDEX_PAGE_RANGES[vintage]


def is_valid_vintage(vintage: str) -> bool:
    """Check if vintage is valid for index parsing."""
    return vintage in VALID_VINTAGES


def get_cache_path(vintage: str) -> Path:
    """Get cache file path for a vintage."""
    return CACHE_DIR / f"{vintage}.json"


def extract_article_references(text: str) -> list[dict]:
    """
    Extract all article/section references from text.

    Returns list of dicts with:
        - article_number: "3.2.4.3" (or section "3.2", subsection "3.2.2")
        - suffix: "A" (from 8.4.4.21.-A) or None
        - division: "A", "B", "C" - defaults to "B" if no marker present
    """
    refs = []
    for match in ARTICLE_REF_PATTERN.finditer(text):
        # Division markers: [A] = Division A, [C] = Division C
        # No marker = Division B (implied, the default for technical requirements)
        explicit_division = match.group(3)  # From [X]
        division = explicit_division if explicit_division else "B"

        refs.append({
            "article_number": match.group(1),
            "suffix": match.group(2),  # From .-X
            "division": division,
        })
    return refs


def extract_see_also(text: str) -> Optional[str]:
    """Extract cross-reference from '(see ...)' pattern."""
    match = SEE_ALSO_PATTERN.search(text)
    if match:
        return match.group(1).strip()
    return None


def is_main_term_line(line: str) -> bool:
    """Check if line starts a new main term (uppercase, not indented)."""
    if not line or line[0].isspace():
        return False
    # Must start with uppercase letter
    if not line[0].isupper():
        return False
    # Exclude lines that are just article references
    if ARTICLE_REF_PATTERN.match(line.strip()):
        return False
    return True


def is_sub_term_line(line: str) -> bool:
    """Check if line is an indented sub-term."""
    return line.startswith("  ") and not line.startswith("    " * 2)
