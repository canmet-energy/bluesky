# Phase 1: NECB Figure Extraction Implementation Plan

## Objective
Extract figures (images + labels + captions) from NECB PDFs with spatial relationship detection.

## Architecture

### Module Location
`src/bluesky/mcp/scrapers/necb/section_parser/` (alongside article extraction)

### Approach
- PyMuPDF for image extraction (bitmap and vector)
- Spatial coordinate matching (vertical ordering: image → label → caption)
- Regex pattern matching for figure labels
- SQLite storage in `necb_production.db`

### Target Output
- **Images:** `/workspaces/bluesky/src/bluesky/mcp/data/necb/figures/`
- **Metadata:** `necb_production.db` (new `necb_figures` table)

---

## Core Modules (5 modules)

### 1. figure_config.py
**Purpose:** Configuration and patterns

**Constants:**
- `FIGURE_OUTPUT_DIR` = `/workspaces/bluesky/src/bluesky/mcp/data/necb/figures/`
- `FIGURE_LABEL_PATTERN` = Regex for "Figure A-8.4.4.17.(2)" format
- `IMAGE_FORMATS` = Supported formats (PNG, JPEG, etc.)
- `VECTOR_DPI` = Resolution for rendering vector graphics (default: 150)
- `MAX_CAPTION_LINES` = Maximum lines to capture for caption (default: 3)

**Patterns:**
```python
# Figure label: "Figure A-8.4.4.17.(2)" or "Figure 3.2.1"
FIGURE_LABEL_PATTERN = re.compile(
    r"(?i)^figure\s+([A-Z]?-?\d+(?:\.\d+)*(?:\.\(\d+\))?)",
    re.IGNORECASE
)

# Stop patterns for caption detection
CAPTION_STOP_PATTERNS = [
    ARTICLE_PATTERN,  # Reuse from article config
    SECTION_PATTERN,
    PART_PATTERN,
    FIGURE_LABEL_PATTERN  # New figure starts
]
```

---

### 2. figure_models.py
**Purpose:** Pydantic data models

**Models:**
```python
class Figure(BaseModel):
    """A figure with image, label, and caption."""

    # Identification
    label: str  # e.g., "A-8.4.4.17.(2)"
    caption: Optional[str]  # e.g., "Fan part-load curves"
    vintage: str  # NECB year

    # Location in PDF
    page: int
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)

    # Image details
    image_path: str  # Relative path to saved image
    image_type: str  # "bitmap" or "vector"
    image_format: str  # "PNG", "JPEG", etc.

    # Metadata
    width: int  # Image width in pixels
    height: int  # Image height in pixels
    file_size: int  # Image file size in bytes

    # Database ID
    id: Optional[int] = None
    extracted_at: datetime = Field(default_factory=datetime.now)
```

**Additional Models:**
- `BitmapImage` - Raw bitmap data before saving
- `VectorDrawing` - Vector graphics bounding box
- `TextBlock` - Text with coordinates (reuse from article_extractor)
- `FigureParseResult` - Results from full document parsing

---

### 3. figure_extractor.py
**Purpose:** Image extraction using PyMuPDF

**Functions:**

**Bitmap Extraction:**
```python
def extract_bitmap_images(page: fitz.Page, page_num: int) -> List[BitmapImage]:
    """Extract bitmap images from a page.

    Uses page.get_images(full=True) and doc.extract_image(xref).
    Returns list of BitmapImage objects with coordinates.
    """

def save_bitmap_image(image: BitmapImage, output_path: Path) -> dict:
    """Save bitmap image to disk.

    Returns metadata: width, height, format, file_size.
    """
```

**Vector Extraction:**
```python
def extract_vector_drawings(page: fitz.Page, page_num: int) -> List[VectorDrawing]:
    """Detect vector graphics using page.get_drawings().

    Groups drawing elements by bounding box proximity.
    Returns list of VectorDrawing objects.
    """

def render_vector_to_image(page: fitz.Page, bbox: tuple, dpi: int = 150) -> bytes:
    """Render vector graphics region to PNG.

    Uses page.get_pixmap(clip=bbox, dpi=dpi).
    Returns PNG bytes.
    """
```

