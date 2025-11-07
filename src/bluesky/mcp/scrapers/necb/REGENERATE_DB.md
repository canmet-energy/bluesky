# Regenerating the NECB Database

This guide explains how to regenerate the NECB database after fixing the table parsing logic.

## What Was Fixed

**Problem:** The NECB PDF parser was using placeholder table numbers like "Table-51-6" instead of extracting the actual NECB table numbers like "Table 3.2.2.2."

**Solution:** Enhanced `necb_pdf_parser.py` with a new `_extract_table_metadata()` method that:
- Extracts actual NECB table numbers from page text using regex patterns
- Extracts table titles from the lines following the table number
- Falls back to the old numbering scheme if extraction fails

## Prerequisites

1. NECB PDF files must be available at `src/bluesky/mcp/scrapers/necb/pdfs/`:
   - `NECB-2011.pdf`
   - `NECB-2015.pdf`
   - `NECB-2017.pdf`
   - `NECB-2020.pdf`

2. Required Python packages (should already be installed):
   - `pdfplumber`
   - `rich`

## How to Regenerate

### Method 1: Using the main scraper script

```bash
cd /workspaces/bluesky
python -m bluesky.mcp.scrapers.necb.necb_db_builder
```

This will:
1. Parse all NECB PDFs in the `pdfs/` directory
2. Extract sections, tables (with proper numbering), and requirements
3. Build a new SQLite database at `src/bluesky/mcp/data/necb.db`

### Method 2: Step by step

```bash
cd /workspaces/bluesky

# 1. Parse PDFs
python -c "
from pathlib import Path
from bluesky.mcp.scrapers.necb.necb_pdf_parser import parse_all_necb_pdfs

pdf_dir = Path('src/bluesky/mcp/scrapers/necb/pdfs')
results = parse_all_necb_pdfs(pdf_dir)
print(f'Parsed {len(results)} vintages')
"

# 2. Build database
python -c "
from pathlib import Path
from bluesky.mcp.scrapers.necb.necb_db_builder import NECBDatabaseBuilder
from bluesky.mcp.scrapers.necb.necb_pdf_parser import parse_all_necb_pdfs

pdf_dir = Path('src/bluesky/mcp/scrapers/necb/pdfs')
db_path = Path('src/bluesky/mcp/data/necb.db')

# Parse PDFs
parsed_data = parse_all_necb_pdfs(pdf_dir)

# Build database
with NECBDatabaseBuilder(db_path) as builder:
    builder.create_schema()
    for vintage, data in parsed_data.items():
        builder.insert_vintage_data(vintage, data)
    builder.create_fts_index()

print(f'Database created at {db_path}')
"
```

## Verifying the Fix

After regeneration, test that tables are queryable by their NECB numbers:

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('src/bluesky/mcp/data/necb.db')
cursor = conn.cursor()

# Check for Table 3.2.2.2
cursor.execute(\"SELECT table_number, title FROM necb_tables WHERE vintage='2011' AND table_number LIKE '%3.2.2.2%'\")
result = cursor.fetchone()

if result:
    print(f'✓ Found: {result[0]} - {result[1]}')
else:
    print('✗ Table 3.2.2.2 not found')

# List first 10 tables to verify format
cursor.execute(\"SELECT table_number, title FROM necb_tables WHERE vintage='2011' ORDER BY table_number LIMIT 10\")
print('\\nFirst 10 tables:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1][:60]}')
"
```

Expected output:
```
✓ Found: Table 3.2.2.2. - Overall Thermal Transmittance of Above-ground Opaque Building Assemblies

First 10 tables:
  Table 3.2.1.3.: ...
  Table 3.2.2.2.: Overall Thermal Transmittance of Above-ground Opaque Building Assemblies
  Table 3.2.2.4.: ...
  ...
```

## Testing with MCP Server

After regeneration, test the MCP server queries:

```python
from bluesky.mcp import openstudio_server

# Test get_necb_table with proper NECB number
result = openstudio_server.get_necb_table(vintage="2011", table_number="Table 3.2.2.2.")

if result:
    print(f"Table found: {result['title']}")
    print(f"Headers: {result['headers'][:3]}")
    print(f"First row: {result['rows'][0]}")
else:
    print("Table not found")
```

## Backup

Before regenerating, backup the existing database:

```bash
cp src/bluesky/mcp/data/necb.db src/bluesky/mcp/data/necb.db.backup
```

## Troubleshooting

**Issue:** PDFs not found
**Solution:** Download NECB PDFs from NRC and place them in `src/bluesky/mcp/scrapers/necb/pdfs/`

**Issue:** Parsing fails on specific table
**Solution:** Check `necb_pdf_parser.py` regex patterns in `_extract_table_metadata()`. The pattern may need adjustment for edge cases.

**Issue:** Some tables still have generic numbers
**Solution:** This is expected for tables that don't follow the standard "Table X.X.X.X." pattern. The parser falls back to page-based numbering for these cases.

## Additional Notes

- The fix maintains backward compatibility - the MCP server's `get_necb_table()` function supports both old "Table-51-6" style and new "Table 3.2.2.2." style lookups
- Section content still contains embedded table text (this is correct - it preserves the full section)
- The FTS search index is regenerated automatically with proper table titles
