# OpenStudio MCP Server Implementation Plan

**Status:** Planning
**Target OpenStudio Version:** 3.9.0
**Estimated Implementation Time:** 16-23 hours
**Last Updated:** 2025-01-06

---

## Overview

Build a Model Context Protocol (MCP) server that provides LLMs with dynamic access to:
1. **OpenStudio SDK documentation** - 1,100+ classes with methods, parameters, descriptions
2. **Ruby gem source code** - Search 5,100+ Ruby files across openstudio-standards and measure gems
3. **Code generation** - Generate Python/Ruby examples on-demand

### Goals

- ✅ Enable LLMs to discover OpenStudio classes/methods dynamically (no hardcoded knowledge)
- ✅ Search Ruby gem code for patterns and examples
- ✅ Generate working Python/Ruby code for common operations
- ✅ Fast startup (<1 second using pre-built index)
- ✅ Auto-refresh documentation (background, non-blocking)
- ✅ Work offline (shipped database)
- ✅ Extensible (add NECB PDF, ASHRAE standards, EnergyPlus docs later)

---

## Architecture

### Documentation Strategy

**Hybrid approach:**
1. **Pre-scraped SQLite database** (~5-8 MB, ships with repo)
   - Contains: 1,100+ OpenStudio classes from C++ docs
   - Source: `https://s3.amazonaws.com/openstudio-sdk-documentation/cpp/OpenStudio-3.9.0-doc/model/html/`
   - Location: `src/bluesky/mcp/data/openstudio-3.9.0.db`

2. **Auto-refresh logic** (non-blocking)
   - Check shipped DB age on startup
   - If >30 days old: trigger background refresh
   - Use local cache: `~/.cache/bluesky/openstudio-3.9.0.db`

3. **Manual refresh** via CLI
   ```bash
   bluesky mcp-server --refresh-docs
   bluesky refresh-openstudio-docs
   ```

### Why SQLite Over JSON?

| Feature | SQLite | JSON |
|---------|--------|------|
| Size | 5-8 MB | 15-20 MB |
| Queries | Indexed, fast | Full scan |
| Memory | Load on demand | Load entire file |
| Search | FTS5 full-text | Manual |
| GitHub-friendly | ✅ <50 MB | ✅ <50 MB |

**Verdict:** SQLite is more efficient in every way.

---

## File Structure

```
src/bluesky/mcp/
├── __init__.py
├── openstudio_server.py              # Main FastMCP server entry point
│
├── scrapers/                          # Documentation scrapers
│   ├── __init__.py
│   ├── openstudio_docs_scraper.py    # Scrape S3 C++ docs (1,100+ classes)
│   └── db_builder.py                 # Build SQLite database from scraped data
│
├── tools/                             # MCP tools (11 total)
│   ├── __init__.py
│   ├── sdk_query.py                  # 4 SDK query tools
│   ├── ruby_gems.py                  # 4 Ruby gem search tools
│   └── code_generation.py            # 3 code generation tools
│
├── utils/                             # Utilities
│   ├── __init__.py
│   ├── cpp_to_python.py              # C++ → Python/Ruby name mapping
│   ├── ruby_searcher.py              # Ripgrep wrapper for gem search
│   └── code_templates.py             # Code generation templates
│
└── data/                              # Data files
    ├── openstudio-3.9.0.db           # Pre-scraped SQLite DB (ship with repo)
    └── .gitignore                     # Ignore .cache/ directory

.mcp.json                              # MCP server configuration (repo root)
```

---

## Database Schema

### SQLite Tables

