"""
Configuration constants and patterns for NECB article extraction.

Defines thresholds, regex patterns, and settings for all NECB vintages.
"""

import re
from pathlib import Path
from typing import Dict, List, Pattern

from bluesky.necb import DB_PATH, PDF_DIR

# ============================================================
# PATH CONFIGURATION
# ============================================================

# Database path (uses package-level constant)
DATABASE_PATH = DB_PATH

# NECB PDF paths by vintage (only 2020 supported)
PDF_PATHS = {
    "2020": PDF_DIR / "NECB-2020.pdf",
}

# ============================================================
# HEADER & FOOTER CLEANING THRESHOLDS
# ============================================================

# Position-based filtering (percentage of page height)
HEADER_THRESHOLD = 0.10  # Top 10% of page
FOOTER_THRESHOLD = 0.90  # Bottom 10% of page

# Frequency-based filtering (percentage of pages where line appears)
REPEAT_LINE_THRESHOLD = 0.70  # Remove lines appearing on ≥70% of pages

# Minimum line length to consider (filter out stray characters)
MIN_LINE_LENGTH = 3

# ============================================================
# REGEX PATTERNS FOR HEADER/FOOTER ARTIFACTS
# ============================================================

# Patterns to remove from all vintages
# NOTE: Division headers are intentionally NOT removed here - they're handled separately
# by position filtering. Only the running headers (y < 10%) are removed.
HEADER_FOOTER_PATTERNS: List[Pattern] = [
    re.compile(r"^Page\s+\d+", re.IGNORECASE),  # Page numbers
    re.compile(r"^\d+\s*$"),  # Standalone numbers
    re.compile(r"^National\s+Energy\s+Code", re.IGNORECASE),  # NRC header
    re.compile(r"^National\s+Research\s+Council", re.IGNORECASE),  # NRC name
    re.compile(r"©.*National Research Council", re.IGNORECASE),  # Copyright
    # Division headers in running header region removed by position filter, not regex
    re.compile(r"^NECB\s+\d{4}", re.IGNORECASE),  # NECB year in header
    re.compile(r"^\s*$"),  # Blank lines
    re.compile(r"^[-–—]+\s*$"),  # Lines with only dashes
    re.compile(r"^[\.]+\s*$"),  # Lines with only dots
]

# ============================================================
# ARTICLE STRUCTURE PATTERNS
# ============================================================

# Division pattern: "Division A" or "Division B" (standalone)
DIVISION_PATTERN = re.compile(
    r"^Division\s+([A-D])$",
    re.IGNORECASE
)

# Part pattern: "Part 8" or "Part 8 Energy Efficiency"
PART_PATTERN = re.compile(
    r"^Part\s+(\d+)(?:\s+(.+))?$",
    re.IGNORECASE
)

# Section pattern: "Section 8.1" or "8.1." (exactly 2 parts)
# Matches "Section 8.1" or just "8.1." with optional title
SECTION_PATTERN = re.compile(
    r"^(?:Section\s+)?(\d+\.\d+)\.(?!\d)\s*(.*)$",
    re.IGNORECASE
)

# Subsection pattern: "8.1.1." (exactly 3 parts)
# Must have trailing dot and NOT be followed by more digits
SUBSECTION_PATTERN = re.compile(
    r"^(\d+\.\d+\.\d+)\.(?!\d)\s*(.*)$"
)

# Article pattern: "8.1.1.1." (4+ parts)
# Matches 4+ level numbering with trailing dot
# Examples: 3.5.2.1. or 3.5.2.1.2.
ARTICLE_PATTERN = re.compile(
    r"^(\d+\.\d+\.\d+\.\d+(?:\.\d+)*)\.(?!\d)\s*(.*)$"
)

# Sentence pattern: "1)" or "1) Some text"
# Sentences are the numbered elements within an article (e.g., 3.5.2.1.(1))
SENTENCE_PATTERN = re.compile(
    r"^\s*(\d+)\)\s+(.*)$"
)

# Clause pattern: "a)" or "a) Some text"
# Clauses are the lettered elements within a sentence (e.g., 3.5.2.1.(1)(a))
CLAUSE_PATTERN = re.compile(
    r"^\s*([a-z])\)\s+(.*)$"
)

