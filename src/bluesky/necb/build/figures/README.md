# NECB Figure Parser

Extracts figures (images + labels + captions) from NECB PDF documents using spatial relationship detection.

## Process Flow

```
PDF Document
     │
     ▼
┌────────────────────────────────────────────────────────────────────┐
│ 1. EXTRACTION (figure_extractor.py)                                │
│    - Load PDF with PyMuPDF                                         │
│    - Extract bitmap images (PNG/JPEG embedded in PDF)              │
│    - Extract vector drawings (render paths to PNG at 150 DPI)      │
│    - Extract text blocks with coordinates                          │
└────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────────────┐
│ 2. DETECTION (figure_detector.py)                                  │
│    - Find "Figure X.Y.Z" labels using regex                        │
│    - Match labels to images using spatial proximity                │
│    - Capture caption text below figures (up to 3 lines)            │
└────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────────────┐
│ 3. CROPPING (crop_figures.py) [Optional]                           │
│    - Interactive tool for manual crop selection                    │
│    - Auto-apply saved crop coordinates from JSON                   │
│    - Stored in crop_coords/{vintage}.json                          │
└────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────────────┐
│ 4. STORAGE (figure_db.py)                                          │
│    - Save figure metadata to SQLite (necb_figures table)           │
│    - Save PNG images to data/necb/figures/{vintage}/               │
└────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────────────┐
│ 5. ENRICHMENT (vision_enrichment.py) [Optional]                    │
│    - Generate AI descriptions using Claude Vision API              │
│    - Cache results as markdown files                               │
│    - Save ai_description to database                               │
└────────────────────────────────────────────────────────────────────┘
```

## File Reference

| File | Purpose |
|------|---------|
| `__init__.py` | Public API: `parse_figures()`, models |
| `figure_parser.py` | Main orchestrator - coordinates entire pipeline |
| `figure_extractor.py` | PDF extraction: bitmaps, vectors, text blocks |
| `figure_detector.py` | Label detection, caption capture, spatial matching |
| `figure_models.py` | Pydantic models: `Figure`, `BitmapImage`, `VectorDrawing`, `TextBlock` |
| `figure_config.py` | Configuration: paths, regex patterns, thresholds |
| `figure_db.py` | SQLite operations: insert, query, delete figures |
| `crop_figures.py` | Interactive cropping tool with matplotlib |
| `cache.py` | Cache manager for Vision API outputs |
| `vision_enrichment.py` | Claude Vision API integration for AI descriptions |

## Key Data Models

```python
# figure_models.py

class Figure:
    label: str           # "A-8.4.4.17.(2)"
    caption: str         # Text below figure
    vintage: str         # "2011", "2015", "2017", "2020"
    division: str        # "A", "B", "C", "D"
    page: int            # 0-indexed page number
    bbox: tuple          # (x0, y0, x1, y1) bounding box
    image_path: str      # Relative path to PNG
    image_type: str      # "bitmap" or "vector"
    width: int           # Pixels
    height: int          # Pixels

class BitmapImage:
    # Embedded raster image from PDF
    page: int
    xref: int            # PyMuPDF cross-reference
    bbox: tuple
    image_data: bytes    # Raw image bytes

class VectorDrawing:
    # Rendered vector graphics region
    page: int
    bbox: tuple
    element_count: int   # Number of drawing elements
```

## Configuration (figure_config.py)

```python
# Spatial detection
VERTICAL_TOLERANCE = 5          # Points below image for label
FIGURE_PROXIMITY_THRESHOLD = 200 # Points around label to search

# Image filtering
MIN_IMAGE_WIDTH = 50            # Skip icons/bullets
MIN_IMAGE_HEIGHT = 50

# Vector rendering
VECTOR_DPI = 150                # Quality vs file size balance

# Caption extraction
MAX_CAPTION_LINES = 3

# Figure label regex
FIGURE_LABEL_PATTERN = r"(?i)^\s*figure\s+([A-Z]?-?\d+(?:\.\d+)*...)"
```

## Usage

### Basic Extraction

```python
from bluesky.necb.build.figures import parse_figures

result = parse_figures(vintage="2020", save_to_db=True)
print(f"Extracted {result.total_figures} figures")
```

### Query Database

```python
from bluesky.necb.build.figures import db

figure = db.get_figure_by_label("A-8.4.4.17.(2)", "2020")
figures = db.get_figures_by_vintage("2020")
```

### Vision Enrichment

```python
from bluesky.necb.build.figures.vision_enrichment import VisionEnricher

enricher = VisionEnricher(
    cache_dir=Path("data/necb/cache/figures"),  # Vision API output cache
    section_cache_dir=Path("data/necb/cache"),   # Section cache for article context
    db_path=Path("data/necb/necb_production.db") # For fetching figure images
)
result = enricher.enrich_figure(figure, vintage="2020")
print(result.ai_description)
```

**Note:** The enricher reads article context from section cache files (JSON), not the database. This allows vision enrichment to run independently of whether sections have been saved to the database.

## Database Schema

```sql
CREATE TABLE necb_figures (
    id INTEGER PRIMARY KEY,
    vintage TEXT NOT NULL,
    division TEXT,
    label TEXT NOT NULL,
    caption TEXT,
    page INTEGER NOT NULL,
    bbox_x0 REAL, bbox_y0 REAL, bbox_x1 REAL, bbox_y1 REAL,
    image_path TEXT NOT NULL,
    image_type TEXT NOT NULL,  -- 'bitmap' or 'vector'
    image_format TEXT,
    width INTEGER,
    height INTEGER,
    file_size INTEGER,
    ai_description TEXT,       -- From vision enrichment
    extracted_at TIMESTAMP
);
```

## Output Structure

```
data/necb/
├── figures/
│   └── {vintage}/
│       ├── Figure_A-8.4.4.17.2.png
│       └── ...
└── cache/
    └── figures/
        └── {vintage}/
            └── A-8.4.4.17.2.md  # Vision API cache
```

## Spatial Detection Algorithm

1. Find "Figure X.Y.Z" text pattern on page
2. Search within 200 points (FIGURE_PROXIMITY_THRESHOLD) for images
3. Check both WITHIN image bbox (embedded labels) and BELOW image
4. Prefer content directly below label
5. Capture caption text until stop pattern (new article/figure/table)

## Common Modifications

**Add new figure label format:**
Edit `FIGURE_LABEL_PATTERN` in `figure_config.py`

**Change crop coordinates:**
Edit JSON files in `crop_coords/` directory

**Adjust detection sensitivity:**
Modify `VERTICAL_TOLERANCE` and `FIGURE_PROXIMITY_THRESHOLD`

**Change Vision API model:**
Update `VisionEnrichmentConfig.model` in `vision_enrichment.py`
