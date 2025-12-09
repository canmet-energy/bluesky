# NECB Database Build

Build the NECB SQLite database from PDF source documents.

## Prerequisites

1. Place PDF files in project root `data/necb/pdfs/`:
   ```
   data/necb/pdfs/
   ├── NECB-2011.pdf
   ├── NECB-2015.pdf
   ├── NECB-2017.pdf
   └── NECB-2020.pdf
   ```

2. Set `ANTHROPIC_API_KEY` environment variable (for Claude backend)

## Quick Start

```bash
# Build everything (sections + tables + figures)
python -m bluesky.necb.build all --backend claude --vintages 2020

# Check status
python -m bluesky.necb.build status
```

## Step-by-Step Build

```bash
# 1. Parse sections (fast, no LLM required)
python -m bluesky.necb.build sections --vintages 2020

# 2. Parse tables (slow, requires LLM for repair)
python -m bluesky.necb.build tables --backend claude --vintages 2020

# 3. Enrich figures with AI descriptions (uses existing cropped PNGs)
python -m bluesky.necb.build figures --vintage 2020 --enrich

# 4. Build semantic search index
python -m bluesky.necb.build index --vintages 2020
```

## Output

- **Database:** `src/bluesky/necb/data/necb_production.db`
- **Vector Index:** `src/bluesky/necb/data/chroma/`

## Options

| Flag | Description |
|------|-------------|
| `--backend claude\|ollama` | LLM backend for table repair |
| `--vintages 2011 2015 2017 2020` | Select specific vintages |
| `--tables 3.2.2.2 8.4.4.10` | Parse specific tables only |
| `--skip-successful` | Incremental build (skip existing) |
| `--dry-run` | Preview without parsing |

## Data Flow

```
PDFs → table-specs-*.json → tables parser → necb_tables
                         → sections parser → necb_sections
                         → figures enricher → necb_figures
                                           → ChromaDB index
```
