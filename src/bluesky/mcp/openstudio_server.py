"""
OpenStudio MCP Server

Provides dynamic access to OpenStudio SDK documentation and Ruby gem source code.
"""

import json
import sqlite3
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("openstudio")

# Database paths
OPENSTUDIO_DB_PATH = Path(__file__).parent / "data" / "openstudio-3.9.0.db"
NECB_DB_PATH = Path(__file__).parent / "data" / "necb.db"


def get_database_connection() -> sqlite3.Connection:
    """Get a connection to the OpenStudio documentation database"""
    if not OPENSTUDIO_DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {OPENSTUDIO_DB_PATH}")

    conn = sqlite3.connect(OPENSTUDIO_DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


def get_necb_database_connection() -> sqlite3.Connection:
    """Get a connection to the NECB documentation database"""
    if not NECB_DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {NECB_DB_PATH}")

    conn = sqlite3.connect(NECB_DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


@mcp.tool()
def query_openstudio_classes(
    pattern: str,
    namespace: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """
    Search OpenStudio SDK for classes matching a pattern.

    Args:
        pattern: Regex pattern to match class names (e.g., ".*Zone.*", "Coil.*Heating.*")
        namespace: Filter by namespace (e.g., "openstudio::model")
        limit: Maximum results to return (default: 50)

    Returns:
        List of matching classes with name, namespace, description, and doc URL
    """
    conn = get_database_connection()
    cursor = conn.cursor()

    query = """
        SELECT name, namespace, full_name, description, parent_class, doc_url
        FROM classes
        WHERE name LIKE ?
    """
    params = [f"%{pattern}%"]

    if namespace:
        query += " AND namespace = ?"
        params.append(namespace)

    query += " LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    results = []

    for row in cursor.fetchall():
        results.append({
            "name": row["name"],
            "namespace": row["namespace"],
            "full_name": row["full_name"],
            "description": row["description"],
            "parent_class": row["parent_class"],
            "doc_url": row["doc_url"],
        })

    conn.close()
    return results


@mcp.tool()
def get_class_methods(
    class_name: str,
    filter: Optional[str] = None,
    include_inherited: bool = False,
) -> list[dict]:
    """
    Get all methods for a specific OpenStudio class.

    Args:
        class_name: Full class name (e.g., "ThermalZone", "openstudio::model::ThermalZone")
        filter: Filter methods by name pattern (e.g., "set.*", ".*Equipment.*")
        include_inherited: Include methods from parent classes (not yet implemented)

    Returns:
        List of methods with name, signature, return type, and description
    """
    conn = get_database_connection()
    cursor = conn.cursor()

    # Find the class
    cursor.execute(
        """
        SELECT id FROM classes
        WHERE name = ? OR full_name = ?
    """,
        (class_name, class_name),
    )

    class_row = cursor.fetchone()
    if not class_row:
        conn.close()
        return []

    class_id = class_row["id"]

    # Get methods
    query = """
        SELECT m.name, m.signature, m.return_type, m.description, m.is_static, m.is_const
        FROM methods m
        WHERE m.class_id = ?
    """
    params = [class_id]

    if filter:
        query += " AND m.name LIKE ?"
        params.append(f"%{filter}%")

    cursor.execute(query, params)
    results = []

    for row in cursor.fetchall():
        results.append({
            "name": row["name"],
            "signature": row["signature"],
            "return_type": row["return_type"],
            "description": row["description"],
            "is_static": bool(row["is_static"]),
            "is_const": bool(row["is_const"]),
        })

    conn.close()
    return results


@mcp.tool()
def get_method_details(class_name: str, method_name: str) -> Optional[dict]:
    """
    Get detailed documentation for a specific method.

    Args:
        class_name: Class name
        method_name: Method name

    Returns:
        Method details including parameters, or None if not found
    """
    conn = get_database_connection()
    cursor = conn.cursor()

    # Find the class
    cursor.execute(
        """
        SELECT id, full_name FROM classes
        WHERE name = ? OR full_name = ?
    """,
        (class_name, class_name),
    )

    class_row = cursor.fetchone()
    if not class_row:
        conn.close()
        return None

    class_id = class_row["id"]
    class_full_name = class_row["full_name"]

    # Get method
    cursor.execute(
        """
        SELECT id, name, signature, return_type, description, is_static, is_const
        FROM methods
        WHERE class_id = ? AND name = ?
    """,
        (class_id, method_name),
    )

    method_row = cursor.fetchone()
    if not method_row:
        conn.close()
        return None

    method_id = method_row["id"]

    # Get parameters
    cursor.execute(
        """
        SELECT param_name, param_type, default_value
        FROM method_params
        WHERE method_id = ?
        ORDER BY param_order
    """,
        (method_id,),
    )

    parameters = []
    for param_row in cursor.fetchall():
        parameters.append({
            "name": param_row["param_name"],
            "type": param_row["param_type"],
            "default_value": param_row["default_value"],
        })

    conn.close()

    return {
        "class": class_full_name,
        "name": method_row["name"],
        "signature": method_row["signature"],
        "return_type": method_row["return_type"],
        "description": method_row["description"],
        "is_static": bool(method_row["is_static"]),
        "is_const": bool(method_row["is_const"]),
        "parameters": parameters,
    }


@mcp.tool()
def search_sdk_documentation(
    query: str,
    search_type: str = "all",
    limit: int = 20,
) -> list[dict]:
    """
    Full-text search across all OpenStudio SDK documentation.

    Args:
        query: Search query (natural language or keywords)
        search_type: "classes", "methods", or "all" (default: "all")
        limit: Maximum results (default: 20)

    Returns:
        List of search results ranked by relevance
    """
    conn = get_database_connection()
    cursor = conn.cursor()

    # Use FTS5 full-text search
    fts_query = """
        SELECT content_type, name, description
        FROM search_index
        WHERE search_index MATCH ?
    """
    params = [query]

    if search_type != "all":
        fts_query += " AND content_type = ?"
        params.append(search_type.rstrip("es"))  # "classes" -> "class", "methods" -> "method"

    fts_query += " LIMIT ?"
    params.append(limit)

    cursor.execute(fts_query, params)
    results = []

    for row in cursor.fetchall():
        results.append({
            "type": row["content_type"],
            "name": row["name"],
            "snippet": row["description"][:200] if row["description"] else "",
        })

    conn.close()
    return results


# ============================================================================
# Ruby Gem Search Tools
# ============================================================================

import subprocess
import os


def find_gem_path(gem_name: str) -> Optional[Path]:
    """Find the path to a vendor gem"""
    vendor_base = Path(__file__).parent.parent.parent.parent / "vendor" / "bundle" / "ruby" / "3.2.0" / "bundler" / "gems"

    if not vendor_base.exists():
        return None

    # Find gem directory (may have hash suffix)
    for gem_dir in vendor_base.iterdir():
        if gem_dir.name.startswith(gem_name):
            return gem_dir

    return None


@mcp.tool()
def search_ruby_gem_code(
    gem_name: str,
    pattern: str,
    file_pattern: str = "*.rb",
) -> list[dict]:
    """
    Search Ruby gem source code for patterns using ripgrep.

    Args:
        gem_name: Gem name (e.g., "openstudio-standards", "openstudio-common-measures")
        pattern: Search pattern (regex)
        file_pattern: File glob pattern (default: "*.rb")

    Returns:
        List of matches with file path, line number, and code snippet
    """
    gem_path = find_gem_path(gem_name)
    if not gem_path:
        return [{"error": f"Gem not found: {gem_name}"}]

    try:
        # Use ripgrep for fast searching
        result = subprocess.run(
            ["rg", pattern, "--glob", file_pattern, "--line-number", "--no-heading"],
            cwd=gem_path,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return []

        matches = []
        for line in result.stdout.split("\n"):
            if not line.strip():
                continue

            # Parse: file_path:line_number:code
            parts = line.split(":", 2)
            if len(parts) >= 3:
                matches.append({
                    "gem": gem_name,
                    "file": parts[0],
                    "line": int(parts[1]),
                    "code_snippet": parts[2].strip()[:200],
                })

        return matches[:50]  # Limit results

    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
def get_ruby_gem_structure(
    gem_name: str,
    path: str = "",
) -> Optional[dict]:
    """
    Get file tree structure of a Ruby gem.

    Args:
        gem_name: Gem name
        path: Subdirectory within gem (e.g., "lib/openstudio-standards")

    Returns:
        Dictionary with directories and files, or None if gem not found
    """
    gem_path = find_gem_path(gem_name)
    if not gem_path:
        return None

    target_path = gem_path / path if path else gem_path

    if not target_path.exists():
        return None

    directories = []
    files = []

    for item in sorted(target_path.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            directories.append(item.name)
        elif item.is_file() and not item.name.startswith("."):
            files.append(item.name)

    return {
        "gem": gem_name,
        "path": path or "/",
        "directories": directories,
        "files": files,
    }


@mcp.tool()
def read_ruby_source_file(
    gem_name: str,
    file_path: str,
) -> Optional[dict]:
    """
    Read a specific Ruby source file from a gem.

    Args:
        gem_name: Gem name
        file_path: Relative path within gem

    Returns:
        Dictionary with file content and metadata, or None if not found
    """
    gem_path = find_gem_path(gem_name)
    if not gem_path:
        return None

    full_path = gem_path / file_path

    if not full_path.exists() or not full_path.is_file():
        return None

    try:
        content = full_path.read_text()
        return {
            "gem": gem_name,
            "file": file_path,
            "content": content,
            "lines": len(content.split("\n")),
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def find_ruby_examples(
    concept: str,
    gems: Optional[list[str]] = None,
) -> list[dict]:
    """
    Find example usage patterns in Ruby gems.

    Args:
        concept: What to find examples of (e.g., "NECB space types", "create geometry")
        gems: Specific gems to search (default: all common gems)

    Returns:
        List of example code snippets with context
    """
    if gems is None:
        gems = [
            "openstudio-standards",
            "openstudio-common-measures",
            "openstudio-model-articulation",
        ]

    results = []

    for gem_name in gems:
        # Search for concept in comments and method names
        matches = search_ruby_gem_code(gem_name, concept, "*.rb")

        for match in matches:
            if not isinstance(match, dict) or "error" in match:
                continue

            results.append({
                "concept_match": concept,
                "gem": match["gem"],
                "file": match["file"],
                "code_snippet": match["code_snippet"],
                "line": match["line"],
            })

    return results[:20]  # Limit to top 20 results


# ============================================================================
# Code Generation Tools
# ============================================================================


@mcp.tool()
def generate_python_example(
    operation: str,
    style: str = "documented",
) -> dict:
    """
    Generate Python example code for OpenStudio operations.

    Args:
        operation: What to do (e.g., "create thermal zone", "add VAV system")
        style: "minimal", "documented", or "comprehensive" (default: "documented")

    Returns:
        Python code with explanation
    """
    # Simple template-based generation
    # In production, this could use LLM or more sophisticated templates

    templates = {
        "create thermal zone": """import openstudio

# Create model
model = openstudio.model.Model()

# Create thermal zone
zone = openstudio.model.ThermalZone(model)
zone.setName('Office Zone')

# Create thermostat with dual setpoints
thermostat = openstudio.model.ThermostatSetpointDualSetpoint(model)
# Note: You need to create schedules for heating and cooling
# thermostat.setHeatingSetpointTemperatureSchedule(heating_schedule)
# thermostat.setCoolingSetpointTemperatureSchedule(cooling_schedule)
zone.setThermostatSetpointDualSetpoint(thermostat)
""",
        "create building": """import openstudio

# Create model
model = openstudio.model.Model()

# Create building
building = model.getBuilding()
building.setName('My Building')

# Set building properties
building.setNorthAxis(0.0)  # degrees from true north
building.setStandardsNumberOfStories(3)
building.setStandardsNumberOfAboveGroundStories(3)
""",
    }

    code = templates.get(operation.lower(), f"# TODO: Implement {operation}")

    return {
        "operation": operation,
        "language": "python",
        "style": style,
        "code": code,
        "explanation": f"Example Python code for: {operation}",
    }


@mcp.tool()
def generate_ruby_example(
    operation: str,
    standard: Optional[str] = None,
) -> dict:
    """
    Generate Ruby example code using openstudio-standards.

    Args:
        operation: What to do
        standard: Building standard (e.g., "NECB", "ASHRAE 90.1-2019")

    Returns:
        Ruby code with explanation
    """
    templates = {
        "create NECB building": """require 'openstudio'
require 'openstudio-standards'

# Create model
model = OpenStudio::Model::Model.new

# Create geometry
geometry = OpenstudioStandards::Geometry.create_shape_rectangle(
  model,
  length: 50.0,
  width: 30.0,
  num_floors: 3,
  floor_to_floor_height: 3.8
)

# Apply NECB 2020 space types
standard = Standard.build('NECB2020')
standard.model_add_necb_space_type(model, 'Office', 'OpenOffice')
""",
    }

    code = templates.get(operation.lower(), f"# TODO: Implement {operation}")

    return {
        "operation": operation,
        "language": "ruby",
        "standard": standard,
        "code": code,
        "explanation": f"Example Ruby code for: {operation}",
    }


@mcp.tool()
def compare_python_ruby(operation: str) -> dict:
    """
    Show equivalent code in both Python and Ruby.

    Args:
        operation: Operation to demonstrate

    Returns:
        Side-by-side comparison with notes
    """
    python = generate_python_example(operation, "minimal")
    ruby = generate_ruby_example(operation)

    return {
        "operation": operation,
        "python_code": python["code"],
        "ruby_code": ruby["code"],
        "notes": [
            "Python uses openstudio. prefix, Ruby uses OpenStudio::",
            "Both use same method names and signatures",
            "Parameter handling is identical",
        ],
    }


# ============================================================================
# NECB Query Tools
# ============================================================================


@mcp.tool()
def query_necb_sections(
    vintage: str,
    section_pattern: Optional[str] = None,
    title_pattern: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """
    Search NECB sections by vintage, section number, or title.

    Args:
        vintage: NECB vintage ("2011", "2015", "2017", "2020")
        section_pattern: Section number pattern (e.g., "3.2", "3.2.1")
        title_pattern: Title search pattern
        limit: Maximum results (default: 20)

    Returns:
        List of matching sections with content
    """
    conn = get_necb_database_connection()
    cursor = conn.cursor()

    query = """
        SELECT section_number, title, content, page_number
        FROM necb_sections
        WHERE vintage = ?
    """
    params = [vintage]

    if section_pattern:
        query += " AND section_number LIKE ?"
        params.append(f"%{section_pattern}%")

    if title_pattern:
        query += " AND title LIKE ?"
        params.append(f"%{title_pattern}%")

    query += " ORDER BY section_number LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    results = []

    for row in cursor.fetchall():
        results.append({
            "vintage": vintage,
            "section_number": row["section_number"],
            "title": row["title"],
            "content": row["content"][:500] if row["content"] else "",  # Limit content preview
            "page_number": row["page_number"],
        })

    conn.close()
    return results


@mcp.tool()
def get_necb_table(
    vintage: str,
    table_number: str,
) -> Optional[dict]:
    """
    Get a specific NECB table with all rows.

    Args:
        vintage: NECB vintage ("2011", "2015", "2017", "2020")
        table_number: Table number (e.g., "Table 3.2.2.2." or "Table-51-6" for legacy IDs)

    Returns:
        Table details with headers and rows, or None if not found
    """
    conn = get_necb_database_connection()
    cursor = conn.cursor()

    # Get table metadata - support both NECB numbers and legacy IDs
    # Try exact match first, prioritizing lower page numbers (main text over appendices)
    cursor.execute(
        """
        SELECT id, table_number, title, headers, page_number
        FROM necb_tables
        WHERE vintage = ? AND table_number = ?
        ORDER BY page_number ASC
        LIMIT 1
    """,
        (vintage, table_number),
    )

    table_row = cursor.fetchone()

    # If not found and input looks like NECB format, try with/without trailing period
    if not table_row and re.match(r'^Table\s+\d+', table_number):
        # Try adding or removing trailing period
        alt_table_number = table_number.rstrip('.') + '.' if not table_number.endswith('.') else table_number.rstrip('.')

        cursor.execute(
            """
            SELECT id, table_number, title, headers, page_number
            FROM necb_tables
            WHERE vintage = ? AND table_number = ?
            ORDER BY page_number ASC
            LIMIT 1
        """,
            (vintage, alt_table_number),
        )
        table_row = cursor.fetchone()

    if not table_row:
        conn.close()
        return None

    table_id = table_row["id"]
    headers = json.loads(table_row["headers"])

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
        "headers": headers,
        "rows": rows,
        "page_number": table_row["page_number"],
    }


@mcp.tool()
def query_necb_requirements(
    requirement_type: Optional[str] = None,
    vintage: Optional[str] = None,
    section: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """
    Search NECB requirements by type, vintage, or section.

    Args:
        requirement_type: Type of requirement ("envelope", "u_value", "lighting_power_density", "climate_zone")
        vintage: Filter by vintage ("2011", "2015", "2017", "2020")
        section: Filter by section
        limit: Maximum results (default: 50)

    Returns:
        List of requirements with values and units
    """
    conn = get_necb_database_connection()
    cursor = conn.cursor()

    query = """
        SELECT vintage, section, requirement_type, description, value, unit
        FROM necb_requirements
        WHERE 1=1
    """
    params = []

    if requirement_type:
        query += " AND requirement_type = ?"
        params.append(requirement_type)

    if vintage:
        query += " AND vintage = ?"
        params.append(vintage)

    if section:
        query += " AND section = ?"
        params.append(section)

    query += " LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    results = []

    for row in cursor.fetchall():
        results.append({
            "vintage": row["vintage"],
            "section": row["section"],
            "requirement_type": row["requirement_type"],
            "description": row["description"],
            "value": row["value"],
            "unit": row["unit"],
        })

    conn.close()
    return results


@mcp.tool()
def search_necb(
    query: str,
    vintage: Optional[str] = None,
    content_type: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """
    Full-text search across all NECB content.

    Args:
        query: Search query (natural language or keywords)
        vintage: Filter by vintage ("2011", "2015", "2017", "2020")
        content_type: Filter by content type ("section", "table")
        limit: Maximum results (default: 20)

    Returns:
        List of search results ranked by relevance
    """
    conn = get_necb_database_connection()
    cursor = conn.cursor()

    fts_query = """
        SELECT vintage, content_type, title, content
        FROM necb_search
        WHERE necb_search MATCH ?
    """
    params = [query]

    if vintage:
        fts_query += " AND vintage = ?"
        params.append(vintage)

    if content_type:
        fts_query += " AND content_type = ?"
        params.append(content_type)

    fts_query += " LIMIT ?"
    params.append(limit)

    cursor.execute(fts_query, params)
    results = []

    for row in cursor.fetchall():
        results.append({
            "vintage": row["vintage"],
            "type": row["content_type"],
            "title": row["title"],
            "snippet": row["content"][:200] if row["content"] else "",
        })

    conn.close()
    return results


@mcp.tool()
def compare_necb_vintages(
    requirement_type: str,
    vintages: Optional[list[str]] = None,
) -> dict:
    """
    Compare a specific requirement type across NECB vintages.

    Args:
        requirement_type: Type of requirement to compare ("envelope", "u_value", "lighting_power_density")
        vintages: List of vintages to compare (default: all vintages)

    Returns:
        Dictionary with comparison results grouped by vintage
    """
    if vintages is None:
        vintages = ["2011", "2015", "2017", "2020"]

    conn = get_necb_database_connection()
    cursor = conn.cursor()

    comparison = {}

    for vintage in vintages:
        cursor.execute(
            """
            SELECT description, value, unit
            FROM necb_requirements
            WHERE vintage = ? AND requirement_type = ?
        """,
            (vintage, requirement_type),
        )

        requirements = []
        for row in cursor.fetchall():
            requirements.append({
                "description": row["description"],
                "value": row["value"],
                "unit": row["unit"],
            })

        comparison[vintage] = requirements

    conn.close()

    return {
        "requirement_type": requirement_type,
        "vintages": comparison,
    }


if __name__ == "__main__":
    # Run the server
    mcp.run()
