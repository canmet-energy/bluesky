"""
NECB (National Energy Code of Canada for Buildings) package.

This package provides:
- MCP server for querying NECB documentation
- Build tools for parsing NECB PDFs into SQLite databases
"""

from pathlib import Path

# Package paths
PACKAGE_DIR = Path(__file__).parent
DATA_DIR = PACKAGE_DIR / "data"
DB_PATH = DATA_DIR / "necb_production.db"
CHROMA_PATH = DATA_DIR / "chroma"

# Build-time paths (at project root, not shipped)
PROJECT_ROOT = PACKAGE_DIR.parent.parent.parent
BUILD_DATA_DIR = PROJECT_ROOT / "data" / "necb"
PDF_DIR = BUILD_DATA_DIR / "pdfs"
FIGURES_DIR = BUILD_DATA_DIR / "figures"
LLM_CACHE_DIR = BUILD_DATA_DIR / "cache" / "tables"

__all__ = [
    "PACKAGE_DIR",
    "DATA_DIR",
    "DB_PATH",
    "CHROMA_PATH",
    "PDF_DIR",
    "FIGURES_DIR",
    "LLM_CACHE_DIR",
]
