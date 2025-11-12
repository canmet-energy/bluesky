# OpenStudio MCP Server

**Status:** ✅ Fully Implemented
**Version:** OpenStudio 3.9.0 + NECB 2011-2020
**Database Size:** 11 MB (OpenStudio 6.52 MB + NECB 4.37 MB)

## Overview

The OpenStudio MCP Server provides LLMs with dynamic access to:
- **OpenStudio SDK documentation** (619 classes from C++ docs)
- **NECB building code** (Canadian National Energy Code for Buildings 2011-2020)
- **Ruby gem source code** (openstudio-standards, measure gems)
- **Code generation** (Python/Ruby examples)

## Quick Start

### 1. Start the MCP Server

```bash
python -m bluesky.mcp.openstudio_server
```

### 2. Configure Claude Desktop

Add to your Claude Desktop config:

```json
{
  "mcpServers": {
    "openstudio": {
      "command": "uv",
      "args": ["run", "python", "-m", "bluesky.mcp.openstudio_server"],
      "env": {
        "PYTHONPATH": "/path/to/bluesky/src"
      }
    }
  }
}
```

### 3. Use in Claude

Claude can now query OpenStudio documentation dynamically:

```
You: "Show me how to create a thermal zone in OpenStudio"
Claude: [Uses query_openstudio_classes and generate_python_example tools]
```

## Available Tools (17 total)

### OpenStudio SDK Query Tools (4)

1. **query_openstudio_classes**(pattern, namespace?, limit=50)
   - Search 619 classes by name pattern
   - Example: `query_openstudio_classes("ThermalZone")`

2. **get_class_methods**(class_name, filter?, include_inherited=false)
   - Get all methods for a class
   - Example: `get_class_methods("ThermalZone")`

3. **get_method_details**(class_name, method_name)
   - Get detailed method documentation with parameters
   - Example: `get_method_details("ThermalZone", "setName")`

4. **search_sdk_documentation**(query, search_type="all", limit=20)
   - Full-text search across all documentation
   - Example: `search_sdk_documentation("how to add HVAC")`

### Ruby Gem Tools (4)

**Supported Gems:**
- `openstudio-standards` (NECB, ASHRAE 90.1, DOE prototypes)
- `openstudio-common-measures` (common measure patterns)
- `openstudio-model-articulation` (geometry and model manipulation)

5. **search_ruby_gem_code**(gem_name, pattern, file_pattern="*.rb")
   - Search Ruby source code with ripgrep
   - Gem location: `vendor/bundle/ruby/3.2.0/bundler/gems/`
   - Example: `search_ruby_gem_code("openstudio-standards", "necb_space_type")`
   - Use cases: Find NECB methods, ASHRAE compliance code, geometry helpers

6. **get_ruby_gem_structure**(gem_name, path="")
   - Get file tree of a gem
   - Example: `get_ruby_gem_structure("openstudio-standards", "lib/openstudio-standards")`

7. **read_ruby_source_file**(gem_name, file_path)
   - Read a specific Ruby file from gems
   - Example: `read_ruby_source_file("openstudio-standards", "lib/openstudio-standards/standards/necb/necb_2020/necb_2020.rb")`

8. **find_ruby_examples**(concept, gems?)
   - Find usage examples across multiple gems
   - Default gems: openstudio-standards, openstudio-common-measures, openstudio-model-articulation
   - Example: `find_ruby_examples("NECB space types")`
   - Example: `find_ruby_examples("create geometry", ["openstudio-model-articulation"])`

### Code Generation Tools (3)

9. **generate_python_example**(operation, style="documented")
   - Generate Python OpenStudio code
   - Example: `generate_python_example("create thermal zone")`

10. **generate_ruby_example**(operation, standard?)
    - Generate Ruby openstudio-standards code
    - Example: `generate_ruby_example("create NECB building")`

11. **compare_python_ruby**(operation)
    - Show Python and Ruby equivalents side-by-side
    - Example: `compare_python_ruby("create thermal zone")`

### NECB Query Tools (6)

12. **query_necb_sections**(vintage, section_pattern?, title_pattern?, limit=20)
    - Search NECB sections by vintage, section number, or title
    - Example: `query_necb_sections("2020", section_pattern="3.2")`

13. **get_necb_table**(vintage, table_number)
    - Get a specific NECB table with all rows
    - Supports formats: "3.2.2.2", "Table 3.2.2.2", "Table 3.2.2.2.", "Table-45-3"
    - Example: `get_necb_table("2020", "3.2.2.2")`

14. **query_necb_requirements**(requirement_type?, vintage?, section?, limit=50)
    - Search NECB requirements by type, vintage, or section
    - Types: "envelope", "u_value", "lighting_power_density", "climate_zone"
    - Example: `query_necb_requirements(requirement_type="u_value", vintage="2020")`

