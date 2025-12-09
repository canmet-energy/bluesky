# NECB Table Parser

Extracts structured tabular data from NECB PDF documents using a hybrid pipeline with LLM repair.

## Process Flow

```
PDF Document
     │
     ▼
┌────────────────────────────────────────────────────────────────────┐
│ 1. SCANNING (table_scanner.py)                                     │
│    - Detect table titles using bold + centered text                │
│    - Find multi-page tables via continuation markers               │
│    - Build inventory of all tables with page locations             │
└────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────────────┐
│ 2. EXTRACTION (pymupdf_extractor.py)                               │
│    - Extract tables as Markdown using PyMuPDF4LLM                  │
│    - Fast baseline extraction for simple tables                    │
│    - Calculate confidence score for extraction quality             │
└────────────────────────────────────────────────────────────────────┘
     │
     ▼ (if confidence < threshold or complex table)
┌────────────────────────────────────────────────────────────────────┐
│ 3. FALLBACK (marker_extractor.py) [DISABLED - upstream bug]        │
│    - Advanced extraction with merged cell handling                 │
│    - Uses deep learning models for complex layouts                 │
│    - Currently disabled due to surya-ocr Issue #465                │
└────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────────────┐
│ 4. LLM REPAIR (llm_repair.py)                                      │
│    - Repair extraction errors and normalize data                   │
│    - Map to target Pydantic schema for validation                  │
│    - Supports Claude API or Ollama (local) backends                │
│    - NECB 2011 table number normalization                          │
└────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────────────┐
│ 5. CACHING (cache.py)                                              │
│    - Save raw extraction and LLM output as markdown files          │
│    - Enables database rebuilds without LLM calls                   │
│    - Enables schema iteration without re-parsing PDFs              │
└────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────────────┐
│ 6. STORAGE (db_builder.py)                                         │
│    - Save to SQLite: necb_tables, necb_table_rows tables           │
│    - Track parser metadata: method, confidence, timing             │
└────────────────────────────────────────────────────────────────────┘
```

## File Reference

| File | Purpose |
|------|---------|
| `__init__.py` | Public API: `ParserConfig`, `PyMuPDFTableExtractor`, models |
| `hybrid_parser.py` | Main orchestrator - coordinates PyMuPDF → (Marker) → LLM pipeline |
| `pymupdf_extractor.py` | Fast baseline extraction using PyMuPDF4LLM |
| `marker_extractor.py` | Advanced extraction for merged cells (currently disabled) |
| `llm_repair.py` | LLM-powered repair and schema normalization |
| `llm_backends.py` | Claude API and Ollama backend integrations |
| `schemas.py` | Pydantic schemas for each NECB table type |
| `db_builder.py` | SQLite database builder and batch processing |
| `table_scanner.py` | PDF scanner for automated table detection |
| `table_specs.py` | Table inventory definitions |
| `custom_extractors.py` | Table-specific extraction logic for problem tables |
| `cache.py` | Markdown cache manager for LLM outputs |
| `config.py` | Configuration: LLM settings, thresholds, table preferences |
| `models.py` | Data models: `MarkdownTable`, `ParseResult`, `ValidationResult` |

## Key Data Models

```python
# models.py

class MarkdownTable:
    markdown_text: str      # Raw table in MD format
    estimated_rows: int
    estimated_cols: int
    confidence: float       # 0-1 quality score
    page_number: int

class ParseResult:
    success: bool
    data: BaseModel | None  # Validated Pydantic model
    method_used: str        # "pymupdf", "marker", or "failed"
    llm_applied: bool
    errors: list[str]
    confidence: float
    raw_markdown: str       # Cached extraction
    repaired_markdown: str  # LLM-repaired output
```

## Configuration (config.py)

