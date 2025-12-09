"""
Pydantic data models for NECB figure extraction.

Defines validated data structures for figures, images, and extraction results.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List

from pydantic import BaseModel, Field, field_validator


# ============================================================
# RAW IMAGE MODELS (Before Processing)
# ============================================================

class BitmapImage(BaseModel):
    """A raw bitmap image extracted from PDF."""

    page: int = Field(..., description="Page number (0-indexed)")
    index: int = Field(..., description="Image index on page")
    xref: int = Field(..., description="PyMuPDF cross-reference number")
    bbox: Tuple[float, float, float, float] = Field(..., description="Bounding box (x0, y0, x1, y1)")

    # Image properties
    width: int = Field(..., description="Image width in pixels")
    height: int = Field(..., description="Image height in pixels")
    colorspace: Optional[str] = Field(None, description="Color space (e.g., 'DeviceRGB')")
    bpc: Optional[int] = Field(None, description="Bits per component")

    # Raw data
    image_data: Optional[bytes] = Field(None, description="Raw image bytes")
    ext: str = Field(..., description="Image format extension (png, jpeg, etc.)")

    class Config:
        arbitrary_types_allowed = True  # Allow bytes


class VectorDrawing(BaseModel):
    """A vector graphic region detected in PDF."""

    page: int = Field(..., description="Page number (0-indexed)")
    bbox: Tuple[float, float, float, float] = Field(..., description="Bounding box (x0, y0, x1, y1)")
    element_count: int = Field(..., description="Number of drawing elements in region")

    # Properties
    width: float = Field(..., description="Width in points")
    height: float = Field(..., description="Height in points")


# ============================================================
# TEXT BLOCK MODEL (Reused from article parser logic)
# ============================================================

class TextBlock(BaseModel):
    """A text block with coordinates from PyMuPDF."""

    page: int = Field(..., description="Page number (0-indexed)")
    x0: float = Field(..., description="Left x-coordinate")
    y0: float = Field(..., description="Top y-coordinate")
    x1: float = Field(..., description="Right x-coordinate")
    y1: float = Field(..., description="Bottom y-coordinate")
    text: str = Field(..., description="Block text content")

    def is_below(self, y_position: float, tolerance: float = 0) -> bool:
        """Check if this block is below a given y-position.

        Args:
            y_position: Y-coordinate to compare against
            tolerance: Tolerance in points (default: 0)

        Returns:
            True if block is below the position
        """
        return self.y0 >= (y_position - tolerance)

    def __repr__(self) -> str:
        display_text = self.text.strip().replace('\n', '\\n')
        return f"TextBlock(page={self.page}, y0={self.y0:.1f}, text='{display_text[:50]}...')"


# ============================================================
# FIGURE MODEL (Final Output)
# ============================================================

class Figure(BaseModel):
    """A complete figure with image, label, and caption."""

    # Identification
    label: str = Field(..., description="Figure label (e.g., 'A-8.4.4.17.(2)')")
    caption: Optional[str] = Field(None, description="Figure caption text")
    vintage: str = Field(..., description="NECB vintage year (2011, 2015, 2017, 2020)")
    division: Optional[str] = Field(None, description="Division (A, B, C, or D)")

    # Location in PDF
    page: int = Field(..., description="Page number (0-indexed)")
    bbox: Tuple[float, float, float, float] = Field(..., description="Bounding box (x0, y0, x1, y1)")

    # Image details
    image_path: str = Field(..., description="Relative path to saved image")
    image_type: str = Field(..., description="Image type: 'bitmap' or 'vector'")
    image_format: str = Field(default="png", description="Image format (png, jpeg, etc.)")

    # Image metadata
    width: int = Field(..., description="Image width in pixels")
    height: int = Field(..., description="Image height in pixels")
    file_size: Optional[int] = Field(None, description="Image file size in bytes")

    # Database metadata
    id: Optional[int] = Field(None, description="Database primary key")
    extracted_at: datetime = Field(default_factory=datetime.now, description="Extraction timestamp")

    @field_validator("vintage")
    @classmethod
    def validate_vintage(cls, v: str) -> str:
        """Validate vintage year."""
        valid_vintages = ["2011", "2015", "2017", "2020"]
        if v not in valid_vintages:
            raise ValueError(f"Invalid vintage: {v}. Must be one of {valid_vintages}")
        return v

    @field_validator("image_type")
    @classmethod
    def validate_image_type(cls, v: str) -> str:
        """Validate image type."""
        valid_types = ["bitmap", "vector"]
        if v not in valid_types:
            raise ValueError(f"Invalid image type: {v}. Must be one of {valid_types}")
        return v

    def to_dict(self) -> dict:
        """Convert figure to dictionary.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "id": self.id,
            "label": self.label,
            "caption": self.caption,
            "vintage": self.vintage,
            "division": self.division,
            "page": self.page,
            "bbox": list(self.bbox),
            "image_path": self.image_path,
            "image_type": self.image_type,
            "image_format": self.image_format,
            "width": self.width,
            "height": self.height,
            "file_size": self.file_size,
            "extracted_at": self.extracted_at.isoformat(),
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert figure to JSON string.

        Args:
            indent: JSON indentation level

        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def get_absolute_path(self, base_path: Path) -> Path:
        """Get absolute path to image file.

        Args:
            base_path: Base directory path

        Returns:
            Absolute path to image
        """
        return base_path / self.image_path