15. **search_necb**(query, vintage?, content_type?, limit=20)
    - Full-text keyword search across all NECB content
    - Example: `search_necb("thermal envelope requirements")`

16. **semantic_search_necb**(query, vintage="2020", top_k=5, use_query_understanding=True)
    - Natural language semantic search with AI-powered query understanding
    - Extracts entities: location, climate zone, building type, concepts
    - Uses hybrid keyword + vector search with reciprocal rank fusion
    - **Requires initialization:** Run `python -m bluesky.mcp.tools.vector_indexer` first
    - Examples:
      - `semantic_search_necb("What's the max window area for a 3-story office in Calgary?")`
      - `semantic_search_necb("R-value for roofs in Vancouver NECB 2020")`
      - `semantic_search_necb("Lighting power density for school classrooms in Toronto")`

17. **compare_necb_vintages**(requirement_type, vintages?)
    - Compare a specific requirement type across NECB vintages
    - Example: `compare_necb_vintages("u_value", ["2015", "2020"])`

## Database Details

### What's Indexed

**OpenStudio SDK:**
- **619 classes** from `openstudio::model` namespace
- **24,124 methods** with signatures and parameters
- **10,425 parameters** with types and names
- **Full-text search** via SQLite FTS5

**NECB Building Code:**
- **4 vintages** (2011, 2015, 2017, 2020)
- **1,810 sections** across all vintages
- **729 tables** with prescriptive requirements
- **204 requirements** (U-values, lighting power density, climate zones)
- **Full-text search** via SQLite FTS5

### Database Location

```
src/bluesky/mcp/data/openstudio-3.9.0.db  (6.52 MB)   # OpenStudio SDK docs
src/bluesky/mcp/data/necb.db              (4.37 MB)   # NECB code (SQLite + FTS5)
src/bluesky/mcp/data/chroma/              (~15 MB)    # Vector embeddings (ChromaDB)
```

**Note:** ChromaDB vector index is optional. If not initialized, `semantic_search_necb()` will return an error message directing users to run the vector indexer. All other tools work without it.

### Top Classes by Method Count

1. `CoilCoolingDXSingleSpeedThermalStorage` - 277 methods
2. `Facility` - 237 methods
3. `AirConditionerVariableRefrigerantFlow` - 234 methods
4. `RefrigerationCase` - 208 methods
5. `CoolingTowerTwoSpeed` - 186 methods

## Architecture

### File Structure

```
src/bluesky/mcp/
├── openstudio_server.py           # Main MCP server (17 tools)
├── scrapers/
│   ├── openstudio_docs_scraper.py # S3 documentation scraper
│   ├── db_builder.py              # SQLite database builder
│   ├── necb/
│   │   ├── necb_pdf_downloader.py # Download NECB PDFs from NRC
│   │   ├── necb_pdf_parser.py     # Parse NECB PDFs (marker-pdf + camelot)
│   │   └── necb_db_builder.py     # Build NECB database
│   └── __main__.py                # CLI for running scraper
├── tools/
│   ├── vector_indexer.py          # ChromaDB vector index builder
│   ├── hybrid_search.py           # Hybrid keyword + semantic search engine
│   ├── query_understanding.py     # NLP query entity extraction
│   └── model_config.py            # Ollama embedding model config
├── data/
│   ├── openstudio-3.9.0.db        # OpenStudio database (6.52 MB)
│   ├── necb.db                    # NECB database (4.37 MB)
│   └── chroma/                    # Vector embeddings (ChromaDB)
└── README.md                       # This file
```

### Semantic Search Architecture

The `semantic_search_necb()` tool uses a sophisticated hybrid search pipeline:

```
User Query: "What's the max window area for a 3-story office in Calgary?"
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 1. Query Understanding (query_understanding.py)            │
│    - Entity extraction: location="Calgary", building="office"│
│    - Concept mapping: "window area" → NECB synonyms         │
│    - Query expansion with building code terminology         │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Hybrid Search (hybrid_search.py)                        │
│    - Keyword search: SQLite FTS5 for exact term matching    │
│    - Semantic search: ChromaDB vector similarity search     │
│    - Reciprocal Rank Fusion (RRF): Merge both rankings     │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Results with Provenance                                 │
│    - Content: Full section/table text                      │
│    - Metadata: Page number, section/table number           │
│    - Rankings: Keyword rank, semantic rank, RRF score      │
│    - Extracted entities: For debugging query understanding  │
└─────────────────────────────────────────────────────────────┘
```

**Key Components:**

- **Query Understanding** (`query_understanding.py`):
  - Extracts: location, climate zone, building type, NECB concepts
  - Maps colloquial terms → NECB terminology (e.g., "R-value" → "thermal resistance")
  - Canadian location → climate zone + HDD lookup

