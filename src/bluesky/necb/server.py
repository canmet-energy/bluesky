"""
NECB MCP Server

Provides access to NECB (National Energy Code of Canada for Buildings) documentation
across multiple vintages (2011, 2015, 2017, 2020).

Features:
- Article/section queries with full text and sentences
- Table queries with normalized table number handling
- Figure queries with AI-generated descriptions
- Full-text keyword search across all NECB content
- Semantic search using natural language queries (requires ChromaDB index)
"""

import json
import re
import sqlite3
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

from bluesky.necb import DB_PATH

# Initialize MCP server
mcp = FastMCP("necb")

# Database path
NECB_DB_PATH = DB_PATH

# Valid vintages
VALID_VINTAGES = {"2011", "2015", "2017", "2020"}

# Singleton for semantic search engine (lazy-loaded for performance)
_search_engine = None
_query_understanding = None


def get_necb_database_connection() -> sqlite3.Connection:
    """Get a connection to the NECB documentation database"""
    if not NECB_DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {NECB_DB_PATH}")

    conn = sqlite3.connect(NECB_DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


def validate_vintage(vintage: str) -> str:
    """Validate and normalize vintage string"""
    vintage = str(vintage).strip()
    if vintage not in VALID_VINTAGES:
        raise ValueError(f"Invalid vintage '{vintage}'. Valid values: {sorted(VALID_VINTAGES)}")
    return vintage


# =============================================================================
# Article/Section Tools
# =============================================================================


@mcp.tool()
def query_necb_sections(
    vintage: str = "2020",
    article_pattern: Optional[str] = None,
    division: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """
    Search NECB sections/articles by vintage, article number pattern, division, or keyword.

    Args:
        vintage: NECB vintage ("2011", "2015", "2017", "2020") - default: "2020"
        article_pattern: Article number pattern using SQL LIKE syntax
            Examples: "3.2.%" matches all 3.2.x articles, "3.2.2.2" exact match
        division: Filter by NECB division ("A", "B", "C", "D")
        keyword: Search keyword in article text
        limit: Maximum results (default: 20, max: 100)

    Returns:
        List of matching sections with article_number, title, content preview, page numbers
    """
    vintage = validate_vintage(vintage)
    limit = min(limit, 100)

    conn = get_necb_database_connection()
    cursor = conn.cursor()

    query = """
        SELECT article_number, title, full_text, page_start, page_end,
               hierarchy_level, division, reference
        FROM necb_articles
        WHERE vintage = ?
    """
    params: list = [vintage]

    if article_pattern:
        # Support both exact match and pattern
        if "%" in article_pattern:
            query += " AND article_number LIKE ?"
        else:
            query += " AND article_number LIKE ?"
            article_pattern = f"%{article_pattern}%"
        params.append(article_pattern)

    if division:
        query += " AND division = ?"
        params.append(division.upper())

    if keyword:
        query += " AND full_text LIKE ?"
        params.append(f"%{keyword}%")

    query += " ORDER BY article_number LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    results = []

    for row in cursor.fetchall():
        results.append({
            "vintage": vintage,
            "article_number": row["article_number"],
            "reference": row["reference"],
            "title": row["title"],
            "division": row["division"],
            "hierarchy_level": row["hierarchy_level"],
            "content": row["full_text"][:500] + "..." if row["full_text"] and len(row["full_text"]) > 500 else row["full_text"],
            "page_start": row["page_start"],
            "page_end": row["page_end"],
        })

    conn.close()
    return results


@mcp.tool()
def get_necb_article(
    article_number: str,
    vintage: str = "2020",
    include_sentences: bool = True,
) -> Optional[dict]:
    """
    Get a specific NECB article by exact article number, with optional sentence details.

    Args:
        article_number: Exact article number (e.g., "3.2.2.2", "4.3.1.1")
        vintage: NECB vintage ("2011", "2015", "2017", "2020") - default: "2020"
        include_sentences: Include sentence-level breakdown with clauses (default: True)

    Returns:
        Article with full text, metadata, and optionally sentences with clause structure
    """
    vintage = validate_vintage(vintage)

    conn = get_necb_database_connection()
    cursor = conn.cursor()

    # Get article
    cursor.execute(
        """
        SELECT id, article_number, title, full_text, page_start, page_end,
               hierarchy_level, division, reference, part_number, section_number
        FROM necb_articles
        WHERE vintage = ? AND article_number = ?
        LIMIT 1
        """,
        (vintage, article_number),
    )

    article_row = cursor.fetchone()
    if not article_row:
        conn.close()
        return None

    result = {
        "vintage": vintage,
        "article_number": article_row["article_number"],
        "reference": article_row["reference"],
        "title": article_row["title"],
        "division": article_row["division"],
        "hierarchy_level": article_row["hierarchy_level"],
        "part_number": article_row["part_number"],
        "section_number": article_row["section_number"],
        "full_text": article_row["full_text"],
        "page_start": article_row["page_start"],
        "page_end": article_row["page_end"],
    }

    if include_sentences:
        cursor.execute(
            """
            SELECT sentence_number, reference, sentence_text, clauses_json
            FROM necb_sentences
            WHERE article_id = ?
            ORDER BY sentence_number
            """,
            (article_row["id"],),
        )

        sentences = []
        for sent_row in cursor.fetchall():
            sentence = {
                "sentence_number": sent_row["sentence_number"],
                "reference": sent_row["reference"],
                "text": sent_row["sentence_text"],
            }
            if sent_row["clauses_json"]:
                sentence["clauses"] = json.loads(sent_row["clauses_json"])
            sentences.append(sentence)

        result["sentences"] = sentences

    conn.close()
    return result


# =============================================================================
# Table Tools
# =============================================================================


@mcp.tool()
def get_necb_table(
    table_number: str,
    vintage: str = "2020",
) -> Optional[dict]:
    """
    Get a specific NECB table with all rows.

    Args:
        table_number: Table number - accepts multiple formats:
            - "3.2.2.2" → normalized to "3.2.2.2"
            - "Table 3.2.2.2" → normalized to "3.2.2.2"
            - "8.4.4.21.-G" → used as-is (letter suffix tables)
        vintage: NECB vintage ("2011", "2015", "2017", "2020") - default: "2020"

    Returns:
        Table details with headers and all data rows, or None if not found
    """
    vintage = validate_vintage(vintage)

    conn = get_necb_database_connection()
    cursor = conn.cursor()

    # Normalize table number
    normalized = table_number.strip()
    if normalized.lower().startswith("table "):
        normalized = normalized[6:]
    # Remove trailing period unless it's a letter suffix
    if normalized.endswith(".") and not re.search(r'\.-[A-Z]$', normalized):
        normalized = normalized.rstrip(".")

    # Try exact match first
    cursor.execute(
        """
        SELECT id, table_number, title, headers, page_number, division
        FROM necb_tables
        WHERE vintage = ? AND table_number = ?
        LIMIT 1
        """,
        (vintage, normalized),
    )

    table_row = cursor.fetchone()

    # If not found, try partial match
    if not table_row:
        cursor.execute(
            """
            SELECT id, table_number, title, headers, page_number, division
            FROM necb_tables
            WHERE vintage = ? AND table_number LIKE ?
            LIMIT 1
            """,
            (vintage, f"%{normalized}%"),
        )
        table_row = cursor.fetchone()

    if not table_row:
        conn.close()
        return None

    table_id = table_row["id"]
    headers = json.loads(table_row["headers"]) if table_row["headers"] else []

    # Get table rows
    cursor.execute(
        """
        SELECT row_data
        FROM necb_table_rows
        WHERE table_id = ?
        """,
        (table_id,),
    )

    rows = []
    for row in cursor.fetchall():
        rows.append(json.loads(row["row_data"]))

    conn.close()

    return {
        "vintage": vintage,
        "table_number": table_row["table_number"],
        "title": table_row["title"],
        "division": table_row["division"],
        "headers": headers,
        "rows": rows,
        "row_count": len(rows),
        "page_number": table_row["page_number"],
    }


@mcp.tool()
def list_necb_tables(
    vintage: str = "2020",
    division: Optional[str] = None,
) -> list[dict]:
    """
    List all NECB tables for a vintage, useful for discovering available tables.

    Args:
        vintage: NECB vintage ("2011", "2015", "2017", "2020") - default: "2020"
        division: Filter by NECB division ("A", "B", "C", "D")

    Returns:
        List of tables with table_number, title, and row count
    """
    vintage = validate_vintage(vintage)

    conn = get_necb_database_connection()
    cursor = conn.cursor()

    query = """
        SELECT t.id, t.table_number, t.title, t.page_number, t.division,
               COUNT(r.id) as row_count
        FROM necb_tables t
        LEFT JOIN necb_table_rows r ON t.id = r.table_id
        WHERE t.vintage = ?
    """
    params: list = [vintage]

    if division:
        query += " AND t.division = ?"
        params.append(division.upper())

    query += " GROUP BY t.id ORDER BY t.table_number"

    cursor.execute(query, params)

    results = []
    for row in cursor.fetchall():
        results.append({
            "vintage": vintage,
            "table_number": row["table_number"],
            "title": row["title"],
            "division": row["division"],
            "row_count": row["row_count"],
            "page_number": row["page_number"],
        })

    conn.close()
    return results


# =============================================================================
# Figure Tools
# =============================================================================


@mcp.tool()
def get_necb_figure(
    figure_label: str,
    vintage: str = "2020",
) -> Optional[dict]:
    """
    Get a specific NECB figure with its AI-generated description.

    Args:
        figure_label: Figure label (e.g., "Figure A-1.1.2.1", "Figure 1")
            Accepts with or without "Figure " prefix
        vintage: NECB vintage ("2011", "2015", "2017", "2020") - default: "2020"

    Returns:
        Figure details with label, caption, AI description, and image path
    """
    vintage = validate_vintage(vintage)

    conn = get_necb_database_connection()
    cursor = conn.cursor()

    # Normalize figure label
    normalized = figure_label.strip()
    if not normalized.lower().startswith("figure "):
        normalized = f"Figure {normalized}"

    cursor.execute(
        """
        SELECT label, caption, page, ai_description, image_path,
               image_type, width, height, division
        FROM necb_figures
        WHERE vintage = ? AND label = ?
        LIMIT 1
        """,
        (vintage, normalized),
    )

    row = cursor.fetchone()

    # Try partial match if not found
    if not row:
        cursor.execute(
            """
            SELECT label, caption, page, ai_description, image_path,
                   image_type, width, height, division
            FROM necb_figures
            WHERE vintage = ? AND label LIKE ?
            LIMIT 1
            """,
            (vintage, f"%{figure_label}%"),
        )
        row = cursor.fetchone()

    conn.close()

    if not row:
        return None

    return {
        "vintage": vintage,
        "label": row["label"],
        "caption": row["caption"],
        "page": row["page"],
        "division": row["division"],
        "ai_description": row["ai_description"],
        "image_path": row["image_path"],
        "image_type": row["image_type"],
        "dimensions": {"width": row["width"], "height": row["height"]},
    }


@mcp.tool()
def list_necb_figures(
    vintage: str = "2020",
    division: Optional[str] = None,
) -> list[dict]:
    """
    List all NECB figures for a vintage.

    Args:
        vintage: NECB vintage ("2011", "2015", "2017", "2020") - default: "2020"
        division: Filter by NECB division ("A", "B", "C", "D")

    Returns:
        List of figures with labels, captions, and page numbers
    """
    vintage = validate_vintage(vintage)

    conn = get_necb_database_connection()
    cursor = conn.cursor()

    query = """
        SELECT label, caption, page, division, image_type
        FROM necb_figures
        WHERE vintage = ?
    """
    params: list = [vintage]

    if division:
        query += " AND division = ?"
        params.append(division.upper())

    query += " ORDER BY label"

    cursor.execute(query, params)

    results = []
    for row in cursor.fetchall():
        results.append({
            "vintage": vintage,
            "label": row["label"],
            "caption": row["caption"],
            "page": row["page"],
            "division": row["division"],
            "image_type": row["image_type"],
        })

    conn.close()
    return results


# =============================================================================
# Search Tools
# =============================================================================


@mcp.tool()
def search_necb(
    query: str,
    vintage: Optional[str] = "2020",
    content_types: Optional[list[str]] = None,
    limit: int = 20,
) -> list[dict]:
    """
    Keyword search across all NECB content (articles, tables, figures).

    Uses SQL LIKE queries for keyword matching. For natural language queries,
    use semantic_search_necb() instead.

    Args:
        query: Search keywords (searches in article text, table titles, figure captions)
        vintage: Filter by vintage ("2011", "2015", "2017", "2020") - default: "2020"
        content_types: Filter by content types (["articles", "tables", "figures"])
            Default: searches all types
        limit: Maximum results per content type (default: 20, max: 50)

    Returns:
        List of search results with type, content preview, and location info
    """
    if vintage:
        vintage = validate_vintage(vintage)
    limit = min(limit, 50)

    if not content_types:
        content_types = ["articles", "tables", "figures"]

    results = []
    conn = get_necb_database_connection()
    cursor = conn.cursor()

    search_term = f"%{query}%"

    # Search articles
    if "articles" in content_types:
        article_query = """
            SELECT article_number, title, full_text, page_start, division, vintage
            FROM necb_articles
            WHERE full_text LIKE ?
        """
        params: list = [search_term]

        if vintage:
            article_query += " AND vintage = ?"
            params.append(vintage)

        article_query += " ORDER BY article_number LIMIT ?"
        params.append(limit)

        cursor.execute(article_query, params)

        for row in cursor.fetchall():
            # Find snippet around the match
            text = row["full_text"] or ""
            match_pos = text.lower().find(query.lower())
            if match_pos >= 0:
                start = max(0, match_pos - 50)
                end = min(len(text), match_pos + len(query) + 100)
                snippet = text[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(text):
                    snippet = snippet + "..."
            else:
                snippet = text[:150] + "..." if len(text) > 150 else text

            results.append({
                "type": "article",
                "vintage": row["vintage"],
                "reference": row["article_number"],
                "title": row["title"],
                "division": row["division"],
                "snippet": snippet,
                "page": row["page_start"],
            })

    # Search tables
    if "tables" in content_types:
        table_query = """
            SELECT table_number, title, page_number, division, vintage
            FROM necb_tables
            WHERE title LIKE ?
        """
        params = [search_term]

        if vintage:
            table_query += " AND vintage = ?"
            params.append(vintage)

        table_query += " ORDER BY table_number LIMIT ?"
        params.append(limit)

        cursor.execute(table_query, params)

        for row in cursor.fetchall():
            results.append({
                "type": "table",
                "vintage": row["vintage"],
                "reference": row["table_number"],
                "title": row["title"],
                "division": row["division"],
                "snippet": row["title"],
                "page": row["page_number"],
            })

    # Search figures
    if "figures" in content_types:
        figure_query = """
            SELECT label, caption, page, division, vintage, ai_description
            FROM necb_figures
            WHERE caption LIKE ? OR ai_description LIKE ?
        """
        params = [search_term, search_term]

        if vintage:
            figure_query += " AND vintage = ?"
            params.append(vintage)

        figure_query += " ORDER BY label LIMIT ?"
        params.append(limit)

        cursor.execute(figure_query, params)

        for row in cursor.fetchall():
            results.append({
                "type": "figure",
                "vintage": row["vintage"],
                "reference": row["label"],
                "title": row["caption"],
                "division": row["division"],
                "snippet": row["caption"] or (row["ai_description"][:150] + "..." if row["ai_description"] and len(row["ai_description"]) > 150 else row["ai_description"]),
                "page": row["page"],
            })

    conn.close()
    return results


@mcp.tool()
def semantic_search_necb(
    query: str,
    vintage: str = "2020",
    top_k: int = 5,
    use_query_understanding: bool = True,
) -> list[dict]:
    """
    Natural language semantic search for NECB content.

    Combines entity extraction, query expansion, and hybrid keyword+semantic search
    to find relevant NECB content from natural language queries.

    Requires ChromaDB vector index to be built first:
        python -m bluesky.necb.tools.vector_indexer

    Examples:
        "What's the max window area for a 3-story office in Calgary?"
        "Thermal transmittance requirements for walls in cold climate"
        "Lighting power density for school classrooms in Toronto"
        "R-value for roofs in Vancouver NECB 2020"

    Args:
        query: Natural language query about NECB requirements
        vintage: NECB vintage (2011, 2015, 2017, 2020) - default: 2020
        top_k: Number of results to return (default: 5, max: 20)
        use_query_understanding: Enable entity extraction and query expansion (default: True)

    Returns:
        List of search results with:
        - content: Full text of section/table
        - vintage: NECB vintage
        - type: "section" or "table"
        - title: Section/table title
        - page_number: Page in PDF
        - section_number/table_number: Reference number
        - rrf_score: Relevance score (higher = more relevant)
        - extracted_entities: Detected location, building type, concepts (if query understanding enabled)
    """
    vintage = validate_vintage(vintage)
    top_k = min(top_k, 20)

    global _search_engine, _query_understanding

    try:
        from bluesky.necb import CHROMA_PATH
        from bluesky.necb.tools.hybrid_search import NECBHybridSearchEngine
        from bluesky.necb.tools.query_understanding import NECBQueryUnderstanding
    except ImportError as e:
        return [{
            "error": "Missing dependencies",
            "message": f"Required module not found: {e}",
            "fallback": "Use search_necb() for keyword-only search"
        }]

    # Check if semantic search is available
    if not CHROMA_PATH.exists():
        return [{
            "error": "Semantic search not initialized",
            "message": "Run: python -m bluesky.necb.tools.vector_indexer to build the vector index",
            "fallback": "Use search_necb() for keyword-only search"
        }]

    try:
        # Use singleton for search engine (lazy initialization)
        # This makes subsequent calls ~5-10x faster by avoiding model reload
        if _search_engine is None:
            _search_engine = NECBHybridSearchEngine(
                db_path=NECB_DB_PATH,
                chroma_path=CHROMA_PATH
            )
        search_engine = _search_engine
    except Exception as e:
        return [{
            "error": "Failed to initialize search engine",
            "message": str(e),
            "fallback": "Use search_necb() for keyword-only search"
        }]

    # Query understanding (optional, also uses singleton)
    entities = None
    search_query = query

    if use_query_understanding:
        if _query_understanding is None:
            _query_understanding = NECBQueryUnderstanding()
        query_engine = _query_understanding
        entities = query_engine.understand_query(query)

        # Build focused query from extracted concepts
        if entities.concepts:
            main_concept = entities.concepts[0]
            necb_terms = query_engine.concept_synonyms.get(main_concept, [])
            search_terms = [main_concept]
            if necb_terms:
                search_terms.extend(necb_terms[:2])
            search_query = " ".join(search_terms)

    # Perform hybrid search
    results = search_engine.search(
        query=search_query,
        vintage=vintage,
        top_k=top_k
    )

    # Format results
    formatted_results = []
    for result in results:
        formatted = {
            "content": result.content[:500] + "..." if len(result.content) > 500 else result.content,
            "vintage": result.vintage,
            "type": result.content_type,
            "title": result.title,
            "page_number": result.page_number,
            "rrf_score": round(result.rrf_score, 4) if result.rrf_score else None,
        }

        if result.section_number:
            formatted["section_number"] = result.section_number
        if result.table_number:
            formatted["table_number"] = result.table_number

        if result.fts_rank:
            formatted["keyword_rank"] = result.fts_rank
        if result.semantic_rank:
            formatted["semantic_rank"] = result.semantic_rank
            formatted["semantic_distance"] = round(result.semantic_distance, 4) if result.semantic_distance else None

        if entities:
            formatted["extracted_entities"] = {
                "location": entities.location,
                "climate_zone": entities.climate_zone,
                "hdd": entities.hdd,
                "building_type": entities.building_type,
                "concepts": entities.concepts,
                "vintage": entities.vintage,
                "confidence": round(entities.confidence, 2),
            }

        formatted_results.append(formatted)

    return formatted_results


# =============================================================================
# Metadata Tools
# =============================================================================


@mcp.tool()
def get_necb_stats(vintage: str = "2020") -> dict:
    """
    Get statistics about NECB content for a vintage.

    Args:
        vintage: NECB vintage ("2011", "2015", "2017", "2020") - default: "2020"

    Returns:
        Dictionary with counts of articles, sentences, tables, rows, and figures
    """
    vintage = validate_vintage(vintage)

    conn = get_necb_database_connection()
    cursor = conn.cursor()

    stats = {"vintage": vintage}

    # Count articles
    cursor.execute(
        "SELECT COUNT(*) as count FROM necb_articles WHERE vintage = ?",
        (vintage,),
    )
    stats["articles"] = cursor.fetchone()["count"]

    # Count sentences
    cursor.execute(
        """
        SELECT COUNT(*) as count FROM necb_sentences s
        JOIN necb_articles a ON s.article_id = a.id
        WHERE a.vintage = ?
        """,
        (vintage,),
    )
    stats["sentences"] = cursor.fetchone()["count"]

    # Count tables
    cursor.execute(
        "SELECT COUNT(*) as count FROM necb_tables WHERE vintage = ?",
        (vintage,),
    )
    stats["tables"] = cursor.fetchone()["count"]

    # Count table rows
    cursor.execute(
        """
        SELECT COUNT(*) as count FROM necb_table_rows r
        JOIN necb_tables t ON r.table_id = t.id
        WHERE t.vintage = ?
        """,
        (vintage,),
    )
    stats["table_rows"] = cursor.fetchone()["count"]

    # Count figures
    cursor.execute(
        "SELECT COUNT(*) as count FROM necb_figures WHERE vintage = ?",
        (vintage,),
    )
    stats["figures"] = cursor.fetchone()["count"]

    # Count index entries (if table exists)
    try:
        cursor.execute(
            "SELECT COUNT(*) as count FROM necb_index WHERE vintage = ?",
            (vintage,),
        )
        stats["index_entries"] = cursor.fetchone()["count"]
    except Exception:
        stats["index_entries"] = 0

    conn.close()
    return stats


# =============================================================================
# Index Tools (Fast Topic Lookups)
# =============================================================================


@mcp.tool()
def lookup_necb_index(
    term: str,
    vintage: str = "2020",
    include_children: bool = True,
) -> list[dict]:
    """
    Fast topic lookup using the NECB alphabetical index.

    Returns article references for a topic WITHOUT using semantic search.
    Much faster than semantic_search_necb() (~5ms vs ~3-5s) for known topics.

    Examples:
        lookup_necb_index("FDWR") -> articles 3.1.1.6, 3.2.1.4, 8.4.4.3
        lookup_necb_index("fenestration") -> all fenestration-related articles
        lookup_necb_index("boilers") -> all boiler requirements

    Args:
        term: Index term to look up (case-insensitive, partial match supported)
        vintage: NECB vintage (2020 currently supported)
        include_children: Include sub-term entries under this term (default: True)

    Returns:
        List of matching index entries with:
        - term: Main index term
        - description: Sub-term description (for child entries)
        - article_references: List of article numbers
        - see_also: Cross-reference to other terms
    """
    vintage = validate_vintage(vintage)

    conn = get_necb_database_connection()
    cursor = conn.cursor()

    results = []

    try:
        if include_children:
            # Get main term and all sub-entries
            cursor.execute(
                """
                SELECT term, parent_term, description, article_references,
                       division_hints, see_also, page
                FROM necb_index
                WHERE vintage = ?
                  AND (term LIKE ? COLLATE NOCASE OR parent_term LIKE ? COLLATE NOCASE)
                ORDER BY
                    CASE WHEN parent_term IS NULL THEN 0 ELSE 1 END,
                    term, description
                """,
                (vintage, f"%{term}%", f"%{term}%"),
            )
        else:
            # Only main terms
            cursor.execute(
                """
                SELECT term, parent_term, description, article_references,
                       division_hints, see_also, page
                FROM necb_index
                WHERE vintage = ? AND term LIKE ? COLLATE NOCASE AND parent_term IS NULL
                ORDER BY term
                """,
                (vintage, f"%{term}%"),
            )

        for row in cursor.fetchall():
            entry = {
                "term": row["term"],
                "description": row["description"],
                "article_references": json.loads(row["article_references"] or "[]"),
                "see_also": row["see_also"],
                "page": row["page"],
                "vintage": vintage,
            }

            # Add division hints if present
            hints = json.loads(row["division_hints"] or "[]")
            if hints:
                entry["division_hints"] = hints

            # Mark if this is a sub-entry
            if row["parent_term"]:
                entry["is_sub_entry"] = True
                entry["parent_term"] = row["parent_term"]

            results.append(entry)

    except Exception as e:
        # Table might not exist yet
        return [{"error": f"Index lookup failed: {e}"}]

    conn.close()
    return results


@mcp.tool()
def list_necb_index_terms(
    prefix: str = "",
    vintage: str = "2020",
    limit: int = 50,
) -> list[dict]:
    """
    List available index terms, optionally filtered by prefix.

    Useful for discovering what topics are indexed in NECB.

    Examples:
        list_necb_index_terms("fen") -> ["Fenestration", "Fenestration and door area..."]
        list_necb_index_terms("H") -> ["Heating", "HVAC", "Heat pumps", ...]
        list_necb_index_terms() -> All main terms (up to limit)

    Args:
        prefix: Optional prefix to filter terms (case-insensitive)
        vintage: NECB vintage (2020 currently supported)
        limit: Maximum results (default: 50)

    Returns:
        List of main index terms with sub-entry counts
    """
    vintage = validate_vintage(vintage)
    limit = min(limit, 200)

    conn = get_necb_database_connection()
    cursor = conn.cursor()

    results = []

    try:
        if prefix:
            cursor.execute(
                """
                SELECT term,
                       COUNT(CASE WHEN parent_term IS NOT NULL THEN 1 END) as sub_count,
                       GROUP_CONCAT(DISTINCT see_also) as see_also_refs
                FROM necb_index
                WHERE vintage = ? AND parent_term IS NULL
                  AND term LIKE ? COLLATE NOCASE
                GROUP BY term
                ORDER BY term
                LIMIT ?
                """,
                (vintage, f"{prefix}%", limit),
            )
        else:
            cursor.execute(
                """
                SELECT term,
                       COUNT(CASE WHEN parent_term IS NOT NULL THEN 1 END) as sub_count,
                       GROUP_CONCAT(DISTINCT see_also) as see_also_refs
                FROM necb_index
                WHERE vintage = ? AND parent_term IS NULL
                GROUP BY term
                ORDER BY term
                LIMIT ?
                """,
                (vintage, limit),
            )

        for row in cursor.fetchall():
            entry = {
                "term": row["term"],
                "vintage": vintage,
            }

            # Get sub-entry count from a separate query
            cursor.execute(
                """
                SELECT COUNT(*) as count FROM necb_index
                WHERE vintage = ? AND parent_term = ?
                """,
                (vintage, row["term"]),
            )
            sub_count = cursor.fetchone()["count"]
            if sub_count > 0:
                entry["sub_entries"] = sub_count

            if row["see_also_refs"]:
                entry["see_also"] = row["see_also_refs"]

            results.append(entry)

    except Exception as e:
        return [{"error": f"Index listing failed: {e}"}]

    conn.close()
    return results


if __name__ == "__main__":
    # Run the server
    mcp.run()