```sql
-- Metadata table
CREATE TABLE metadata (
    version TEXT PRIMARY KEY,           -- "3.9.0"
    scraped_at TEXT,                    -- ISO 8601 timestamp
    source_url TEXT,                    -- S3 base URL
    total_classes INTEGER,              -- 1,100+
    total_methods INTEGER               -- ~30,000+
);

-- Classes table
CREATE TABLE classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                 -- "Model"
    namespace TEXT,                     -- "openstudio::model"
    full_name TEXT,                     -- "openstudio::model::Model"
    description TEXT,                   -- Class description from docs
    parent_class TEXT,                  -- "Workspace" (null if no parent)
    doc_url TEXT,                       -- Full URL to class documentation
    UNIQUE(namespace, name)
);
CREATE INDEX idx_class_name ON classes(name);
CREATE INDEX idx_class_namespace ON classes(namespace);
CREATE INDEX idx_class_full_name ON classes(full_name);

-- Methods table
CREATE TABLE methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL,
    name TEXT NOT NULL,                 -- "getBuilding"
    signature TEXT,                     -- "boost::optional<Building> getBuilding() const"
    return_type TEXT,                   -- "boost::optional<Building>"
    description TEXT,                   -- Method description
    is_static BOOLEAN DEFAULT 0,
    is_const BOOLEAN DEFAULT 0,
    FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE
);
CREATE INDEX idx_method_class ON methods(class_id);
CREATE INDEX idx_method_name ON methods(name);

-- Method parameters table
CREATE TABLE method_params (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    method_id INTEGER NOT NULL,
    param_order INTEGER NOT NULL,       -- 0, 1, 2, ...
    param_name TEXT,                    -- "zone" (may be empty in C++ docs)
    param_type TEXT,                    -- "ThermalZone&"
    default_value TEXT,                 -- null if no default
    FOREIGN KEY(method_id) REFERENCES methods(id) ON DELETE CASCADE
);
CREATE INDEX idx_param_method ON method_params(method_id);

-- Full-text search table (for fast text search)
CREATE VIRTUAL TABLE search_index USING fts5(
    content_type,                       -- "class" or "method"
    name,                               -- Class or method name
    description,                        -- Full description
    content='',                         -- External content (don't duplicate)
    content_rowid=id
);
```

### Database Size Estimate

- **1,100 classes** × 500 bytes = 550 KB
- **30,000 methods** × 350 bytes = 10.5 MB
- **Parameters** (avg 2/method) × 150 bytes = 9 MB
- **FTS5 index** ≈ 3 MB
- **Total:** ~5-8 MB (compressed with SQLite page compression)

---

## MCP Tools

### SDK Query Tools (4 tools)

#### 1. `query_openstudio_classes`
**Description:** Search OpenStudio SDK for classes matching a pattern

**Parameters:**
- `pattern` (string, required): Regex pattern to match class names (e.g., ".*Zone.*", "Coil.*Heating.*")
- `namespace` (string, optional): Filter by namespace ("model", "measure", "utilities")
- `limit` (integer, optional, default=50): Maximum results to return

**Returns:**
```json
[
  {
    "name": "ThermalZone",
    "namespace": "openstudio::model",
    "description": "Represents a thermal zone in the building...",
    "parent_class": "ParentObject",
    "doc_url": "https://s3.amazonaws.com/..."
  }
]
```

**Example usage:**
```
query_openstudio_classes(pattern="ThermalZone", namespace="model")
query_openstudio_classes(pattern="Coil.*DX.*", limit=20)
```

---

#### 2. `get_class_methods`
**Description:** Get all methods for a specific OpenStudio class

**Parameters:**
- `class_name` (string, required): Full class name (e.g., "ThermalZone", "openstudio::model::ThermalZone")
- `filter` (string, optional): Filter methods by name pattern (e.g., "set.*", ".*Equipment.*")
- `include_inherited` (boolean, optional, default=false): Include methods from parent classes

**Returns:**
```json
[
  {
    "name": "setName",
    "signature": "void setName(const std::string& name)",
    "return_type": "void",
    "description": "Sets the name of the thermal zone",
    "is_static": false,
    "is_const": false,
    "parameters": [
      {"name": "name", "type": "const std::string&"}
    ]
  }
]
```

**Example usage:**
```
get_class_methods(class_name="ThermalZone")
get_class_methods(class_name="Model", filter="get.*")
```

---

#### 3. `get_method_details`
**Description:** Get detailed documentation for a specific method

**Parameters:**
- `class_name` (string, required): Class name
- `method_name` (string, required): Method name

