# Phase 1: NECB Article Extraction Implementation Plan

## Objective
Extract article-level structured text from NECB PDFs (2011, 2015, 2017, 2020) with hierarchical parsing: Part → Section → Subsection → Article → Clause → Subclause.

## Architecture

### Module Location
`src/bluesky/mcp/scrapers/necb/section_parser/`

### Approach
- Deterministic extraction using PyMuPDF + regex patterns
- 3-layer header/footer cleaning (position, frequency, regex)
- State machine for hierarchical structure detection
- Simple parent_id relationships in SQLite

### Target Vintages
All NECB editions: 2011, 2015, 2017, 2020

---

## Core Modules (7 modules)

### 1. config.py
**Purpose:** Configuration constants and patterns

**Responsibilities:**
- Position filter thresholds (header: top 10%, footer: bottom 10%)
- Frequency threshold for repeated line removal (≥70%)
- Regex patterns for each NECB vintage
- Database file paths
- Logging configuration

**Key Constants:**
- HEADER_THRESHOLD, FOOTER_THRESHOLD
- REPEAT_LINE_THRESHOLD
- ARTICLE_PATTERNS, CLAUSE_PATTERNS, SUBCLAUSE_PATTERNS
- DATABASE_PATH

---

### 2. article_models.py
**Purpose:** Pydantic data models for validation

**Models:**
- Article: article_number, title, full_text, parent_id, hierarchy_level, vintage, page_start, page_end
- Clause: clause_number, clause_text, article_id
- Section: section_number, title, parent_id
- Part: part_number, title

**Features:**
- Field validation for numbering patterns
- Vintage-specific validation rules
- Export methods: to_dict(), to_json()
- Hierarchy level enum: PART, SECTION, SUBSECTION, ARTICLE, CLAUSE, SUBCLAUSE

---

### 3. header_footer_cleaner.py
**Purpose:** Multi-layer header and footer removal

**Functions:**
- `clean_blocks_by_position(blocks, page_height)` → Position-based filtering
- `filter_repeated_lines(pages)` → Frequency-based removal
- `filter_regex_artifacts(lines, vintage)` → Regex cleanup
- `clean_pages(document, vintage)` → Full pipeline orchestrator

**Cleaning Layers:**
1. Position: Remove y0 < 10% (header) and y1 > 90% (footer)
2. Frequency: Track line occurrences, remove if present on ≥70% of pages
3. Regex: Remove page numbers, NRC headers, running titles, blank lines

**Input:** PyMuPDF blocks with coordinates
**Output:** Cleaned text lines with original line numbers preserved

---

### 4. article_detector.py
**Purpose:** Hierarchical structure detection and parsing

**Functions:**
- `detect_part(line)` → Match Part pattern, return number and title
- `detect_section(line)` → Match Section pattern
- `detect_article(line)` → Match Article pattern
- `detect_clause(line)` → Match clause numbering: 1), 2), 3)
- `detect_subclause(line)` → Match subclause: a), b), c)
- `is_continuation_line(line)` → Check if line continues previous element
- `parse_document(cleaned_lines, vintage)` → State machine orchestrator

**State Machine:**
- Track: current_part, current_section, current_subsection, current_article, current_clause
- Build parent-child relationships as parsing progresses
- Handle multi-page articles by accumulating text until next article detected

**Regex Patterns:**
- Part: `^Part\s+(\d+)\b`
- Section: `^Section\s+(\d+\.\d+)\s+(.*)$`
- Article: `^(\d+\.\d+\.\d+\.\d+)\s+(.*)$`
- Clause: `^\s*(\d+)\)\s+(.*)$`
- Subclause: `^\s*([a-z])\)\s+(.*)$`

**Output:** List of Article objects with nested clauses

---

### 5. article_extractor.py
**Purpose:** PDF text extraction with PyMuPDF

**Functions:**
- `load_pdf(pdf_path)` → Open PDF with PyMuPDF
- `extract_text_blocks(page)` → Get blocks with coordinates using get_text("blocks")
- `extract_document_text(pdf_path, vintage)` → Full extraction pipeline
- `normalize_text(text)` → Clean whitespace, fix encoding

**Pipeline:**
1. Load PDF document
2. Iterate pages, extract blocks with coordinates
3. Apply header_footer_cleaner
4. Normalize text (remove extra whitespace, fix line breaks)
5. Return cleaned text with page mapping

**Output:** List of (page_num, cleaned_text) tuples

---

### 6. article_db.py
**Purpose:** SQLite database operations

**Schema Extensions to necb_production.db:**

