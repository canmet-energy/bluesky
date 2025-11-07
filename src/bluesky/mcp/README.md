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

## Available Tools (16 total)

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

5. **search_ruby_gem_code**(gem_name, pattern, file_pattern="*.rb")
   - Search Ruby source code with ripgrep
   - Example: `search_ruby_gem_code("openstudio-standards", "create_shape")`

6. **get_ruby_gem_structure**(gem_name, path="")
   - Get file tree of a gem
   - Example: `get_ruby_gem_structure("openstudio-standards", "lib")`

7. **read_ruby_source_file**(gem_name, file_path)
   - Read a specific Ruby file
   - Example: `read_ruby_source_file("openstudio-standards", "lib/openstudio-standards/geometry/create_shape.rb")`

8. **find_ruby_examples**(concept, gems?)
   - Find usage examples in gems
   - Example: `find_ruby_examples("NECB space types")`

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

### NECB Query Tools (5)

12. **query_necb_sections**(vintage, section_pattern?, title_pattern?, limit=20)
    - Search NECB sections by vintage, section number, or title
    - Example: `query_necb_sections("2020", section_pattern="3.2")`

13. **get_necb_table**(vintage, table_number)
    - Get a specific NECB table with all rows
    - Example: `get_necb_table("2020", "Table-45-3")`

14. **query_necb_requirements**(requirement_type?, vintage?, section?, limit=50)
    - Search NECB requirements by type, vintage, or section
    - Example: `query_necb_requirements(requirement_type="u_value", vintage="2020")`

15. **search_necb**(query, vintage?, content_type?, limit=20)
    - Full-text search across all NECB content
    - Example: `search_necb("thermal envelope requirements")`

16. **compare_necb_vintages**(requirement_type, vintages?)
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
src/bluesky/mcp/data/openstudio-3.9.0.db  (6.52 MB)
src/bluesky/mcp/data/necb.db              (4.37 MB)
```

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
├── openstudio_server.py           # Main MCP server (16 tools)
├── scrapers/
│   ├── openstudio_docs_scraper.py # S3 documentation scraper
│   ├── db_builder.py              # SQLite database builder
│   ├── necb/
│   │   ├── necb_pdf_downloader.py # Download NECB PDFs from NRC
│   │   ├── necb_pdf_parser.py     # Parse NECB PDFs
│   │   └── necb_db_builder.py     # Build NECB database
│   └── __main__.py                # CLI for running scraper
├── data/
│   ├── openstudio-3.9.0.db        # OpenStudio database (6.52 MB)
│   └── necb.db                    # NECB database (4.37 MB)
└── README.md                       # This file
```

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

## Implementation Stats

- **Phase 1:** OpenStudio Scraper + Database Builder (~800 lines)
- **Phase 2:** MCP Server with 11 tools (~600 lines)
- **Phase 3:** NECB PDF Parser + Database Builder (~560 lines)
- **Phase 4:** NECB Query Tools (~290 lines)
- **Total Implementation:** ~2,250 lines
- **Total Database Size:** 11 MB (fits easily in GitHub)
- **Performance:** <100ms typical query time

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

### Ripgrep Not Available

```
FileNotFoundError: [Errno 2] No such file or directory: 'rg'
```

**Solution:** Install ripgrep (usually pre-installed in devcontainer)

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