**Returns:**
```json
{
  "class": "openstudio::model::ThermalZone",
  "name": "setCoolingPriority",
  "signature": "bool setCoolingPriority(const std::vector<ModelObject>& equipment, unsigned priority)",
  "return_type": "bool",
  "description": "Set the priority of cooling equipment in the thermal zone...",
  "parameters": [
    {
      "name": "equipment",
      "type": "const std::vector<ModelObject>&",
      "description": "Vector of equipment to set priority for"
    },
    {
      "name": "priority",
      "type": "unsigned",
      "description": "Priority order (0 is highest)"
    }
  ],
  "python_equivalent": "zone.setCoolingPriority(equipment, priority)",
  "ruby_equivalent": "zone.setCoolingPriority(equipment, priority)"
}
```

---

#### 4. `search_sdk_documentation`
**Description:** Full-text search across all OpenStudio SDK documentation

**Parameters:**
- `query` (string, required): Search query (natural language or keywords)
- `search_type` (string, optional, default="all"): "classes", "methods", or "all"
- `limit` (integer, optional, default=20): Maximum results

**Returns:**
```json
[
  {
    "type": "class",
    "name": "ThermalZone",
    "relevance_score": 0.95,
    "snippet": "...represents a thermal zone in the building model...",
    "doc_url": "https://..."
  },
  {
    "type": "method",
    "class": "ThermalZone",
    "name": "equipment",
    "relevance_score": 0.87,
    "snippet": "...returns all equipment serving this thermal zone..."
  }
]
```

**Example usage:**
```
search_sdk_documentation(query="how to add HVAC to thermal zone")
search_sdk_documentation(query="window construction", search_type="classes")
```

---

### Ruby Gem Tools (4 tools)

#### 5. `search_ruby_gem_code`
**Description:** Search Ruby gem source code for patterns using ripgrep

**Parameters:**
- `gem_name` (string, required): Gem name ("openstudio-standards", "openstudio-common-measures", etc.)
- `pattern` (string, required): Search pattern (regex)
- `file_pattern` (string, optional, default="*.rb"): File glob pattern

**Returns:**
```json
[
  {
    "gem": "openstudio-standards",
    "file": "lib/openstudio-standards/hvac/cbecs_hvac.rb",
    "line": 142,
    "code_snippet": "def add_cbecs_hvac_system(model, system_type, zones)"
  }
]
```

**Example usage:**
```
search_ruby_gem_code(gem_name="openstudio-standards", pattern="create_shape_")
search_ruby_gem_code(gem_name="openstudio-common-measures", pattern="def.*thermal.*zone")
```

---

#### 6. `get_ruby_gem_structure`
**Description:** Get file tree structure of a Ruby gem

**Parameters:**
- `gem_name` (string, required): Gem name
- `path` (string, optional): Subdirectory within gem (e.g., "lib/openstudio-standards")

**Returns:**
```json
{
  "gem": "openstudio-standards",
  "path": "lib/openstudio-standards",
  "directories": [
    "geometry",
    "hvac",
    "standards"
  ],
  "files": [
    "version.rb",
    "geometry.rb",
    "hvac.rb"
  ]
}
```

---

#### 7. `read_ruby_source_file`
**Description:** Read a specific Ruby source file from a gem

**Parameters:**
- `gem_name` (string, required): Gem name
- `file_path` (string, required): Relative path within gem

**Returns:**
```json
{
  "gem": "openstudio-standards",
  "file": "lib/openstudio-standards/geometry/create_shape.rb",
  "content": "# Full file contents...",
  "lines": 450
}
```

---

#### 8. `find_ruby_examples`
**Description:** Find example usage patterns in Ruby gems

**Parameters:**
- `concept` (string, required): What to find examples of (e.g., "NECB space types", "create geometry")
- `gems` (array[string], optional): Specific gems to search (default: all)

**Returns:**
```json
[
  {
    "concept_match": "NECB space types",
    "gem": "openstudio-standards",
    "file": "lib/openstudio-standards/standards/necb/necb_2011/building.rb",
    "code_snippet": "def apply_necb_space_type(space, building_type, space_type_name)",
    "context": "Applies NECB 2011 space type properties to a space"
  }
]
```

---

### Code Generation Tools (3 tools)

#### 9. `generate_python_example`
**Description:** Generate Python example code for OpenStudio operations

**Parameters:**
- `operation` (string, required): What to do (e.g., "create thermal zone", "add VAV system")
- `style` (string, optional, default="documented"): "minimal", "documented", or "comprehensive"

