"""
Regex-based header and footer removal for NECB PDFs.

Uses pattern matching to identify and remove known header/footer text,
while preserving all article content regardless of page position.
"""

import logging
import re
from typing import List, Set

from . import config

logger = logging.getLogger(__name__)


# ============================================================
# DATA STRUCTURES
# ============================================================

class TextBlock:
    """Represents a text block with coordinates from PyMuPDF."""

    def __init__(self, x0: float, y0: float, x1: float, y1: float, text: str, page_num: int):
        """Initialize text block.

        Args:
            x0: Left x-coordinate
            y0: Top y-coordinate
            x1: Right x-coordinate
            y1: Bottom y-coordinate
            text: Block text content
            page_num: Page number (0-indexed)
        """
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
        self.text = text
        self.page_num = page_num

    def __repr__(self) -> str:
        display_text = self.text.strip().replace('\n', '\\n')
        return f"TextBlock(page={self.page_num}, y0={self.y0:.1f}, text='{display_text[:30]}...')"


# ============================================================
# HEADER/FOOTER PATTERNS
# ============================================================

# Running page headers - these appear at top of each page
# Format: "Division B \n4.3.2.X." or "4.3.2.X. \nDivision B"
RUNNING_HEADER_PATTERNS = [
    # "Division B" alone or "Division B \n<article number>"
    re.compile(r'^Division\s+[A-D]\s*$', re.IGNORECASE),
    # Block that is ONLY "Division B \n<number>" (running header, not article content)
    re.compile(r'^Division\s+[A-D]\s*\n\s*\d+\.\d+\.\d+\.\d+\.?\s*$', re.IGNORECASE | re.MULTILINE),
    # Block that is ONLY "<number> \nDivision B" (running header, not article content)
    re.compile(r'^\d+\.\d+\.\d+\.\d+\.?\s*\n\s*Division\s+[A-D]\s*$', re.IGNORECASE | re.MULTILINE),
]

# Page footer patterns - these appear at bottom of each page
PAGE_FOOTER_PATTERNS = [
    # "National Energy Code of Canada for Buildings 2020"
    re.compile(r'^National\s+Energy\s+Code\s+of\s+Canada\s+for\s+Buildings\s+\d{4}', re.IGNORECASE),
    # "Division B 5-9" (page number format)
    re.compile(r'^Division\s+[A-D]\s+\d+-\d+\s*$', re.IGNORECASE),
    # "5-9 Division B" (alternate page number format)
    re.compile(r'^\d+-\d+\s+Division\s+[A-D]\s*$', re.IGNORECASE),
    # Copyright notices
    re.compile(r'^Copyright\s+©', re.IGNORECASE),
    re.compile(r'Droits\s+réservés', re.IGNORECASE),
    re.compile(r'World\s+Rights\s+Reserved', re.IGNORECASE),
    # "NECB 2020" standalone
    re.compile(r'^NECB\s+\d{4}\s*$', re.IGNORECASE),
]

# Lines within blocks that should be removed (artifacts from page breaks)
ARTIFACT_LINE_PATTERNS = [
    re.compile(r'^National\s+Energy\s+Code\s+of\s+Canada', re.IGNORECASE),
    re.compile(r'^Division\s+[A-D]\s+\d+-\d+\s*$', re.IGNORECASE),
    re.compile(r'^\d+-\d+\s+Division\s+[A-D]\s*$', re.IGNORECASE),
    re.compile(r'^Copyright\s+©', re.IGNORECASE),
    re.compile(r'Droits\s+réservés', re.IGNORECASE),
    re.compile(r'World\s+Rights\s+Reserved', re.IGNORECASE),
    re.compile(r'^NECB\s+\d{4}\s*$', re.IGNORECASE),
]


# ============================================================
# BLOCK-LEVEL FILTERING
# ============================================================

def is_running_header_block(text: str) -> bool:
    """Check if entire block is a running page header.

    Running headers are blocks containing ONLY:
    - "Division B" alone
    - "Division B \n4.3.2.X." (no title, just the number)
    - "4.3.2.X. \nDivision B" (no title, just the number)

    Real article headers have a title after the number.

    Args:
        text: Block text content

    Returns:
        True if block is a running header (should be removed)
    """
    stripped = text.strip()

    for pattern in RUNNING_HEADER_PATTERNS:
        if pattern.match(stripped):
            return True

    return False


def is_page_footer_block(text: str) -> bool:
    """Check if entire block is a page footer.

    Args:
        text: Block text content

    Returns:
        True if block is a page footer (should be removed)
    """
    stripped = text.strip()

    for pattern in PAGE_FOOTER_PATTERNS:
        if pattern.match(stripped):
            return True

    return False


# ============================================================
# LINE-LEVEL CLEANING
# ============================================================

def is_artifact_line(line: str) -> bool:
    """Check if a single line is a header/footer artifact.

    These can appear within article content when content spans page breaks.

    Args:
        line: Single line of text

    Returns:
        True if line is an artifact (should be removed)
    """
    stripped = line.strip()
    if not stripped:
        return False

    for pattern in ARTIFACT_LINE_PATTERNS:
        if pattern.match(stripped):
            return True

    return False


