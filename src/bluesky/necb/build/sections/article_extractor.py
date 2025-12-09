"""
PDF text extraction using PyMuPDF with coordinate-based cleaning.

Extracts text blocks from NECB PDFs and applies header/footer cleaning.
Includes OCR-based equation extraction for vector graphics equations.
"""

import logging
import re
from pathlib import Path
from typing import List, Tuple

import fitz  # PyMuPDF

from . import config
from .header_footer_cleaner import TextBlock, clean_pages, merge_page_blocks

logger = logging.getLogger(__name__)


# ============================================================
# RUNNING HEADER DETECTION
# ============================================================

# Font used for running headers in NECB PDFs
RUNNING_HEADER_FONTS = {
    "HelveticaLTPro-BlackObli",  # Italic header font used for page running headers
}

# Y-coordinate threshold for running header zone (top of page)
RUNNING_HEADER_Y_THRESHOLD = 50.0

# Pattern matching article numbers in running headers (e.g., "4.3.2.7.")
ARTICLE_NUMBER_PATTERN = re.compile(r'^\d+\.\d+\.\d+\.\d+\.?$')


def is_running_header_span(span: dict, y_threshold: float = RUNNING_HEADER_Y_THRESHOLD) -> bool:
    """Check if a text span is a running header that should be filtered out.

    Running headers in NECB PDFs appear at the top of each page showing the
    current article number. They use a distinctive italic font and should
    not be confused with actual article headers in the body text.

    Args:
        span: PyMuPDF span dict with 'text', 'font', 'bbox' keys
        y_threshold: Y-coordinate below which headers are considered running headers

    Returns:
        True if this span is a running header that should be filtered
    """
    text = span.get("text", "").strip()
    font = span.get("font", "")
    bbox = span.get("bbox", (0, 0, 0, 0))
    y_position = bbox[1]  # Top Y coordinate of the span

    # Check all conditions for running header
    if font in RUNNING_HEADER_FONTS:
        if y_position < y_threshold:
            if ARTICLE_NUMBER_PATTERN.match(text):
                logger.debug(f"Filtering running header: '{text}' at Y={y_position:.0f}")
                return True

    return False


# ============================================================
# PDF LOADING
# ============================================================