- **Vector Indexer** (`vector_indexer.py`):
  - Uses Ollama `nomic-embed-text` model (768-dim embeddings)
  - Stores in ChromaDB with metadata (vintage, type, page_number)
  - Run: `python -m bluesky.mcp.tools.vector_indexer`

- **Hybrid Search** (`hybrid_search.py`):
  - SQLite FTS5: Fast exact keyword matching
  - ChromaDB: Semantic similarity via cosine distance
  - RRF: Combines rankings for best of both worlds

**When to Use Each Search:**

| Tool | Best For | Speed |
|------|----------|-------|
| `search_necb()` | Exact terminology, known keywords | Fast (FTS5 only) |
| `semantic_search_necb()` | Natural language, conceptual queries | Slower (hybrid) |
| `query_necb_sections()` | Known section numbers | Fastest (indexed lookup) |

### Database Schema

**OpenStudio SDK Database:**
```sql
-- Classes
CREATE TABLE classes (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    namespace TEXT,
    full_name TEXT NOT NULL,
    description TEXT,
    parent_class TEXT,
    doc_url TEXT
);

-- Methods
CREATE TABLE methods (
    id INTEGER PRIMARY KEY,
    class_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    signature TEXT,
    return_type TEXT,
    description TEXT,
    is_static BOOLEAN,
    is_const BOOLEAN
);

-- Method Parameters
CREATE TABLE method_params (
    id INTEGER PRIMARY KEY,
    method_id INTEGER NOT NULL,
    param_order INTEGER NOT NULL,
    param_name TEXT,
    param_type TEXT NOT NULL,
    default_value TEXT
);

-- Full-text Search
CREATE VIRTUAL TABLE search_index USING fts5(
    content_type,
    name,
    description
);
```

**NECB Database:**
```sql
-- Sections
CREATE TABLE necb_sections (
    id INTEGER PRIMARY KEY,
    vintage TEXT NOT NULL,
    section_number TEXT NOT NULL,
    title TEXT,
    content TEXT,
    page_number INTEGER
);

-- Tables
CREATE TABLE necb_tables (
    id INTEGER PRIMARY KEY,
    vintage TEXT NOT NULL,
    table_number TEXT NOT NULL,
    title TEXT,
    headers TEXT,  -- JSON array
    page_number INTEGER
);

-- Table Rows
CREATE TABLE necb_table_rows (
    id INTEGER PRIMARY KEY,
    table_id INTEGER NOT NULL,
    row_data TEXT  -- JSON array
);

-- Requirements
CREATE TABLE necb_requirements (
    id INTEGER PRIMARY KEY,
    vintage TEXT NOT NULL,
    section TEXT,
    requirement_type TEXT,
    description TEXT,
    value TEXT,
    unit TEXT
);

-- Full-text Search
CREATE VIRTUAL TABLE necb_search USING fts5(
    vintage,
    content_type,
    title,
    content
);
```

## Refreshing the Database

### OpenStudio SDK

To update the OpenStudio documentation database (e.g., for new versions):

```bash
python -m bluesky.mcp.scrapers --output src/bluesky/mcp/data/openstudio-3.X.0.db --version 3.X.0
```

Scraping time: ~19 seconds (50 concurrent requests to S3)

### NECB Building Code

To rebuild the NECB database:

```bash
# Download PDFs (if needed)
python -m bluesky.mcp.scrapers.necb.necb_pdf_downloader

# Build database from PDFs
python -m bluesky.mcp.scrapers.necb.necb_db_builder
```

Processing time: ~90 seconds (4 PDFs, ~1,260 pages total)

### Vector Index for Semantic Search

To enable the `semantic_search_necb()` tool, build the ChromaDB vector index:

```bash
# Ensure Ollama is installed and running
ollama pull nomic-embed-text

# Build vector index from NECB database
python -m bluesky.mcp.tools.vector_indexer

# Output: src/bluesky/mcp/data/chroma/ (~15 MB)
```

**Requirements:**
- Ollama with `nomic-embed-text` model
- ~2-3 minutes to index all NECB sections and tables
- 768-dimensional embeddings stored in ChromaDB

**Note:** This step is optional. All other MCP tools work without it.

## Implementation Stats

- **Phase 1:** OpenStudio Scraper + Database Builder (~800 lines)
- **Phase 2:** MCP Server with 11 tools (~600 lines)
- **Phase 3:** NECB PDF Parser + Database Builder (~560 lines)
- **Phase 4:** NECB Query Tools (~290 lines)
- **Phase 5:** Semantic Search (vector indexer, hybrid search, query understanding) (~450 lines)
- **Total Implementation:** ~2,700 lines
- **Total Database Size:** ~26 MB (SQLite 11 MB + ChromaDB 15 MB)
- **Performance:**
  - SQLite queries: <100ms
  - Semantic search: ~500-1500ms (depends on query complexity and Ollama response time)

