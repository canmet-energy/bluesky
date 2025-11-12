"""Integration tests for Marker table extraction on NECB PDFs

Tests advanced extraction on complex tables with merged cells.
"""

import pytest
from pathlib import Path

from bluesky.mcp.scrapers.necb.parser_v2.marker_extractor import MarkerTableExtractor
from bluesky.mcp.scrapers.necb.parser_v2.models import MarkerTable


# NECB PDF paths
NECB_2011_PATH = Path("/workspaces/bluesky/src/bluesky/mcp/scrapers/necb/pdfs/NECB-2011.pdf")
NECB_2020_PATH = Path("/workspaces/bluesky/src/bluesky/mcp/scrapers/necb/pdfs/NECB-2020.pdf")


@pytest.mark.skipif(not NECB_2011_PATH.exists(), reason="NECB 2011 PDF not available")
def test_marker_extractor_necb_2011_table_322():
    """Test Marker extraction of Table 3.2.2.2 from NECB 2011 (page 51)

    Expected structure:
    - Headers: Building Assembly | Zone 4 | Zone 5 | Zone 6 | Zone 7A | Zone 7B | Zone 8
    - Data rows: Walls, Roofs, Floors (3 rows)
    - Total: 4 rows (1 header + 3 data)
    """
    extractor = MarkerTableExtractor(use_gpu=False, verbose=True)

    # Page 51 (0-indexed = 50)
    tables = extractor.extract_tables_from_page(NECB_2011_PATH, page_num=50)

    # Should find at least one table
    assert len(tables) > 0, "Should extract at least one table"

    # First table should be 3.2.2.2
    table = tables[0]
    assert isinstance(table, MarkerTable)
    assert table.page_number == 50

    # Check structure
    assert len(table.cells) >= 4, f"Expected at least 4 rows, got {len(table.cells)}"
    assert len(table.headers) >= 6, f"Expected at least 6 columns, got {len(table.headers)}"

    # Normalize and verify
    normalized = extractor.normalize_structure(table)
    assert len(normalized.cells) >= 4, "Normalized table should have at least 4 rows"

    print(f"\n✅ NECB 2011 Table 3.2.2.2:")
    print(f"   Rows: {len(normalized.cells)}, Columns: {len(normalized.headers)}")
    print(f"   Headers: {normalized.headers[:3]}...")
    print(f"   First data row: {normalized.cells[1][:2] if len(normalized.cells) > 1 else 'N/A'}...")


@pytest.mark.skipif(not NECB_2020_PATH.exists(), reason="NECB 2020 PDF not available")
def test_marker_extractor_necb_2020_table_322():
    """Test Marker extraction of Table 3.2.2.2 from NECB 2020 (page 73)

    This is the complex table that PyMuPDF struggled with.

    Expected structure:
    - Headers: Building Assembly | Zone 4 | Zone 5 | Zone 6 | Zone 7A | Zone 7B | Zone 8
    - Data rows: Walls, Roofs, Floors (3 rows)
    - Total: 4 rows (1 header + 3 data)

    Note: PyMuPDF extracted 5 rows (likely split merged header cells).
    Marker should handle merged cells better.
    """
    # Enable caching to save 79 min on future runs!
    cache_dir = Path("/tmp/marker_cache")
    extractor = MarkerTableExtractor(use_gpu=False, verbose=True, cache_dir=cache_dir)

    # Page 73 (0-indexed = 72)
    tables = extractor.extract_tables_from_page(NECB_2020_PATH, page_num=72)

    # Should find at least one table
    assert len(tables) > 0, "Should extract at least one table"

    # First table should be 3.2.2.2
    table = tables[0]
    assert isinstance(table, MarkerTable)
    assert table.page_number == 72

    # Check structure
    assert len(table.cells) >= 4, f"Expected at least 4 rows, got {len(table.cells)}"

    # Normalize structure
    normalized = extractor.normalize_structure(table)

    print(f"\n✅ NECB 2020 Table 3.2.2.2:")
    print(f"   Rows: {len(normalized.cells)}, Columns: {len(normalized.headers)}")
    print(f"   Headers: {normalized.headers}")

    # Print first few data rows
    for i, row in enumerate(normalized.cells[1:4], 1):
        print(f"   Row {i}: {row[:2]}...")

    # Detect merged cells
    merged = extractor.detect_merged_cells(table)
    if merged:
        print(f"   Merged cells detected: {len(merged)} regions")


@pytest.mark.skipif(not NECB_2020_PATH.exists(), reason="NECB 2020 PDF not available")
def test_marker_merged_cell_detection():
    """Test Marker's merged cell detection on complex NECB 2020 tables"""
    extractor = MarkerTableExtractor(use_gpu=False, verbose=True)

    # Page 73 - Table 3.2.2.2 has merged header cells
    tables = extractor.extract_tables_from_page(NECB_2020_PATH, page_num=72)

    assert len(tables) > 0, "Should extract at least one table"

    table = tables[0]
    merged_regions = extractor.detect_merged_cells(table)

    print(f"\n✅ Merged cell detection:")
    print(f"   Found {len(merged_regions)} merged regions")
    for region in merged_regions[:5]:  # Show first 5
        row, col, row_span, col_span = region
        print(f"   Region: row={row}, col={col}, row_span={row_span}, col_span={col_span}")


def test_marker_extractor_initialization():
    """Test Marker extractor initialization with GPU detection"""
    # Test CPU mode
    extractor_cpu = MarkerTableExtractor(use_gpu=False, verbose=True)
    assert extractor_cpu.device == "cpu"
    assert extractor_cpu._converter is None  # Lazy loading
    assert extractor_cpu._models is None

    # Test GPU mode (will fall back to CPU if not available)
    extractor_gpu = MarkerTableExtractor(use_gpu=True, verbose=True)
    assert extractor_gpu.device in ["cuda", "cpu"]

    print(f"\n✅ Marker extractor initialized:")
    print(f"   CPU mode: {extractor_cpu.device}")
    print(f"   GPU mode: {extractor_gpu.device}")
