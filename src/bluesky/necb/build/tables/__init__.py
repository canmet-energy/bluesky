"""
NECB PDF Parser v2 - Hybrid Architecture

This module implements a three-stage hybrid PDF parsing pipeline:
1. PyMuPDF4LLM - Fast baseline extraction for simple tables
2. Marker - Advanced extraction for complex tables with merged cells
3. Ollama LLM - Repair and normalization to target schema

Architecture:
    PyMuPDF (fast) → validation → Marker (fallback) → LLM repair → validated output

See docs/necb/pdf-parsing-v2-implementation-plan.md for full specification.
"""

__version__ = "2.0.0-alpha"

from .config import ParserConfig
from .models import MarkdownTable, ParseResult, ValidationResult
from .pymupdf_extractor import PyMuPDFTableExtractor

# HybridNECBParser will be imported once implemented
# from .hybrid_parser import HybridNECBParser

__all__ = ["ParserConfig", "MarkdownTable", "ParseResult", "ValidationResult", "PyMuPDFTableExtractor"]
