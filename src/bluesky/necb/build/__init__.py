"""
NECB build tools for parsing PDFs into SQLite databases.

Submodules:
- tables: Table extraction and parsing
- sections: Article/clause hierarchical extraction
- figures: Figure extraction and vision enrichment
"""

from typing import Optional

# Division page boundaries by vintage (0-indexed page numbers)
# Format: {vintage: {division: (start_page, end_page)}}
DIVISION_PAGE_BOUNDARIES = {
    "2017": {
        "A": (20, 49),
        "B": (50, 311),
        "C": (312, 340),
    },
    "2020": {
        "A": (18, 47),
        "B": (48, 285),
        "C": (286, 314),
    },
}


def get_division_for_page(page_num: int, vintage: str) -> Optional[str]:
    """Determine which Division a page belongs to.

    Args:
        page_num: Page number (0-indexed)
        vintage: NECB vintage year (e.g., "2020")

    Returns:
        Division letter (A, B, C, or D) or None if page is before divisions
    """
    if vintage not in DIVISION_PAGE_BOUNDARIES:
        return None

    boundaries = DIVISION_PAGE_BOUNDARIES[vintage]

    for division, (start, end) in boundaries.items():
        if start <= page_num <= end:
            return division

    return None