def clean_block_text(text: str) -> str:
    """Clean artifact lines from within a text block.

    Removes header/footer lines that appear embedded in article content
    due to page breaks, while preserving actual content.

    Args:
        text: Block text content (may contain multiple lines)

    Returns:
        Cleaned text with artifact lines removed
    """
    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        # Keep empty lines for paragraph structure
        if not line.strip():
            cleaned_lines.append(line)
            continue

        # Skip artifact lines
        if is_artifact_line(line):
            logger.debug(f"Removed artifact line: {line[:60]}")
            continue

        # Skip very short lines (likely stray characters)
        if len(line.strip()) < config.MIN_LINE_LENGTH:
            continue

        cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


# ============================================================
# MAIN CLEANING FUNCTION
# ============================================================

def clean_blocks(blocks: List[TextBlock], vintage: str) -> List[TextBlock]:
    """Clean text blocks by removing headers/footers using regex patterns.

    Two-stage cleaning:
    1. Remove entire blocks that are running headers or page footers
    2. Clean artifact lines from within remaining blocks

    Args:
        blocks: List of text blocks from a page
        vintage: NECB vintage year (for future vintage-specific patterns)

    Returns:
        List of cleaned blocks
    """
    filtered_blocks = []
    removed_blocks = 0
    cleaned_blocks = 0

    for block in blocks:
        original_text = block.text

        # Stage 1: Check if entire block is header/footer
        if is_running_header_block(original_text):
            logger.debug(f"Removed running header block: {original_text[:50]}")
            removed_blocks += 1
            continue

        if is_page_footer_block(original_text):
            logger.debug(f"Removed page footer block: {original_text[:50]}")
            removed_blocks += 1
            continue

        # Stage 2: Clean artifact lines from within the block
        cleaned_text = clean_block_text(original_text)

        # Skip if block is now empty
        if not cleaned_text.strip():
            logger.debug(f"Removed empty block after cleaning: {original_text[:50]}")
            removed_blocks += 1
            continue

        # Track if we cleaned anything
        if cleaned_text != original_text:
            cleaned_blocks += 1
            # Create new block with cleaned text
            cleaned_block = TextBlock(
                x0=block.x0, y0=block.y0, x1=block.x1, y1=block.y1,
                text=cleaned_text, page_num=block.page_num
            )
            filtered_blocks.append(cleaned_block)
        else:
            filtered_blocks.append(block)

    logger.debug(f"Cleaned page: removed {removed_blocks} blocks, cleaned {cleaned_blocks} blocks, kept {len(filtered_blocks)}")
    return filtered_blocks


def clean_pages(
    pages_blocks: List[List[TextBlock]],
    page_height: float,
    vintage: str
) -> List[List[TextBlock]]:
    """Clean all pages using regex-based pattern matching.

    Args:
        pages_blocks: List of block lists, one per page
        page_height: Page height in points (unused, kept for API compatibility)
        vintage: NECB vintage year

    Returns:
        List of cleaned block lists
    """
    logger.info(f"Starting regex-based cleaning for {len(pages_blocks)} pages")

    initial_blocks = sum(len(page_blocks) for page_blocks in pages_blocks)
    logger.info(f"Initial block count: {initial_blocks}")

    cleaned_pages = []
    for page_blocks in pages_blocks:
        cleaned = clean_blocks(page_blocks, vintage)
        cleaned_pages.append(cleaned)

    final_blocks = sum(len(page_blocks) for page_blocks in cleaned_pages)
    removed = initial_blocks - final_blocks
    removal_rate = (removed / initial_blocks * 100) if initial_blocks > 0 else 0

    logger.info(f"Cleaning complete: {removed} blocks removed ({removal_rate:.1f}%), {final_blocks} blocks remaining")

    return cleaned_pages


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def blocks_to_text(blocks: List[TextBlock]) -> str:
    """Convert blocks to plain text.

    Args:
        blocks: List of text blocks

    Returns:
        Concatenated text with newlines between blocks
    """
    return "\n".join(block.text for block in blocks if block.text.strip())


def merge_page_blocks(pages_blocks: List[List[TextBlock]], include_page_markers: bool = True) -> str:
    """Merge all page blocks into single text string.

    Args:
        pages_blocks: List of block lists, one per page
        include_page_markers: Whether to include page boundary markers for tracking

    Returns:
        Complete document text with optional page markers
    """
    all_text = []

    for page_num, page_blocks in enumerate(pages_blocks):
        # Add page marker at start of each page for tracking
        if include_page_markers:
            all_text.append(f"<<<PAGE:{page_num}>>>")

        page_text = blocks_to_text(page_blocks)
        if page_text:
            all_text.append(page_text)

    return "\n\n".join(all_text)


def get_cleaning_stats(
    original_pages: List[List[TextBlock]],
    cleaned_pages: List[List[TextBlock]]
) -> dict:
    """Calculate cleaning statistics.

    Args:
        original_pages: Original page blocks before cleaning
        cleaned_pages: Cleaned page blocks after cleaning

    Returns:
        Dictionary with cleaning statistics
    """
    original_count = sum(len(page_blocks) for page_blocks in original_pages)
    cleaned_count = sum(len(page_blocks) for page_blocks in cleaned_pages)
    removed_count = original_count - cleaned_count
    removal_rate = (removed_count / original_count * 100) if original_count > 0 else 0

    return {
        "original_blocks": original_count,
        "cleaned_blocks": cleaned_count,
        "removed_blocks": removed_count,
        "removal_rate_percent": removal_rate,
        "pages_processed": len(original_pages),
    }