```sql
CREATE TABLE IF NOT EXISTS necb_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER,
    vintage TEXT NOT NULL,
    article_number TEXT NOT NULL,
    title TEXT,
    hierarchy_level TEXT NOT NULL,
    full_text TEXT NOT NULL,
    page_start INTEGER,
    page_end INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES necb_articles(id)
);

CREATE TABLE IF NOT EXISTS necb_clauses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,
    clause_number TEXT NOT NULL,
    clause_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES necb_articles(id)
);

CREATE INDEX idx_article_number ON necb_articles(article_number, vintage);
CREATE INDEX idx_article_parent ON necb_articles(parent_id);
CREATE INDEX idx_clause_article ON necb_clauses(article_id);
```

**Functions:**
- `init_database()` → Create tables and indexes
- `insert_article(article)` → Insert single article
- `insert_batch(articles)` → Bulk insert with transaction
- `get_article_by_number(article_number, vintage)` → Query by ID
- `get_children(parent_id)` → Get child articles
- `get_articles_by_vintage(vintage)` → Get all for vintage

---

### 7. article_parser.py
**Purpose:** Main orchestration pipeline

**Functions:**
- `parse_pdf(pdf_path, vintage)` → Full pipeline for one PDF
- `parse_all_vintages()` → Process all 4 vintages
- `main()` → CLI entry point with argparse

**Pipeline:**
1. Load PDF using article_extractor
2. Clean pages using header_footer_cleaner
3. Detect structure using article_detector
4. Validate using article_models
5. Store using article_db
6. Log statistics and errors

**CLI Interface:**
```bash
python article_parser.py --vintage 2020
python article_parser.py --all-vintages
python article_parser.py --pdf-path custom.pdf --vintage 2020
```

**Logging:**
- Progress tracking per page
- Articles extracted count
- Validation failures
- Database insertion errors

---

## Implementation Order

1. **Directory Setup** → Create section_parser/ and Implementation_docs/
2. **config.py** → Define all constants and patterns
3. **article_models.py** → Build Pydantic schemas
4. **header_footer_cleaner.py** → Implement 3-layer cleaning
5. **article_detector.py** → Build regex patterns and state machine
6. **article_extractor.py** → Integrate PyMuPDF
7. **article_db.py** → Extend database schema
8. **article_parser.py** → Build orchestrator and CLI
9. **__init__.py** → Expose public API
10. **Tests** → Unit and integration tests

---

## Testing Strategy

### Unit Tests
- Each cleaning function with sample text
- Each regex pattern with known article numbers
- Model validation with valid/invalid data
- Database operations with in-memory SQLite

### Integration Tests
- Full pipeline on 5-10 page PDF sample
- Multi-page article handling
- All 4 vintages with sample pages
- Parent-child relationship verification

### Validation
- Manual review of 20 random articles per vintage
- Check for missing articles (compare to TOC)
- Verify clause nesting accuracy
- Check text quality (no header/footer artifacts)

---

## Success Criteria

1. **Extraction Quality**
   - All Parts, Sections, Articles extracted
   - Proper hierarchy: Part → Section → Article → Clause
   - Multi-page articles handled correctly
   - No header/footer artifacts in article text

2. **Database Integrity**
   - All 4 vintages stored successfully
   - Parent-child relationships correct
   - No duplicate articles
   - Indexes created for fast queries

3. **Performance**
   - Process one vintage in <5 minutes
   - Memory usage stable (no leaks)
   - Logging provides clear progress

4. **Code Quality**
   - All functions have docstrings
   - Type hints throughout
   - Unit tests pass
   - No pylint/mypy errors

---

## Future Enhancements (Phase 2+)

**Not in Phase 1 scope:**
- LLM normalization (optional quality polish)
- Nested set integers (lft, rgt, depth)
- Vector DB integration
- Chunk mapping for RAG
- Article-table cross-references
- Figure/image extraction
- Table parsing integration

**Focus:** Get deterministic extraction working first. Optimize retrieval later.

---

## Dependencies

**Already Available:**
- PyMuPDF (fitz) - PDF text extraction
- Pydantic - Data validation
- SQLite3 - Database (built-in)

**No New Dependencies Required**

---

## File Structure

```
section_parser/
├── __init__.py
├── config.py
├── article_models.py
├── header_footer_cleaner.py
├── article_detector.py
├── article_extractor.py
├── article_db.py
├── article_parser.py
└── Implementation_docs/
    └── phase1-extraction-plan.md
```

---

## Estimated Effort

- Module implementation: ~4-6 hours
- Testing and validation: ~2-3 hours
- Debugging and refinement: ~2-3 hours
- **Total:** ~8-12 hours for complete Phase 1

---

## Notes

- Keep functions small and testable
- Log extensively for debugging
- No OCR - text-based PDFs only
- Tables/figures ignored in this phase
- Simple parent_id relationships (not nested sets yet)
- Focus on deterministic extraction quality