**Combined Pipeline:**
```python
def extract_all_images(doc: fitz.Document, vintage: str) -> List[tuple]:
    """Extract both bitmap and vector images from document.

    Returns list of (page_num, bbox, image_type, image_data) tuples.
    """
```

---

### 4. figure_detector.py
**Purpose:** Label and caption detection using spatial relationships

**Functions:**

**Label Detection:**
```python
def find_figure_label(
    image_bbox: tuple,
    text_blocks: List[TextBlock],
    page_height: float
) -> Optional[str]:
    """Find figure label below image.

    Algorithm:
    1. Filter text blocks where block.y0 > image_bbox[3] (below image)
    2. Sort by vertical position (y0)
    3. Find first match for FIGURE_LABEL_PATTERN
    4. Extract and normalize figure number

    Returns: Normalized label string or None
    """
```

**Caption Detection:**
```python
def find_figure_caption(
    label_block: TextBlock,
    text_blocks: List[TextBlock],
    max_lines: int = 3
) -> Optional[str]:
    """Find caption below figure label.

    Algorithm:
    1. Filter blocks where block.y0 > label_block.y1
    2. Capture next 1-3 non-blank lines
    3. Stop if new Article/Section/Part/Figure detected
    4. Join lines with space

    Returns: Caption text or None
    """
```

**Association:**
```python
def associate_images_with_metadata(
    images: List[tuple],
    text_blocks: List[TextBlock],
    page_height: float,
    vintage: str
) -> List[Figure]:
    """Associate each image with its label and caption.

    For each image:
    1. Find label using find_figure_label()
    2. Find caption using find_figure_caption()
    3. Create Figure object

    Returns: List of Figure objects
    """
```

---

### 5. figure_db.py
**Purpose:** Database operations for figures

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS necb_figures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vintage TEXT NOT NULL,
    label TEXT NOT NULL,
    caption TEXT,
    page INTEGER NOT NULL,
    bbox_x0 REAL,
    bbox_y0 REAL,
    bbox_x1 REAL,
    bbox_y1 REAL,
    image_path TEXT NOT NULL,
    image_type TEXT NOT NULL,
    image_format TEXT,
    width INTEGER,
    height INTEGER,
    file_size INTEGER,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_figure_label ON necb_figures(label, vintage);
CREATE INDEX idx_figure_page ON necb_figures(page, vintage);
```

**Functions:**
```python
def init_figures_table():
    """Initialize necb_figures table."""

def insert_figure(figure: Figure) -> int:
    """Insert single figure with metadata."""

def get_figures_by_vintage(vintage: str) -> List[Figure]:
    """Retrieve all figures for a vintage."""

def get_figure_by_label(label: str, vintage: str) -> Optional[Figure]:
    """Get figure by label."""
```

---

### 6. figure_parser.py
**Purpose:** Main orchestration pipeline

**Pipeline:**
```python
def parse_figures(pdf_path: Path, vintage: str) -> FigureParseResult:
    """Full figure extraction pipeline.

    Steps:
    1. Load PDF using PyMuPDF
    2. Extract images (bitmap + vector) from all pages
    3. Extract text blocks with coordinates (reuse from article_extractor)
    4. Associate images with labels and captions
    5. Save images to output directory
    6. Save metadata to database
    7. Return results
    """