# Subclause pattern (Roman numerals): "i)", "ii)", "iii)"
# Subclauses are the roman numeral elements within a clause (e.g., 3.5.2.1.(1)(a)(i))
SUBCLAUSE_PATTERN = re.compile(
    r"^\s*(i{1,3}|iv|v|vi{0,3}|ix|x)\)\s+(.*)$",
    re.IGNORECASE
)

# ============================================================
# HIERARCHY LEVELS
# ============================================================

class HierarchyLevel:
    """Enumeration of hierarchy levels in NECB documents.

    NECB Hierarchy:
        Division (A, B, C, D)
        └── Part (3)
            └── Section (3.5)
                └── Subsection (3.5.2)
                    └── Article (3.5.2.1)
                        └── Sentence (3.5.2.1.(1))
                            └── Clause (3.5.2.1.(1)(a))
                                └── Subclause (3.5.2.1.(1)(a)(i))
    """
    DIVISION = "division"
    PART = "part"
    SECTION = "section"
    SUBSECTION = "subsection"
    ARTICLE = "article"
    SENTENCE = "sentence"
    CLAUSE = "clause"
    SUBCLAUSE = "subclause"


# ============================================================
# VINTAGE-SPECIFIC CONFIGURATIONS
# ============================================================

# Different vintages may have slight variations in formatting
# These can be extended if needed

VINTAGE_CONFIGS: Dict[str, Dict] = {
    "2020": {
        "header_patterns": HEADER_FOOTER_PATTERNS,
        "has_division_headers": True,
    },
}

# ============================================================
# EXTRACTION CONFIGURATION
# ============================================================

# Text normalization settings
NORMALIZE_WHITESPACE = True
FIX_HYPHENATION = True  # Join hyphenated words split across lines
MERGE_CONTINUATION_LINES = True

# PyMuPDF extraction settings
EXTRACT_MODE = "blocks"  # Use get_text("blocks") for coordinate data

# ============================================================
# DATABASE CONFIGURATION
# ============================================================

# Table names
TABLE_ARTICLES = "necb_articles"
TABLE_SENTENCES = "necb_sentences"  # Contains sentences, clauses, and subclauses

# Batch insert size for performance
BATCH_INSERT_SIZE = 100

# ============================================================
# LOGGING CONFIGURATION
# ============================================================

# Log level for article parser
LOG_LEVEL = "INFO"

# Progress reporting interval (number of pages)
PROGRESS_INTERVAL = 10

# ============================================================
# VALIDATION SETTINGS
# ============================================================

# Minimum article text length to be considered valid
MIN_ARTICLE_LENGTH = 10  # characters

# Maximum article text length (likely an error if exceeded)
MAX_ARTICLE_LENGTH = 50000  # characters

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def get_pdf_path(vintage: str) -> Path:
    """Get the PDF path for a specific vintage.

    Args:
        vintage: NECB vintage year (2011, 2015, 2017, 2020)

    Returns:
        Path to the PDF file

    Raises:
        ValueError: If vintage is not supported
    """
    if vintage not in PDF_PATHS:
        raise ValueError(f"Unsupported vintage: {vintage}. Must be one of {list(PDF_PATHS.keys())}")

    path = PDF_PATHS[vintage]
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    return path


def get_vintage_config(vintage: str) -> Dict:
    """Get configuration for a specific vintage.

    Args:
        vintage: NECB vintage year (2011, 2015, 2017, 2020)

    Returns:
        Dictionary of vintage-specific configuration

    Raises:
        ValueError: If vintage is not supported
    """
    if vintage not in VINTAGE_CONFIGS:
        raise ValueError(f"Unsupported vintage: {vintage}. Must be one of {list(VINTAGE_CONFIGS.keys())}")

    return VINTAGE_CONFIGS[vintage]


def is_valid_vintage(vintage: str) -> bool:
    """Check if a vintage is supported.

    Args:
        vintage: NECB vintage year to check

    Returns:
        True if vintage is supported, False otherwise
    """
    return vintage in PDF_PATHS
