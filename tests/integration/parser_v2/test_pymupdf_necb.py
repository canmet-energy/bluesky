"""Integration tests for PyMuPDF extractor on real NECB PDFs"""

from pathlib import Path

import pytest

from bluesky.mcp.scrapers.necb.parser_v2.pymupdf_extractor import PyMuPDFTableExtractor


# NECB PDF locations
NECB_PDF_DIR = Path(__file__).parent.parent.parent.parent / "src/bluesky/mcp/scrapers/necb/pdfs"
NECB_2011_PDF = NECB_PDF_DIR / "NECB-2011.pdf"
NECB_2020_PDF = NECB_PDF_DIR / "NECB-2020.pdf"


@pytest.mark.integration
def test_pymupdf_extractor_necb_2011_table_322():
    """Test extracting Table 3.2.2.2 from NECB 2011 (page 51)"""
    if not NECB_2011_PDF.exists():
        pytest.skip(f"NECB 2011 PDF not found: {NECB_2011_PDF}")

    extractor = PyMuPDFTableExtractor(verbose=True)

    # NECB 2011 Table 3.2.2.2 is on page 51 (0-indexed: 50)
    tables = extractor.extract_tables_from_page(NECB_2011_PDF, page_num=50)

    print(f"\nFound {len(tables)} tables on page 51")
    for i, table in enumerate(tables, 1):
        print(f"\nTable {i}:")
        print(f"  Rows: {table.estimated_rows}")
        print(f"  Columns: {table.estimated_cols}")
        print(f"  Confidence: {table.confidence:.2f}")
        print(f"  Preview:\n{table.markdown_text[:200]}...")

    # Validate we found at least one table
    assert len(tables) > 0, "Should find at least one table on page 51"

    # Find the envelope table (should have 3 rows: Walls, Roofs, Floors)
    # and 7 columns (one for assembly type + 6 HDD zones)
    envelope_tables = [
        t for t in tables
        if t.estimated_rows >= 2 and t.estimated_cols >= 6
    ]

    assert len(envelope_tables) > 0, "Should find envelope requirements table"

    # Validate the largest table (likely Table 3.2.2.2)
    main_table = max(tables, key=lambda t: t.estimated_rows * t.estimated_cols)
    print(f"\nMain table:")
    print(f"  Rows: {main_table.estimated_rows}")
    print(f"  Columns: {main_table.estimated_cols}")

    # Validation
    validation = extractor.validate_extraction(
        main_table,
        min_rows=2,  # At least 2 data rows (header + data)
        min_cols=6,  # At least 6 columns
        min_confidence=0.5,  # Lower threshold for first test
    )

    print(f"\nValidation:")
    print(f"  Passed: {validation.passed}")
    print(f"  Errors: {validation.errors}")
    print(f"  Warnings: {validation.warnings}")

    # Should pass basic validation
    assert validation.passed or len(validation.errors) <= 1, \
        f"Validation failed: {validation.errors}"


@pytest.mark.integration
def test_pymupdf_extractor_necb_2020_table_322():
    """Test extracting Table 3.2.2.2 from NECB 2020 (page 73)"""
    if not NECB_2020_PDF.exists():
        pytest.skip(f"NECB 2020 PDF not found: {NECB_2020_PDF}")

    extractor = PyMuPDFTableExtractor(verbose=True)

    # NECB 2020 Table 3.2.2.2 is on page 73 (0-indexed: 72)
    tables = extractor.extract_tables_from_page(NECB_2020_PDF, page_num=72)

    print(f"\nFound {len(tables)} tables on page 73")
    for i, table in enumerate(tables, 1):
        print(f"\nTable {i}:")
        print(f"  Rows: {table.estimated_rows}")
        print(f"  Columns: {table.estimated_cols}")
        print(f"  Confidence: {table.confidence:.2f}")
        print(f"  Preview:\n{table.markdown_text[:200]}...")

    # NECB 2020 is more complex, so we may need Marker fallback
    # But PyMuPDF should still find *something*
    assert len(tables) > 0, "Should find at least one table on page 73"


@pytest.mark.integration
def test_pymupdf_validation():
    """Test validation logic on a simple table"""
    from bluesky.mcp.scrapers.necb.parser_v2.models import MarkdownTable

    # Create a simple valid table
    valid_table = MarkdownTable(
        markdown_text="""| Assembly | Zone 4 | Zone 5 | Zone 6 |
|----------|--------|--------|--------|
| Walls    | 0.315  | 0.278  | 0.247  |
| Roofs    | 0.227  | 0.183  | 0.162  |
| Floors   | 0.227  | 0.183  | 0.162  |""",
        estimated_rows=3,
        estimated_cols=4,
        confidence=0.95,
        page_number=50,
    )

    extractor = PyMuPDFTableExtractor()
    result = extractor.validate_extraction(valid_table, min_rows=3, min_cols=4)

    assert result.passed, f"Valid table should pass validation: {result.errors}"
    assert len(result.errors) == 0

    # Create an invalid table (too few rows)
    invalid_table = MarkdownTable(
        markdown_text="| A | B |\n|---|---|",
        estimated_rows=0,
        estimated_cols=2,
        confidence=0.3,
        page_number=1,
    )

    result = extractor.validate_extraction(invalid_table, min_rows=3, min_cols=2)

    assert not result.passed, "Invalid table should fail validation"
    assert len(result.errors) > 0
    print(f"Expected errors: {result.errors}")
