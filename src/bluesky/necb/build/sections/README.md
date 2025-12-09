# NECB Section Parser

Extracts hierarchical article structure from NECB PDF documents using PyMuPDF and regex patterns.

## Process Flow

```
PDF Document
     │
     ▼
┌────────────────────────────────────────────────────────────────────┐
│ 1. EXTRACTION (article_extractor.py)                               │
│    - Load PDF with PyMuPDF                                         │
│    - Extract text blocks with coordinates                          │
│    - Filter running headers (italic font at y < 50pt)              │
│    - Extract equations via LLM vision (if ANTHROPIC_API_KEY set)   │
└────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────────────┐
│ 2. CLEANING (header_footer_cleaner.py)                             │
│    - Remove page numbers, copyright notices, NRC headers           │
│    - Filter "Division X" running headers by position               │
│    - Preserve article content regardless of page position          │
└────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────────────┐
│ 3. DETECTION (article_detector.py)                                 │
│    - State machine parses cleaned text line-by-line                │
│    - Detect hierarchy: Division → Part → Section → Article         │
│    - Parse sentences (1), 2), 3)), clauses (a), b)), subclauses    │
│    - Build full NECB references like "3.5.2.1.(2)(a)(i)"           │
└────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────────────┐
│ 4. CACHING (cache.py) [Optional]                                   │
│    - Save articles as JSON files for review                        │
│    - Structure: {cache_dir}/sections/{vintage}/{division}/{num}.json│
│    - Enables database rebuilds without re-parsing PDFs             │
└────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────────────┐
│ 5. STORAGE (article_db.py)                                         │
│    - Save to SQLite: necb_articles, necb_sentences tables          │
│    - Nested clauses stored as JSON in sentences table              │
└────────────────────────────────────────────────────────────────────┘
```

## NECB Hierarchy

```
Division (A, B, C, D)
└── Part (3)
    └── Section (3.5)
        └── Subsection (3.5.2)
            └── Article (3.5.2.1)
                └── Sentence (3.5.2.1.(1))
                    └── Clause (3.5.2.1.(1)(a))
                        └── Subclause (3.5.2.1.(1)(a)(i))
```

Reference format: `3.5.2.1.(2)(a)(i)` = Part 3, Section 5, Subsection 2, Article 1, Sentence 2, Clause a, Subclause i

## File Reference

| File | Purpose |
|------|---------|
| `__init__.py` | Public API: `parse_pdf()`, `parse_vintage()`, models |
| `article_parser.py` | Main orchestrator - coordinates extraction → cleaning → detection → storage |
| `article_extractor.py` | PyMuPDF text extraction with running header filtering |
| `article_detector.py` | Regex-based structure detection, state machine parser |
| `header_footer_cleaner.py` | Pattern-based header/footer removal |
| `article_models.py` | Pydantic models: `Article`, `Sentence`, `Clause`, `Subclause` |
| `article_db.py` | SQLite operations: insert, query, delete articles |
| `config.py` | Configuration: paths, thresholds, regex patterns |
| `cache.py` | JSON cache manager for extracted articles |
| `equation_extractor.py` | LLM vision extraction for vector equation graphics |
| `debug_extraction.py` | Diagnostic script for troubleshooting extraction issues |

## Key Data Models

```python
# article_models.py

class Article:
    article_number: str     # "3.5.2.1"
    title: str              # "Application of Section"
    division: str           # "A", "B", "C", "D"
    vintage: str            # "2020"
    full_text: str          # Complete article text
    sentences: List[Sentence]
    page_start: int
    page_end: int

class Sentence:
    sentence_number: str    # "1", "2", "3"
    reference: str          # "3.5.2.1.(1)"
    text: str
    clauses: List[Clause]

class Clause:
    clause_letter: str      # "a", "b", "c"
    reference: str          # "3.5.2.1.(1)(a)"
    text: str
    subclauses: List[Subclause]
```

## Configuration (config.py)

```python
# Header/footer thresholds
HEADER_THRESHOLD = 0.10     # Top 10% of page
FOOTER_THRESHOLD = 0.90     # Bottom 10% of page

# Key regex patterns
ARTICLE_PATTERN = r"^(\d+\.\d+\.\d+\.\d+)\.\s+(.*)$"  # "3.5.2.1. Title"
SENTENCE_PATTERN = r"^(\d+)\)"                         # "1)"
CLAUSE_PATTERN = r"^([a-z])\)"                         # "a)"
SUBCLAUSE_PATTERN = r"^(i{1,3}|iv|v|vi{0,3})\)"       # "i)", "ii)", etc.
```

## Usage

### Basic Parsing

```python
from bluesky.necb.build.sections import parse_vintage

result = parse_vintage(vintage="2020", save_to_db=True)
print(f"Extracted {len(result.articles)} articles")
```

### Query Database

```python
from bluesky.necb.build.sections import get_article_by_number

article = get_article_by_number("3.5.2.1", "2020")
print(f"{article.article_number}: {article.title}")
for sentence in article.sentences:
    print(f"  {sentence.reference}: {sentence.text[:50]}...")
```

### CLI Usage

```bash
# Parse and save to cache only (no database)
python -m bluesky.necb.build sections --cache-only --vintages 2020

# Parse and save to database
python -m bluesky.necb.build sections --vintages 2020

# Parse all vintages
python -m bluesky.necb.build sections --vintages 2011 2015 2017 2020
```

## Database Schema

```sql
CREATE TABLE necb_articles (
    id INTEGER PRIMARY KEY,
    vintage TEXT NOT NULL,
    division TEXT,
    article_number TEXT NOT NULL,
    title TEXT,
    full_text TEXT NOT NULL,
    page_start INTEGER,
    page_end INTEGER,
    extracted_at TIMESTAMP
);

CREATE TABLE necb_sentences (
    id INTEGER PRIMARY KEY,
    article_id INTEGER REFERENCES necb_articles(id),
    sentence_number TEXT NOT NULL,
    reference TEXT NOT NULL,
    text TEXT NOT NULL,
    clauses_json TEXT  -- Nested clauses/subclauses as JSON
);
```

## Cache Structure

```
{cache_dir}/
└── sections/
    └── {vintage}/
        └── {division}/
            └── {article_number}.json
```

Example cache file: `cache/sections/2020/B/8.4.4.17.json`

## Common Modifications

**Add new header/footer pattern:**
Edit `HEADER_FOOTER_PATTERNS` in `config.py`

**Adjust running header detection:**
Modify `RUNNING_HEADER_Y_THRESHOLD` in `article_extractor.py` (default: 50pt)

**Change article detection regex:**
Edit `ARTICLE_PATTERN` in `config.py`

**Enable equation extraction:**
Set `ANTHROPIC_API_KEY` environment variable

## Troubleshooting

**Missing articles:** Check if article header is being filtered as running header. Use `debug_extraction.py` to inspect raw vs cleaned text.

**Malformed hierarchy:** Verify regex patterns match article numbering style. NECB 2011 uses different patterns than 2020.

**Equation gaps:** Without `ANTHROPIC_API_KEY`, vector equations appear as blank gaps. Enable LLM vision for complete extraction.