# ============================================================
# PARSING RESULT MODELS
# ============================================================

class FigureParseResult(BaseModel):
    """Result of parsing figures from a PDF document."""

    vintage: str = Field(..., description="NECB vintage year")
    total_pages: int = Field(..., description="Total pages processed")
    total_figures: int = Field(..., description="Total figures extracted")
    total_bitmaps: int = Field(0, description="Total bitmap images")
    total_vectors: int = Field(0, description="Total vector graphics")

    figures: List[Figure] = Field(default_factory=list, description="All extracted figures")
    errors: List[str] = Field(default_factory=list, description="Parsing errors encountered")
    warnings: List[str] = Field(default_factory=list, description="Parsing warnings")

    processing_time_seconds: Optional[float] = Field(None, description="Total processing time")
    success: bool = Field(True, description="Whether parsing succeeded overall")

    def get_summary(self) -> str:
        """Get a human-readable summary of the parsing result.

        Returns:
            Formatted summary string
        """
        summary_lines = [
            f"NECB {self.vintage} Figure Extraction Result",
            f"{'=' * 50}",
            f"Total Pages: {self.total_pages}",
            f"Total Figures: {self.total_figures}",
            f"  Bitmaps: {self.total_bitmaps}",
            f"  Vectors: {self.total_vectors}",
            f"Errors: {len(self.errors)}",
            f"Warnings: {len(self.warnings)}",
            f"Success: {self.success}",
        ]

        if self.processing_time_seconds:
            summary_lines.append(f"Processing Time: {self.processing_time_seconds:.2f}s")

        if self.errors:
            summary_lines.append(f"\nErrors:")
            for error in self.errors[:5]:  # Show first 5 errors
                summary_lines.append(f"  - {error}")
            if len(self.errors) > 5:
                summary_lines.append(f"  ... and {len(self.errors) - 5} more")

        if self.warnings:
            summary_lines.append(f"\nWarnings:")
            for warning in self.warnings[:5]:  # Show first 5 warnings
                summary_lines.append(f"  - {warning}")
            if len(self.warnings) > 5:
                summary_lines.append(f"  ... and {len(self.warnings) - 5} more")

        return "\n".join(summary_lines)

    def get_figures_by_label(self, label: str) -> Optional[Figure]:
        """Get figure by label.

        Args:
            label: Figure label to search for

        Returns:
            Figure object if found, None otherwise
        """
        for figure in self.figures:
            if figure.label == label:
                return figure
        return None

    def get_figures_by_page(self, page: int) -> List[Figure]:
        """Get all figures on a specific page.

        Args:
            page: Page number (0-indexed)

        Returns:
            List of Figure objects on that page
        """
        return [fig for fig in self.figures if fig.page == page]