```python
@dataclass
class ParserConfig:
    # LLM settings
    llm_backend: str = "claude"           # "ollama" or "claude"
    llm_model: str = "qwen2.5:14b-instruct"
    llm_temperature: float = 0.0

    # Validation thresholds
    pymupdf_min_confidence: float = 0.8
    marker_fallback_enabled: bool = True  # Currently disabled upstream

    # Performance
    max_retries: int = 2
    cache_extractions: bool = True
```

## Usage

### Parse Single Table

```python
from bluesky.necb.build.tables.hybrid_parser import HybridNECBParser
from bluesky.necb.build.tables.config import ParserConfig

config = ParserConfig(llm_backend="claude")
parser = HybridNECBParser(config=config)

result = parser.parse_table(
    pdf_path="NECB-2020.pdf",
    page_num=72,
    table_number="3.2.2.2",
)
print(f"Success: {result.success}, Method: {result.method_used}")
```

### Build Database

```python
from bluesky.necb.build.tables.db_builder import NECBDatabaseBuilder

builder = NECBDatabaseBuilder(
    db_path="necb_production.db",
    verbose=True,
    llm_cache_dir="data/necb/cache",
)
stats = builder.build_vintage("2020", table_specs)
print(f"Success: {stats.successful_tables}/{stats.total_tables}")
```

### CLI Usage

```bash
# Build database for NECB 2020
python -m bluesky.necb.build tables --vintages 2020

# Preview what would be parsed (no actual parsing)
python -m bluesky.necb.build tables --dry-run --vintages 2020

# Phase 1: Parse PDFs and cache LLM outputs (no database)
python -m bluesky.necb.build tables --cache-only --vintages 2020

# Phase 2: Build database from cached outputs (no LLM calls)
python -m bluesky.necb.build tables --from-cache --vintages 2020
```

## Database Schema

```sql
CREATE TABLE necb_tables (
    id INTEGER PRIMARY KEY,
    vintage TEXT NOT NULL,
    division TEXT,
    table_number TEXT NOT NULL,
    title TEXT,
    headers TEXT NOT NULL,  -- JSON array
    page_number INTEGER,
    UNIQUE(vintage, division, table_number)
);

CREATE TABLE necb_table_rows (
    id INTEGER PRIMARY KEY,
    table_id INTEGER REFERENCES necb_tables(id),
    row_index INTEGER NOT NULL,
    row_data TEXT NOT NULL  -- JSON object
);

CREATE TABLE parser_metadata (
    id INTEGER PRIMARY KEY,
    table_id INTEGER REFERENCES necb_tables(id),
    method_used TEXT,       -- "pymupdf" or "marker"
    llm_applied BOOLEAN,
    confidence REAL,
    parse_duration_s REAL,
    errors TEXT             -- JSON array
);
```

## Cache Structure

```
{cache_dir}/
└── tables/
    └── {vintage}/
        └── {table_number}.md
```

Each cache file contains YAML front matter with metadata and the raw/repaired markdown.

## Common Modifications

**Add new table schema:**
1. Define Pydantic model in `schemas.py`
2. Register in `SCHEMA_REGISTRY`
3. Test with `HybridNECBParser.parse_table()`

**Change LLM backend:**
Edit `llm_backend` in `ParserConfig`: `"claude"` or `"ollama"`

**Enable Marker fallback:**
Set `enable_marker=True` in `HybridNECBParser` (once upstream bug is fixed)

**Add custom extractor for problem table:**
Add extraction function to `custom_extractors.py`

## Troubleshooting

**Low confidence scores:** Check if schema exists for table. LLM repair requires a matching Pydantic schema to validate output.

**Parsing failures:** Check cache files for raw extraction. LLM repair can iterate on schemas without re-parsing PDFs.

**NECB 2011 table numbers:** Parser auto-normalizes "5.3.2.8.A" → "5.3.2.8.-A" to match schema patterns.

**Marker fallback disabled:** Due to upstream surya-ocr Issue #465 (SPECIAL_TOKENS undefined). PyMuPDF + LLM repair achieves ~99% success rate for NECB 2020.