**Returns:**
```json
{
  "operation": "create thermal zone",
  "language": "python",
  "style": "documented",
  "code": "import openstudio\n\n# Create model\nmodel = openstudio.model.Model()\n\n# Create thermal zone\nzone = openstudio.model.ThermalZone(model)\nzone.setName('Office Zone')\n\n# Create thermostat\nthermostat = openstudio.model.ThermostatSetpointDualSetpoint(model)\nthermostat.setHeatingSetpointTemperatureSchedule(heating_schedule)\nthermostat.setCoolingSetpointTemperatureSchedule(cooling_schedule)\nzone.setThermostatSetpointDualSetpoint(thermostat)",
  "explanation": "Creates a thermal zone with dual setpoint thermostat..."
}
```

---

#### 10. `generate_ruby_example`
**Description:** Generate Ruby example code using openstudio-standards

**Parameters:**
- `operation` (string, required): What to do
- `standard` (string, optional): Building standard ("NECB", "ASHRAE 90.1-2019", etc.)

**Returns:**
```json
{
  "operation": "create NECB office building",
  "language": "ruby",
  "standard": "NECB 2020",
  "code": "require 'openstudio'\nrequire 'openstudio-standards'\n\n# Create model\nmodel = OpenStudio::Model::Model.new\n\n# Create geometry\ngeometry = OpenstudioStandards::Geometry.create_shape_rectangle(\n  model,\n  length: 50.0,\n  width: 30.0,\n  num_floors: 3\n)\n\n# Apply NECB 2020 space types\nstandard = Standard.build('NECB2020')\nstandard.model_add_necb_space_type(model, 'Office', 'OpenOffice')"
}
```

---

#### 11. `compare_python_ruby`
**Description:** Show equivalent code in both Python and Ruby

**Parameters:**
- `operation` (string, required): Operation to demonstrate

**Returns:**
```json
{
  "operation": "add window to wall",
  "python_code": "# Python\nimport openstudio\n\nwindow = openstudio.model.SubSurface(vertices, model)\nwindow.setSurface(wall)\nwindow.setSubSurfaceType('FixedWindow')",
  "ruby_code": "# Ruby\nrequire 'openstudio'\n\nwindow = OpenStudio::Model::SubSurface.new(vertices, model)\nwindow.setSurface(wall)\nwindow.setSubSurfaceType('FixedWindow')",
  "notes": [
    "Python uses openstudio. prefix, Ruby uses OpenStudio::",
    "Both use same method names and signatures",
    "Vertex creation differs: Python uses Point3dVector(), Ruby uses Point3dVector.new + <<"
  ]
}
```

---

## Scraping Strategy

### Source
**URL:** `https://s3.amazonaws.com/openstudio-sdk-documentation/cpp/OpenStudio-3.9.0-doc/model/html/`

### Process

1. **Fetch class list**
   - URL: `.../classes.html`
   - Parse all class names and URLs
   - Expected: 1,100+ classes

2. **Concurrent class page scraping**
   - 50 concurrent HTTP requests (async)
   - Estimated time: ~15-20 seconds for all 1,100 classes
   - Single page fetch: ~0.38 seconds

3. **Parse Doxygen HTML** (per class page)
   - Extract: class name, namespace, description, parent class
   - Extract: all public methods
   - Extract: method signatures, return types, parameters, descriptions
   - Extract: links to related classes

4. **Build SQLite database**
   - Insert classes
   - Insert methods with foreign keys
   - Insert parameters
   - Build FTS5 full-text search index
   - Add metadata (version, scraped_at, source_url)

5. **Validate**
   - Check total class count (should be ~1,100)
   - Check average methods per class (should be ~25-30)
   - Spot-check known classes (Model, ThermalZone, AirLoopHVAC)

### HTML Parsing Patterns

**Class page structure:**
```html
<div class="title">openstudio::model::ThermalZone Class Reference</div>
<div class="textblock">
  <p>ThermalZone is a ModelObject...</p>
</div>
<h2>Public Member Functions</h2>
<table class="memberdecls">
  <tr>
    <td class="memItemLeft">bool</td>
    <td class="memItemRight">setName(const std::string&amp; name)</td>
  </tr>
</table>
```

