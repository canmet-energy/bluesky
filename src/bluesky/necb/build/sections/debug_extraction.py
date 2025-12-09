"""
Debug script to diagnose article extraction issues.

This script shows intermediate extraction steps to help identify where parsing fails.
"""

import logging
import sys
from pathlib import Path

# Setup logging to see everything
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(message)s"
)

from .article_extractor import extract_vintage_document, extract_page_range
from .article_detector import (
    detect_part,
    detect_section,
    detect_subsection,
    detect_article,
    detect_clause,
    parse_document_text,
)
from .config import get_pdf_path


def debug_sample_pages(vintage: str = "2020", num_pages: int = 20):
    """Extract and analyze first N pages to diagnose issues.

    Args:
        vintage: NECB vintage year
        num_pages: Number of pages to analyze
    """
    print(f"\n{'='*80}")
    print(f"DEBUG: Extracting first {num_pages} pages from NECB {vintage}")
    print(f"{'='*80}\n")

    # Get PDF path
    pdf_path = get_pdf_path(vintage)
    print(f"PDF Path: {pdf_path}")
    print(f"PDF Exists: {pdf_path.exists()}\n")

    if not pdf_path.exists():
        print(f"ERROR: PDF not found at {pdf_path}")
        return

    # Extract first N pages WITHOUT cleaning to see raw content
    print(f"\n{'='*80}")
    print("STEP 1: Raw extraction (no cleaning)")
    print(f"{'='*80}\n")

    from .article_extractor import load_pdf, extract_page_range

    raw_text, pages, stats = extract_page_range(
        pdf_path, vintage, 0, min(num_pages, 100), apply_cleaning=False
    )

    print(f"Extracted {pages} pages")
    print(f"Total characters: {len(raw_text)}")
    print(f"Total lines: {raw_text.count(chr(10))}")
    print("\nFirst 2000 characters of raw text:")
    print("-" * 80)
    print(raw_text[:2000])
    print("-" * 80)

    # Now WITH cleaning
    print(f"\n{'='*80}")
    print("STEP 2: With cleaning applied")
    print(f"{'='*80}\n")

    cleaned_text, pages, stats = extract_page_range(
        pdf_path, vintage, 0, min(num_pages, 100), apply_cleaning=True
    )

    print(f"After cleaning:")
    print(f"  Characters: {len(cleaned_text)}")
    print(f"  Lines: {cleaned_text.count(chr(10))}")
    print(f"  Removed: {stats['removed_blocks']} blocks ({stats['removal_rate_percent']:.1f}%)")
    print("\nFirst 2000 characters of cleaned text:")
    print("-" * 80)
    print(cleaned_text[:2000])
    print("-" * 80)

    # Test pattern matching on individual lines
    print(f"\n{'='*80}")
    print("STEP 3: Pattern matching on cleaned text")
    print(f"{'='*80}\n")

    lines = cleaned_text.split("\n")
    print(f"Testing patterns on {len(lines)} lines...\n")

    # Count pattern matches
    part_matches = []
    section_matches = []
    subsection_matches = []
    article_matches = []
    clause_matches = []

    for i, line in enumerate(lines[:500]):  # Check first 500 lines
        line = line.strip()
        if not line:
            continue

        if detect_part(line):
            part_matches.append((i, line))
        elif detect_section(line):
            section_matches.append((i, line))
        elif detect_subsection(line):
            subsection_matches.append((i, line))
        elif detect_article(line):
            article_matches.append((i, line))
        elif detect_clause(line):
            clause_matches.append((i, line))

    print(f"Pattern matches in first 500 lines:")
    print(f"  Parts:       {len(part_matches)}")
    print(f"  Sections:    {len(section_matches)}")
    print(f"  Subsections: {len(subsection_matches)}")
    print(f"  Articles:    {len(article_matches)}")
    print(f"  Clauses:     {len(clause_matches)}")

    if part_matches:
        print(f"\nFirst 5 Part matches:")
        for i, (line_num, text) in enumerate(part_matches[:5]):
            print(f"  Line {line_num}: {text[:80]}")

    if section_matches:
        print(f"\nFirst 5 Section matches:")
        for i, (line_num, text) in enumerate(section_matches[:5]):
            print(f"  Line {line_num}: {text[:80]}")

    if article_matches:
        print(f"\nFirst 5 Article matches:")
        for i, (line_num, text) in enumerate(article_matches[:5]):
            print(f"  Line {line_num}: {text[:80]}")
    else:
        print("\n⚠️  NO ARTICLE MATCHES FOUND")
        print("\nShowing all lines that start with digits (potential articles):")
        digit_lines = [(i, line) for i, line in enumerate(lines[:500]) if line and line[0].isdigit()]
        for line_num, text in digit_lines[:20]:
            print(f"  Line {line_num}: {text[:100]}")

    # Try full parsing
    print(f"\n{'='*80}")
    print("STEP 4: Full parsing pipeline")
    print(f"{'='*80}\n")

    articles = parse_document_text(cleaned_text, vintage)

    print(f"Parsed articles: {len(articles)}")

    if articles:
        print("\nFirst 3 articles:")
        for article in articles[:3]:
            print(f"\n  {article.article_number} - {article.title}")
            print(f"    Hierarchy: {article.hierarchy_level}")
            print(f"    Clauses: {len(article.clauses)}")
            print(f"    Text length: {len(article.full_text)}")
    else:
        print("\n⚠️  NO ARTICLES PARSED")
        print("\nThis suggests:")
        print("  1. Regex patterns don't match the PDF format")
        print("  2. Text extraction has issues")
        print("  3. Cleaning is too aggressive")
        print("\nNext steps:")
        print("  - Review the raw text sample above")
        print("  - Check if article numbers follow expected format")
        print("  - Adjust regex patterns in config.py if needed")


if __name__ == "__main__":
    vintage = sys.argv[1] if len(sys.argv) > 1 else "2020"
    num_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 20

    debug_sample_pages(vintage, num_pages)
