"""
NECB Figure Extraction Module

Extracts figures (images + labels + captions) from NECB PDF documents using
spatial relationship detection.

Public API:
    - parse_figures(): Main extraction function
    - Figure, FigureParseResult: Core data models
    - Database operations via figure_db module

Example:
    from bluesky.mcp.scrapers.necb.parsers.figures import parse_figures

    result = parse_figures(vintage="2020", save_to_db=True)
    print(result.get_summary())
"""

from . import figure_config as config
from . import figure_db as db
from .figure_models import (
    Figure,
    FigureParseResult,
    BitmapImage,
    VectorDrawing,
    TextBlock
)
from .figure_parser import parse_figures

__all__ = [
    # Main API
    "parse_figures",

    # Models
    "Figure",
    "FigureParseResult",
    "BitmapImage",
    "VectorDrawing",
    "TextBlock",

    # Modules (for advanced usage)
    "config",
    "db",
]

__version__ = "1.0.0"