**Extraction logic:**
```python
from bs4 import BeautifulSoup

soup = BeautifulSoup(html, 'lxml')

# Class name and namespace
title = soup.find('div', class_='title').text
# Parse: "openstudio::model::ThermalZone Class Reference"

# Description
description = soup.find('div', class_='textblock').find('p').text

# Methods
methods_table = soup.find('table', class_='memberdecls')
for row in methods_table.find_all('tr'):
    return_type = row.find('td', class_='memItemLeft').text.strip()
    signature = row.find('td', class_='memItemRight').text.strip()
    # Parse signature to extract name and parameters
```

---

## Implementation Phases

### Phase 1: Scraper + SQLite Database (4-6 hours)

**Tasks:**
1. Create `scrapers/openstudio_docs_scraper.py`
   - Async HTTP client (httpx)
   - Fetch class list from `classes.html`
   - Concurrent scraping (50 parallel)
   - BeautifulSoup4 + lxml parsing
   - Progress bar (rich)

2. Create `scrapers/db_builder.py`
   - SQLite database creation
   - Schema definition
   - Insert classes, methods, parameters
   - Build FTS5 index
   - Validation checks

3. Run initial scrape
   - Scrape all 1,100+ classes
   - Build `openstudio-3.9.0.db`
   - Verify database size (5-8 MB)
   - Commit database to repo

**Deliverable:** `src/bluesky/mcp/data/openstudio-3.9.0.db` (ready to ship)

---

### Phase 2: MCP Server Infrastructure (2-3 hours)

**Tasks:**
1. Create `openstudio_server.py`
   - FastMCP server setup
   - Database connection management
   - Hybrid caching logic (shipped DB + auto-refresh)

2. Create `utils/cpp_to_python.py`
   - C++ → Python name mapping
   - C++ → Ruby name mapping
   - Type conversion helpers

3. Implement caching strategy
   ```python
   def get_database():
       shipped = Path("data/openstudio-3.9.0.db")
       cache = Path.home() / ".cache/bluesky/openstudio-3.9.0.db"

       if cache.exists() and age(cache) < timedelta(days=30):
           return cache

       if shipped.exists():
           if age(shipped) > timedelta(days=30):
               asyncio.create_task(refresh_database())
           return shipped

       return scrape_and_build_database()
   ```

**Deliverable:** Working MCP server that loads database and responds to ping

---

### Phase 3: SDK Query Tools (3-4 hours)

**Tasks:**
1. Implement `tools/sdk_query.py`
   - `query_openstudio_classes` (SQL: LIKE with regex)
   - `get_class_methods` (SQL: JOIN classes/methods)
   - `get_method_details` (SQL: JOIN with parameters)
   - `search_sdk_documentation` (FTS5 full-text search)

2. Add C++ → Python/Ruby translation
   - Map class names: `openstudio::model::Model` → `openstudio.model.Model`
   - Map types: `boost::optional<Building>` → `Optional[Building]`

3. Write tests
   - Test each tool with known classes/methods
   - Verify results accuracy

**Deliverable:** 4 SDK query tools working and tested

---

### Phase 4: Ruby Gem Tools (2-3 hours)

**Tasks:**
1. Implement `utils/ruby_searcher.py`
   - Locate vendor gems path
   - Ripgrep wrapper (`rg` subprocess)
   - Parse ripgrep output

2. Implement `tools/ruby_gems.py`
   - `search_ruby_gem_code` (ripgrep search)
   - `get_ruby_gem_structure` (os.walk)
   - `read_ruby_source_file` (open file)
   - `find_ruby_examples` (semantic search + ripgrep)

3. Write tests
   - Test with known gems (openstudio-standards)
   - Verify search results

**Deliverable:** 4 Ruby gem tools working

---

### Phase 5: Code Generation + Polish (3-4 hours)

**Tasks:**
1. Create `utils/code_templates.py`
   - Template patterns for common operations
   - Use validated examples from `/workspaces/bluesky/examples/`

2. Implement `tools/code_generation.py`
   - `generate_python_example`
   - `generate_ruby_example`
   - `compare_python_ruby`

3. CLI integration
   - Add `bluesky mcp-server` command
   - Add `bluesky refresh-openstudio-docs` command
   - Add `--refresh-docs` flag