def load_pdf(pdf_path: Path) -> fitz.Document:
    """Load PDF document using PyMuPDF.

    Args:
        pdf_path: Path to PDF file

    Returns:
        PyMuPDF Document object

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        RuntimeError: If PDF cannot be loaded
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    try:
        doc = fitz.open(pdf_path)
        logger.info(f"Loaded PDF: {pdf_path} ({doc.page_count} pages)")
        return doc
    except Exception as e:
        raise RuntimeError(f"Failed to load PDF {pdf_path}: {e}")


# ============================================================
# TEXT BLOCK EXTRACTION
# ============================================================

def extract_text_blocks(
    page: fitz.Page,
    page_num: int,
    filter_running_headers: bool = True
) -> List[TextBlock]:
    """Extract text blocks with coordinates from a PDF page.

    Args:
        page: PyMuPDF Page object
        page_num: Page number (0-indexed)
        filter_running_headers: Whether to filter out running header article numbers

    Returns:
        List of TextBlock objects with coordinates
    """
    blocks = []
    running_headers_filtered = 0

    # Use dict extraction to get font information for running header detection
    page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:  # Skip non-text blocks (images, etc.)
            continue

        # Collect text spans, filtering running headers if enabled
        block_lines = []
        block_bbox = None

        for line in block.get("lines", []):
            line_text_parts = []
            for span in line.get("spans", []):
                # Check if this span is a running header to filter
                if filter_running_headers and is_running_header_span(span):
                    running_headers_filtered += 1
                    continue

                span_text = span.get("text", "")
                if span_text:
                    line_text_parts.append(span_text)

            # Join spans within a line
            line_text = "".join(line_text_parts)
            if line_text.strip():  # Only add non-empty lines
                block_lines.append(line_text)

        # Skip empty blocks
        if not block_lines:
            continue

        # Get block bounding box
        block_bbox = block.get("bbox", (0, 0, 0, 0))

        # Join lines with newlines to preserve structure
        block_text = "\n".join(block_lines)

        text_block = TextBlock(
            x0=block_bbox[0],
            y0=block_bbox[1],
            x1=block_bbox[2],
            y1=block_bbox[3],
            text=block_text,
            page_num=page_num
        )
        blocks.append(text_block)

    if running_headers_filtered > 0:
        logger.debug(f"Page {page_num}: Filtered {running_headers_filtered} running headers")

    logger.debug(f"Page {page_num}: Extracted {len(blocks)} text blocks")
    return blocks


def extract_all_pages(doc: fitz.Document) -> Tuple[List[List[TextBlock]], float]:
    """Extract text blocks from all pages in document.

    Args:
        doc: PyMuPDF Document object

    Returns:
        Tuple of (pages_blocks, page_height) where pages_blocks is list of block lists
    """
    pages_blocks = []
    page_heights = []

    for page_num in range(doc.page_count):
        page = doc[page_num]
        page_heights.append(page.rect.height)

        blocks = extract_text_blocks(page, page_num)
        pages_blocks.append(blocks)

        if (page_num + 1) % config.PROGRESS_INTERVAL == 0:
            logger.info(f"Extracted {page_num + 1}/{doc.page_count} pages")

    # Use median page height (most pages should be same size)
    median_height = sorted(page_heights)[len(page_heights) // 2] if page_heights else 792.0

    logger.info(f"Extraction complete: {doc.page_count} pages, median height={median_height:.1f}")
    return pages_blocks, median_height


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text: str) -> str:
    """Normalize text by fixing whitespace and encoding issues.

    IMPORTANT: Preserves line breaks for article pattern matching!

    Args:
        text: Raw text to normalize

    Returns:
        Normalized text
    """
    if not text:
        return ""

    # Normalize line breaks first
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Fix hyphenation across lines (if enabled)
    if config.FIX_HYPHENATION:
        text = text.replace("-\n", "")
        text = text.replace("- \n", "")

    # Normalize whitespace within each line (preserve line breaks!)
    if config.NORMALIZE_WHITESPACE:
        lines = text.split("\n")
        normalized_lines = []
        for line in lines:
            # Normalize spaces within the line (but keep the line separate)
            normalized_line = " ".join(line.split())
            if normalized_line:  # Skip empty lines
                normalized_lines.append(normalized_line)
        text = "\n".join(normalized_lines)

    # Remove excessive newlines (max 2 consecutive)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")

    return text.strip()


# ============================================================
# FULL EXTRACTION PIPELINE
# ============================================================

def extract_document_text(
    pdf_path: Path,
    vintage: str,
    apply_cleaning: bool = True,
    extract_equations: bool = True
) -> Tuple[str, int, dict]:
    """Extract and clean text from NECB PDF document.

    Args:
        pdf_path: Path to PDF file
        vintage: NECB vintage year
        apply_cleaning: Whether to apply header/footer cleaning
        extract_equations: Whether to use OCR to extract equations from vector graphics

    Returns:
        Tuple of (cleaned_text, total_pages, extraction_stats)
    """
    logger.info(f"Starting extraction: {pdf_path.name} (vintage {vintage})")

    # Load PDF
    doc = load_pdf(pdf_path)
    total_pages = doc.page_count

    # Extract all text blocks
    pages_blocks, page_height = extract_all_pages(doc)

    # Apply cleaning if requested
    if apply_cleaning:
        logger.info("Applying 3-layer cleaning pipeline")
        original_pages = pages_blocks
        cleaned_pages = clean_pages(pages_blocks, page_height, vintage)

        # Calculate stats
        from .header_footer_cleaner import get_cleaning_stats
        cleaning_stats = get_cleaning_stats(original_pages, cleaned_pages)

        # Use cleaned pages
        pages_blocks = cleaned_pages
    else:
        logger.info("Skipping cleaning (apply_cleaning=False)")
        cleaning_stats = {
            "original_blocks": sum(len(page_blocks) for page_blocks in pages_blocks),
            "cleaned_blocks": sum(len(page_blocks) for page_blocks in pages_blocks),
            "removed_blocks": 0,
            "removal_rate_percent": 0,
            "pages_processed": total_pages,
        }

    # Merge pages into single text
    merged_text = merge_page_blocks(pages_blocks)

    # Normalize text
    normalized_text = normalize_text(merged_text)

    # Extract equations using OCR if enabled
    equations_extracted = 0
    targeted_equations_extracted = 0
    if extract_equations:
        try:
            from .equation_extractor import (
                enhance_extraction_with_ocr,
                extract_equations_from_targeted_pages,
                insert_equations_into_text,
            )

            # Standard equation extraction (gap detection)
            logger.info("Extracting equations via OCR...")
            enhanced_text = enhance_extraction_with_ocr(doc, normalized_text)
            equations_extracted = enhanced_text.count("[Equation:")
            if equations_extracted > 0:
                logger.info(f"Inserted {equations_extracted} equations via standard detection")
                normalized_text = enhanced_text

            # Targeted equation extraction for NECB 2020 (pages with known missing equations)
            if vintage == "2020":
                logger.info("Running targeted equation extraction for NECB 2020...")
                targeted_equations = extract_equations_from_targeted_pages(doc, vintage="2020", use_llm=True)
                if targeted_equations:
                    # Insert targeted equations into text
                    before_count = normalized_text.count("[Equation:")
                    normalized_text = insert_equations_into_text(normalized_text, targeted_equations)
                    after_count = normalized_text.count("[Equation:")
                    targeted_equations_extracted = after_count - before_count
                    if targeted_equations_extracted > 0:
                        logger.info(f"Inserted {targeted_equations_extracted} equations via targeted extraction")
                    equations_extracted = after_count

        except ImportError:
            logger.debug("Equation extractor not available, skipping OCR")
        except Exception as e:
            logger.warning(f"Equation extraction failed: {e}")

    # Close document after all processing
    doc.close()

    # Build statistics
    extraction_stats = {
        **cleaning_stats,
        "total_pages": total_pages,
        "final_text_length": len(normalized_text),
        "final_line_count": normalized_text.count("\n") + 1,
        "equations_extracted": equations_extracted,
    }

    logger.info(f"Extraction complete: {extraction_stats['final_text_length']} chars, "
                f"{extraction_stats['final_line_count']} lines, "
                f"{equations_extracted} equations")

    return normalized_text, total_pages, extraction_stats


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def extract_vintage_document(
    vintage: str,
    apply_cleaning: bool = True
) -> Tuple[str, int, dict]:
    """Extract text from NECB PDF by vintage year.

    Args:
        vintage: NECB vintage year (2020)
        apply_cleaning: Whether to apply header/footer cleaning

    Returns:
        Tuple of (cleaned_text, total_pages, extraction_stats)

    Raises:
        ValueError: If vintage is not supported
        FileNotFoundError: If PDF file doesn't exist
    """
    pdf_path = config.get_pdf_path(vintage)
    return extract_document_text(pdf_path, vintage, apply_cleaning)


def extract_page_range(
    pdf_path: Path,
    vintage: str,
    start_page: int,
    end_page: int,
    apply_cleaning: bool = True
) -> Tuple[str, int, dict]:
    """Extract text from a specific page range.

    Args:
        pdf_path: Path to PDF file
        vintage: NECB vintage year
        start_page: Starting page number (0-indexed)
        end_page: Ending page number (exclusive)
        apply_cleaning: Whether to apply header/footer cleaning

    Returns:
        Tuple of (cleaned_text, total_pages, extraction_stats)
    """
    logger.info(f"Extracting pages {start_page} to {end_page} from {pdf_path.name}")

    # Load PDF
    doc = load_pdf(pdf_path)

    # Validate page range
    if start_page < 0 or end_page > doc.page_count:
        raise ValueError(f"Invalid page range: {start_page}-{end_page} (document has {doc.page_count} pages)")

    # Extract only specified pages
    pages_blocks = []
    page_heights = []

    for page_num in range(start_page, end_page):
        page = doc[page_num]
        page_heights.append(page.rect.height)

        blocks = extract_text_blocks(page, page_num)
        pages_blocks.append(blocks)

    doc.close()

    # Get median height
    median_height = sorted(page_heights)[len(page_heights) // 2] if page_heights else 792.0

    # Apply cleaning if requested
    if apply_cleaning:
        original_pages = pages_blocks
        cleaned_pages = clean_pages(pages_blocks, median_height, vintage)

        from .header_footer_cleaner import get_cleaning_stats
        cleaning_stats = get_cleaning_stats(original_pages, cleaned_pages)

        pages_blocks = cleaned_pages
    else:
        cleaning_stats = {
            "original_blocks": sum(len(page_blocks) for page_blocks in pages_blocks),
            "cleaned_blocks": sum(len(page_blocks) for page_blocks in pages_blocks),
            "removed_blocks": 0,
            "removal_rate_percent": 0,
            "pages_processed": end_page - start_page,
        }

    # Merge and normalize
    merged_text = merge_page_blocks(pages_blocks)
    normalized_text = normalize_text(merged_text)

    # Build statistics
    extraction_stats = {
        **cleaning_stats,
        "total_pages": end_page - start_page,
        "final_text_length": len(normalized_text),
        "final_line_count": normalized_text.count("\n") + 1,
    }

    return normalized_text, end_page - start_page, extraction_stats