```

**CLI Interface:**
```bash
python -m bluesky.mcp.scrapers.necb.section_parser.figure_parser --vintage 2020
python -m bluesky.mcp.scrapers.necb.section_parser.figure_parser --all-vintages
python -m bluesky.mcp.scrapers.necb.section_parser.figure_parser --stats
```

---

## Implementation Order

1. Create `figure_config.py` with patterns and constants
2. Create `figure_models.py` with Pydantic schemas
3. Implement `figure_extractor.py` for image extraction
4. Implement `figure_detector.py` for label/caption detection
5. Implement `figure_db.py` for database operations
6. Implement `figure_parser.py` as orchestrator
7. Update `__init__.py` to expose figure API
8. Create tests
9. Run on sample pages for validation
10. Run on full NECB 2020

---

## Key Algorithms

### Spatial Relationship Detection

**Challenge:** Match images with text below them

**Solution:**
```python
# For each image at bbox (x0, y0, x1, y1)
image_bottom = y1

# Find text blocks below the image
below_blocks = [
    block for block in text_blocks
    if block.y0 > image_bottom
]

# Sort by vertical position (top to bottom)
below_blocks.sort(key=lambda b: b.y0)

# First block matching figure pattern = label
for block in below_blocks:
    if FIGURE_LABEL_PATTERN.match(block.text):
        label = extract_label(block.text)
        caption = find_caption_after_label(block, below_blocks)
        break
```

### Vector Graphics Detection

**Challenge:** Detect diagrams drawn with vector elements

**Solution:**
```python
# Get all drawing paths on page
drawings = page.get_drawings()

# Group by proximity (drawings close together = one figure)
figure_groups = group_drawings_by_proximity(drawings, threshold=20)

# For each group, get bounding box
for group in figure_groups:
    bbox = get_combined_bbox(group)

    # Render to image
    pixmap = page.get_pixmap(clip=bbox, dpi=150)
    image_bytes = pixmap.tobytes("png")
```

---

## File Naming Convention

**Images saved as:**
```
/workspaces/bluesky/src/bluesky/mcp/data/necb/figures/
├── 2020/
│   ├── Figure_A-8.4.4.17.(2).png
│   ├── Figure_3.2.1.png
│   └── Figure_B-5.3.2.1.png
└── 2017/
    └── ...
```

**Naming rules:**
- Organize by vintage subfolder
- Sanitize label for filesystem (replace `/`, `:`, etc.)
- Use PNG format for all images (convert JPEG if needed)

---

## Testing Strategy

### Unit Tests
- Pattern matching for figure labels
- Caption detection with stop conditions
- Spatial filtering (blocks below image)
- Image format conversion

### Integration Tests
- Extract 5 known figures from test PDF
- Verify label, caption, and image saved correctly
- Check database entries match extracted data

### Validation
- Manual review of 10 random figures per vintage
- Verify images are complete and not clipped
- Check labels and captions are accurate

---

## Success Criteria

1. **Image Extraction**
   - All bitmap images detected and saved
   - Vector graphics rendered to PNG
   - No image corruption or quality loss

2. **Label Detection**
   - Figure labels accurately matched
   - Normalized format (e.g., "A-8.4.4.17.(2)")
   - Missing labels logged as warnings

3. **Caption Detection**
   - Captions captured for all labeled figures
   - Multi-line captions properly joined
   - Stop conditions prevent caption overflow

4. **Database Integrity**
   - All figures stored with complete metadata
   - Images accessible via stored paths
   - Queries return correct figures

---

## Dependencies

**Already Available:**
- PyMuPDF (fitz) - Image and text extraction
- Pydantic - Data validation
- SQLite3 - Database

**Reuse from Article Parser:**
- TextBlock extraction from `article_extractor.py`
- Pattern utilities from `config.py`

**No New Dependencies Required**

---

## Estimated Effort

- Module implementation: ~3-4 hours
- Testing and validation: ~1-2 hours
- Debugging and refinement: ~1-2 hours
- **Total:** ~5-8 hours

---

## Notes

- Vector graphics detection may be complex - start with bitmaps first
- Some figures may span multiple columns - use horizontal overlap detection
- Figure labels are case-insensitive in PDFs
- Caption detection must handle edge cases (tables, multi-column layouts)
- Reuse existing article extraction infrastructure where possible