4. Create `.mcp.json` configuration

5. Write documentation
   - Update `/docs/README.md`
   - Add usage examples
   - Add troubleshooting guide

6. Write tests
   - Test code generation quality
   - Test CLI commands

**Deliverable:** Complete MCP server ready for use

---

### Phase 6 (Optional): Polish + Performance (2-3 hours)

**Tasks:**
- Add caching for frequent queries
- Optimize database queries (analyze with EXPLAIN)
- Add telemetry (usage tracking)
- Performance benchmarking
- Error handling improvements

---

## Dependencies

### Add to `pyproject.toml`

```toml
dependencies = [
    # ... existing dependencies ...

    # MCP Server
    "fastmcp>=2.13.0",           # MCP server framework

    # Scraping
    "httpx>=0.27.0",             # Async HTTP client
    "beautifulsoup4>=4.12.0",    # HTML parsing
    "lxml>=5.0.0",               # Fast XML/HTML parser
]
```

### System Dependencies (already available)

- Python 3.12 ✅ (already in devcontainer)
- Ruby 3.2.2 ✅ (already installed via rbenv)
- Vendor gems ✅ (already in `/workspaces/bluesky/vendor/`)
- ripgrep ✅ (available in devcontainer)

---

## Configuration

### `.mcp.json` (create at repo root)

```json
{
  "mcpServers": {
    "openstudio": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "-m",
        "bluesky.mcp.openstudio_server"
      ],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src",
        "OPENSTUDIO_GEM_PATH": "${workspaceFolder}/vendor/bundle/ruby/3.2.0/bundler/gems"
      }
    }
  }
}
```

### CLI Commands

```bash
# Start MCP server (uses shipped database)
bluesky mcp-server

# Start with forced refresh
bluesky mcp-server --refresh-docs

# Manually refresh documentation (standalone)
bluesky refresh-openstudio-docs
```

---

## Future Extensibility

The MCP server is designed to be extensible. Future additions could include:

### Additional Documentation Sources

**Building Codes:**
- NECB 2015, 2017, 2020 (PDF extraction)
- ASHRAE 90.1 (2004-2022)
- International Energy Conservation Code (IECC)

**Software Documentation:**
- EnergyPlus I/O Reference (HTML scrape)
- Hot2000 user manual (PDF extraction)
- OpenStudio Measure Writing Guide

**Reference Data:**
- Climate data (TMY, CWEC weather files)
- Material libraries (LBNL, NREL)
- Equipment catalogs

### Multi-Database Architecture

```
src/bluesky/mcp/data/
├── openstudio-3.9.0.db          # OpenStudio SDK (Phase 1)
├── necb-2020.db                 # NECB building code (Future)
├── ashrae-90.1-2019.db          # ASHRAE standard (Future)
├── energyplus-24.2.0.db         # EnergyPlus docs (Future)
└── hot2000-manual.db            # Hot2000 manual (Future)
```

### Additional MCP Tools (Future)

**NECB tools:**
- `query_necb_requirement(section, building_type)`
- `get_necb_table(table_number)`
- `check_necb_compliance(building_params)`
- `get_necb_climate_zone(location)`
- `get_necb_envelope_requirements(zone, building_type)`

**ASHRAE tools:**
- `query_ashrae_standard(standard, section)`
- `get_ashrae_climate_zone(location)`
- `compare_standards(standard1, standard2, requirement)`

**Cross-database search:**
- `search_all_documentation(query)` - Search across all databases

### Implementation Strategy

1. ✅ **Phase 1-5:** OpenStudio SDK MCP server (proven value, clear scope)
2. **Evaluate:** User feedback, usage metrics
3. **Phase 6+:** Add NECB/ASHRAE/others based on:
   - User demand
   - Data availability (can we scrape/parse?)
   - Maintenance burden (update frequency?)

---

## Testing Strategy

### Unit Tests

```
tests/unit/mcp/
├── test_scraper.py                   # Test scraping logic
├── test_db_builder.py                # Test database creation
├── test_sdk_query_tools.py           # Test SDK query tools
├── test_ruby_gem_tools.py            # Test Ruby gem search
└── test_code_generation.py           # Test code generation
```

