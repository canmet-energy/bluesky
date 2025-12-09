"""Data models for NECB PDF parser v2"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ExtractionMethod(Enum):
    """Method used for table extraction"""

    PYMUPDF = "pymupdf"
    MARKER = "marker"
    FAILED = "failed"


@dataclass
class MarkdownTable:
    """Extracted table in Markdown format (PyMuPDF output)"""

    markdown_text: str
    estimated_rows: int
    estimated_cols: int
    confidence: float  # 0-1 quality score
    page_number: int


@dataclass
class MarkerTable:
    """Extracted table with cell-level structure (Marker output)"""

    cells: list[list[str]]  # 2D grid of cell content
    headers: list[str]
    page_number: int
    bboxes: list[list[float]] | None = None  # Bounding boxes for merged cell detection


@dataclass
class ValidationResult:
    """Result of table validation check"""

    passed: bool
    errors: list[str]
    warnings: list[str]
    confidence: float


@dataclass
class ParseResult:
    """Result of table parsing operation"""

    success: bool
    data: Any | None  # Validated Pydantic model if success
    method_used: ExtractionMethod
    llm_applied: bool
    errors: list[str]
    timing: dict[str, float]  # Stage durations (pymupdf_ms, marker_ms, llm_ms, total_ms)
    raw_extraction: str | None = None  # For debugging


@dataclass
class DocumentParseResult:
    """Result of parsing entire NECB document"""

    tables: list[ParseResult]
    success_rate: float
    total_duration: float
    method_distribution: dict[str, int]  # {"pymupdf": 80, "marker": 15, "failed": 5}
    vintage: str
