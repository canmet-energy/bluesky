"""
Configuration constants and patterns for NECB figure extraction.

Defines figure label patterns, output paths, and extraction settings.
"""

import re
from pathlib import Path
from typing import Pattern, List

from bluesky.necb import DB_PATH, PDF_DIR, FIGURES_DIR

# ============================================================
# PATH CONFIGURATION
# ============================================================

# Figure output directory (uses package-level constant)
FIGURE_OUTPUT_DIR = FIGURES_DIR

# Database path (uses package-level constant)
DATABASE_PATH = DB_PATH

# NECB PDF paths by vintage
PDF_PATHS = {
    "2011": PDF_DIR / "NECB-2011.pdf",
    "2015": PDF_DIR / "NECB-2015.pdf",
    "2017": PDF_DIR / "NECB-2017.pdf",
    "2020": PDF_DIR / "NECB-2020.pdf",
}

# Crop coordinates directory (stored with parser code, not with data)
CROP_COORDS_DIR = Path(__file__).parent / "crop_coords"

# Crop coordinates paths by vintage
CROP_COORDS_PATHS = {
    "2011": CROP_COORDS_DIR / "crop_coordinates_2011.json",
    "2015": CROP_COORDS_DIR / "crop_coordinates_2015.json",
    "2017": CROP_COORDS_DIR / "crop_coordinates_2017.json",
    "2020": CROP_COORDS_DIR / "crop_coordinates_2020.json",
}

# ============================================================
# FIGURE EXTRACTION SETTINGS
# ============================================================

# Vector graphics rendering DPI
VECTOR_DPI = 150  # 150 DPI is good balance between quality and file size

# Supported image formats
SUPPORTED_IMAGE_FORMATS = ["png", "jpeg", "jpg", "bmp", "tiff"]

# Maximum caption lines to capture
MAX_CAPTION_LINES = 3

# Minimum image dimensions (to filter out icons, bullets, etc.)
MIN_IMAGE_WIDTH = 50  # pixels
MIN_IMAGE_HEIGHT = 50  # pixels

# Spatial tolerance for "below" detection (in points)
# Text must be this many points below image to be considered caption/label
VERTICAL_TOLERANCE = 5

# Proximity threshold for label-guided figure region extraction (in points)
# Drawing paths within this distance of a figure label are considered part of that figure
FIGURE_PROXIMITY_THRESHOLD = 200  # ~2.8 inches at 72 DPI

# ============================================================
# REGEX PATTERNS
# ============================================================

# Figure label pattern: "Figure A-8.4.4.17.(2)" or "Figure 3.2.1"
# Captures various formats:
#   - Figure A-8.4.4.17.(2)
#   - Figure A-4.1.1.3.(1)-A  (with letter suffix after parenthetical)
#   - Figure A-4.1.1.3.(1)-B  (with letter suffix after parenthetical)
#   - Figure A-4.2.2.3.-A     (with .-letter suffix)
#   - Figure A-4.2.2.3.-B     (with .-letter suffix)
#   - Figure B-3.2.7.1.
#   - Figure 5.3.1.
#   - Figure A-1
FIGURE_LABEL_PATTERN = re.compile(
    r"(?i)^\s*figure\s+([A-Z]?-?\d+(?:\.\d+)*(?:\.\(\d+\))?(?:\.-[A-Z]|-[A-Z])?\.?)",
    re.IGNORECASE
)

# Stop patterns for caption detection (imported from section_parser)
# These indicate the caption has ended
STOP_PATTERNS_TEXT = [
    r"^\d+\.\d+\.\d+\.\d+",  # Article pattern (e.g., 3.1.1.1)
    r"^Section\s+\d+\.\d+",  # Section pattern
    r"^Part\s+\d+",  # Part pattern
    r"(?i)^\s*figure\s+",  # New figure starts
    r"^Table\s+",  # Table starts
    r"^\s*$",  # Blank line (cautious stop)
]

# Compile stop patterns
CAPTION_STOP_PATTERNS: List[Pattern] = [
    re.compile(pattern) for pattern in STOP_PATTERNS_TEXT
]

# ============================================================
# FILENAME SANITIZATION
# ============================================================

# Characters to remove/replace in filenames
FILENAME_REPLACEMENTS = {
    "/": "_",
    "\\": "_",
    ":": "-",
    "*": "_",
    "?": "_",
    '"': "_",
    "<": "_",
    ">": "_",
    "|": "_",
    " ": "_",
    "(": "",
    ")": "",
}

# ============================================================
# TABLE NAMES
# ============================================================

TABLE_FIGURES = "necb_figures"

# ============================================================
# LOGGING CONFIGURATION
# ============================================================

LOG_LEVEL = "INFO"
PROGRESS_INTERVAL = 10  # Log progress every N pages

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def get_pdf_path(vintage: str) -> Path:
    """Get the PDF path for a specific vintage.

    Args:
        vintage: NECB vintage year (2011, 2015, 2017, 2020)

    Returns:
        Path to the PDF file

    Raises:
        ValueError: If vintage is not supported
        FileNotFoundError: If PDF file doesn't exist
    """
    if vintage not in PDF_PATHS:
        raise ValueError(
            f"Unsupported vintage: {vintage}. Must be one of {list(PDF_PATHS.keys())}"
        )

    path = PDF_PATHS[vintage]
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    return path


def sanitize_filename(label: str) -> str:
    """Sanitize figure label for use as filename.

    Args:
        label: Figure label (e.g., "A-8.4.4.17.(2)")

    Returns:
        Sanitized filename safe for all filesystems
    """
    filename = label

    # Apply replacements
    for old, new in FILENAME_REPLACEMENTS.items():
        filename = filename.replace(old, new)

    # Remove leading/trailing underscores and dots
    filename = filename.strip("_.")

    return filename


def get_figure_output_path(label: str, vintage: str, extension: str = "png") -> Path:
    """Get output path for a figure image.

    Args:
        label: Figure label (e.g., "A-8.4.4.17.(2)")
        vintage: NECB vintage year
        extension: Image file extension (default: png)

    Returns:
        Full path to save the figure
    """
    # Create vintage subdirectory
    vintage_dir = FIGURE_OUTPUT_DIR / vintage
    vintage_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize label for filename
    safe_label = sanitize_filename(label)

    # Construct filename
    filename = f"Figure_{safe_label}.{extension}"

    return vintage_dir / filename


def is_valid_vintage(vintage: str) -> bool:
    """Check if a vintage is supported.

    Args:
        vintage: NECB vintage year to check

    Returns:
        True if vintage is supported, False otherwise
    """
    return vintage in PDF_PATHS


def get_crop_coords_path(vintage: str) -> Path:
    """Get the crop coordinates path for a specific vintage.

    Args:
        vintage: NECB vintage year (2011, 2015, 2017, 2020)

    Returns:
        Path to the crop_coordinates_{vintage}.json file

    Raises:
        ValueError: If vintage is not supported
    """
    if vintage not in CROP_COORDS_PATHS:
        raise ValueError(
            f"Unsupported vintage: {vintage}. Must be one of {list(CROP_COORDS_PATHS.keys())}"
        )

    path = CROP_COORDS_PATHS[vintage]

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    return path