### Integration Tests

```
tests/integration/mcp/
├── test_mcp_server.py                # Test full MCP server
├── test_database_queries.py          # Test complex queries
└── test_code_generation_quality.py   # Verify generated code runs
```

### Test Data

- Use known OpenStudio classes for validation (Model, ThermalZone, AirLoopHVAC)
- Use known Ruby gem files (openstudio-standards/lib/openstudio-standards/geometry/create_shape.rb)
- Validate generated code by actually running it (requires openstudio)

---

## Success Criteria

The MCP server is considered successful when:

1. ✅ **Fast startup:** <1 second (uses shipped database)
2. ✅ **Complete coverage:** All 1,100+ OpenStudio classes queryable
3. ✅ **Accurate results:** SDK queries return correct methods/parameters
4. ✅ **Fast queries:** <100ms for typical queries
5. ✅ **Ruby gem search:** Can find code in all vendor gems
6. ✅ **Code generation:** Generated code is syntactically correct
7. ✅ **Auto-refresh:** Background refresh works (non-blocking)
8. ✅ **Offline mode:** Works without internet (uses shipped DB)
9. ✅ **Extensible:** Easy to add new documentation sources
10. ✅ **Well-tested:** >80% test coverage

---

## Risks and Mitigations

### Risk 1: S3 Documentation Structure Changes
**Impact:** Scraper breaks if HTML structure changes
**Likelihood:** Low (Doxygen output is stable)
**Mitigation:**
- Version-specific scraping (tied to OpenStudio 3.9.0)
- Add schema validation after parsing
- Manual testing before releases

### Risk 2: Database Size Too Large
**Impact:** Database >50 MB, GitHub warnings
**Likelihood:** Low (estimated 5-8 MB)
**Mitigation:**
- Use SQLite page compression
- Exclude less important data (example code, related links)
- Can split into multiple DBs if needed

### Risk 3: Code Generation Quality Poor
**Impact:** Generated code doesn't work or has bugs
**Likelihood:** Medium (hard to generate perfect code)
**Mitigation:**
- Template-based generation (not LLM-generated during runtime)
- Use validated examples from `/workspaces/bluesky/examples/`
- Integration tests that run generated code
- Include "experimental" warning in tool description

### Risk 4: Slow Queries
**Impact:** MCP tools take >1 second to respond
**Likelihood:** Low (SQLite with indexes is fast)
**Mitigation:**
- Proper database indexes
- Query result caching
- EXPLAIN QUERY PLAN analysis
- Lazy loading (don't load all results at once)

---

## Open Questions

1. **Should we include EnergyPlus IDD documentation?**
   - Pro: Complete picture of simulation objects
   - Con: Large additional dataset (~5,000 objects)
   - Decision: Phase 2 if needed

2. **Should code generation use templates or LLM calls?**
   - Templates: Fast, predictable, but limited variety
   - LLM calls: Flexible, but slower and requires API key
   - Decision: Start with templates, add LLM option later

3. **Should we cache Ruby gem search results?**
   - Pro: Faster repeated searches
   - Con: Complexity, cache invalidation
   - Decision: Implement if performance testing shows need

---

## Timeline

### Minimal Viable Product (MVP)
**Phases 1-3:** SDK scraper + MCP server + SDK query tools
**Time:** 9-13 hours
**Deliverable:** Can query OpenStudio classes/methods dynamically

### Full Feature Set
**Phases 1-5:** Add Ruby gem search + code generation
**Time:** 16-23 hours
**Deliverable:** Complete MCP server as designed

### Polish
**Phase 6:** Performance optimization, telemetry, docs
**Time:** +2-3 hours
**Deliverable:** Production-ready

---

## References

- OpenStudio SDK C++ Documentation: https://s3.amazonaws.com/openstudio-sdk-documentation/cpp/OpenStudio-3.9.0-doc/model/html/
- FastMCP Documentation: https://github.com/jlowin/fastmcp
- Model Context Protocol Specification: https://modelcontextprotocol.io/
- OpenStudio SDK: https://github.com/NREL/OpenStudio
- openstudio-standards gem: https://github.com/NREL/openstudio-standards

---

**End of Implementation Plan**