## Future Enhancements

### Completed
1. ✅ **NECB PDF documentation** - Extracted all 4 vintages (2011-2020)

### Planned (from docs/mcp.md)

1. **ASHRAE standards** - Index ASHRAE 90.1 documentation
2. **EnergyPlus I/O Reference** - Scrape EnergyPlus docs
3. **More code templates** - Expand code generation library
4. **HVAC system patterns** - Add air loops and plant loops API reference
5. **Enhanced NECB parsing** - Improve table extraction, add climate zone mappings

### How to Add New Documentation

The NECB implementation serves as a complete example:

1. **Create scrapers** in `scrapers/new_source/`
   - `pdf_downloader.py` - Download source documents
   - `pdf_parser.py` - Extract structured data
   - `db_builder.py` - Build SQLite database

2. **Build database**: `src/bluesky/mcp/data/new-docs.db`

3. **Add query tools** to `openstudio_server.py`:
   ```python
   @mcp.tool()
   def query_new_source(param: str):
       """Query new documentation source"""
       conn = get_new_source_connection()
       # Implementation
   ```

4. **Update README** with new tools and database details

See `scrapers/necb/` for complete reference implementation.

## Testing

```bash
# Test the scraper
python -m bluesky.mcp.scrapers

# Test the server
python -m bluesky.mcp.openstudio_server

# Test a specific tool
python -c "from bluesky.mcp.openstudio_server import query_openstudio_classes; print(query_openstudio_classes('ThermalZone'))"
```

## Troubleshooting

### Database Not Found

```
FileNotFoundError: Database not found: .../openstudio-3.9.0.db
```

**Solution:** Run the scraper to build the database:

```bash
python -m bluesky.mcp.scrapers
```

### Gem Not Found

```
{"error": "Gem not found: openstudio-standards"}
```

**Solution:** Verify vendor gems are installed:

```bash
ls -la vendor/bundle/ruby/3.2.0/bundler/gems/
```

Expected gems:
- `openstudio-standards-gem-*`
- `openstudio-common-measures-gem-*`
- `openstudio-model-articulation-gem-*`

If missing, run:
```bash
bundle install --path vendor/bundle
```

### Ripgrep Not Available

```
FileNotFoundError: [Errno 2] No such file or directory: 'rg'
```

**Solution:** Install ripgrep (usually pre-installed in devcontainer)

```bash
# Ubuntu/Debian
apt-get install ripgrep

# macOS
brew install ripgrep
```

### Semantic Search Not Initialized

```
{"error": "Semantic search not initialized"}
```

**Solution:** Build the vector index:

```bash
# Install Ollama and pull embedding model
ollama pull nomic-embed-text

# Build vector index
python -m bluesky.mcp.tools.vector_indexer
```

Verify index exists:
```bash
ls -la src/bluesky/mcp/data/chroma/
```

### Ollama Connection Error

```
Error: Failed to connect to Ollama
```

**Solution:** Ensure Ollama is running:

```bash
# Check if Ollama is installed
ollama --version

# Check if service is running
ollama list

# If not running, start Ollama service (usually auto-starts)
# On macOS: Ollama runs as a menu bar app
# On Linux: systemctl start ollama (if installed as service)
```

### Slow Semantic Search Performance

If `semantic_search_necb()` is taking >2 seconds:

1. **Check Ollama model:** Ensure `nomic-embed-text` is pulled locally
   ```bash
   ollama list  # Should show nomic-embed-text
   ```

2. **GPU acceleration:** Ollama uses GPU if available
   - Check: `nvidia-smi` (NVIDIA) or `rocm-smi` (AMD)
   - CPU-only mode is slower but functional

3. **Reduce query complexity:** Shorter queries are faster
   ```python
   # Slower
   semantic_search_necb("What are all the thermal transmittance requirements for above-grade walls in commercial buildings located in climate zone 6 according to NECB 2020?")

   # Faster
   semantic_search_necb("wall U-value climate zone 6")
   ```

## References

- **Implementation Plan:** `/docs/mcp.md` (complete 600-line plan)
- **OpenStudio C++ Docs:** https://s3.amazonaws.com/openstudio-sdk-documentation/cpp/OpenStudio-3.9.0-doc/model/html/
- **FastMCP Docs:** https://gofastmcp.com
- **MCP Specification:** https://modelcontextprotocol.io

## Credits

Built with:
- **FastMCP** - MCP server framework
- **httpx** - Async HTTP client for scraping
- **BeautifulSoup4** - HTML parsing
- **SQLite** - Database and full-text search
- **ripgrep** - Fast Ruby code search

---

**Status:** ✅ Ready for use
**Last Updated:** 2025-11-06
**OpenStudio Version:** 3.9.0
**NECB Vintages:** 2011, 2015, 2017, 2020
