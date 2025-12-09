"""LLM-powered table repair and normalization

Uses LLM (Ollama local or Claude API) to repair extraction errors and normalize
table data to target Pydantic schemas with strict validation.
"""

import json
import re
from typing import Any, Dict

from pydantic import BaseModel, ValidationError

from .llm_backends import LLMBackend, create_llm_backend
from .schemas import SCHEMA_REGISTRY, get_schema_for_table


# ============================================================================
# Phase 6A: NECB 2011 Table Number Normalization
# ============================================================================

# NECB 2011 table number normalization patterns
# NECB 2011 PDFs use format like "5.3.2.8.A" (no dash) but schemas expect "5.3.2.8.-A"
NECB_2011_TABLE_NORMALIZATIONS: Dict[str, str] = {
    # HVAC Coefficient tables (26 tables: A-Z + AA)
    r'^5\.3\.2\.8\.([A-Z]{1,2})$': r'5.3.2.8.-\1',

    # Exterior lighting tables (4 tables: A-D)
    r'^4\.2\.3\.1\.([A-E])$': r'4.2.3.1.-\1',

    # Daylight control factor tables (2 tables: A, B)
    r'^4\.3\.2\.7\.([AB])$': r'4.3.2.7.-\1',

    # Occupancy factor tables (2 tables: A, B)
    r'^4\.3\.2\.10\.([AB])$': r'4.3.2.10.-\1',

    # Daylight supply factor tables (2 tables: A, B)
    r'^4\.3\.2\.9\.([AB])$': r'4.3.2.9.-\1',
}


def normalize_necb_2011_table_number(table_number: str, vintage: str) -> str:
    """
    Normalize NECB 2011 table numbers to match schema patterns.

    NECB 2011 PDFs use format like "5.3.2.8.A" (no dash), but schemas expect
    "5.3.2.8.-A" (with dash) to match the format used in NECB 2015+.

    Args:
        table_number: Raw table number from LLM extraction
        vintage: NECB vintage (e.g., "2011", "2015")

    Returns:
        Normalized table number that matches schema patterns

    Examples:
        >>> normalize_necb_2011_table_number("5.3.2.8.A", "2011")
        "5.3.2.8.-A"
        >>> normalize_necb_2011_table_number("5.3.2.8.-A", "2015")
        "5.3.2.8.-A"  # No change for other vintages
        >>> normalize_necb_2011_table_number("3.2.2.2", "2011")
        "3.2.2.2"  # No normalization needed
    """
    # Only apply normalization to NECB 2011
    if vintage != "2011":
        return table_number

    # Apply each normalization pattern
    for pattern, replacement in NECB_2011_TABLE_NORMALIZATIONS.items():
        if re.match(pattern, table_number):
            normalized = re.sub(pattern, replacement, table_number)
            return normalized

    # No normalization needed
    return table_number


class LLMTableRepairer:
    """LLM-powered table repair and schema mapping"""

    def __init__(
        self,
        backend: str = "ollama",
        model: str | None = None,
        temperature: float = 0.0,
        timeout: int = 30,
        api_key: str | None = None,
        verbose: bool = False,
        config: "ParserConfig | None" = None,  # Phase 6C: for table-specific model overrides
    ):
        """
        Initialize LLM table repairer

        Args:
            backend: LLM backend type ("ollama" or "claude")
            model: Model name (uses backend defaults if None)
                   - Ollama: "qwen2.5:14b-instruct" (default), "llama3.1:8b"
                   - Claude: "claude-sonnet-4-5-20250929" (default), "claude-haiku-3-5-20241022"
            temperature: Sampling temperature (0.0 for deterministic)
            timeout: Request timeout in seconds (Ollama only)
            api_key: API key for Claude (uses ANTHROPIC_API_KEY env var if None)
            verbose: Enable verbose logging
            config: ParserConfig for table-specific model overrides (Phase 6C)
        """
        self.backend = create_llm_backend(
            backend_type=backend,
            model=model,
            api_key=api_key,
            verbose=verbose,
        )
        self.temperature = temperature
        self.timeout = timeout
        self.verbose = verbose
        self.config = config  # Phase 6C: store config for table-specific overrides
        self.default_model = model  # Phase 6C: store default model for reference

        if self.verbose:
            print(f"LLM repairer initialized with: {self.backend.get_model_name()}")

    def repair_and_normalize(
        self,
        raw_table: str,
        table_number: str,
        vintage: str,
        target_schema: type[BaseModel] | None = None,
    ) -> tuple[BaseModel | None, str | None, list[str]]:
        """
        Repair extracted table and map to target schema

        Args:
            raw_table: Extracted table (Markdown format from PyMuPDF)
            table_number: NECB table number (e.g., "3.2.2.2")
            vintage: NECB vintage (e.g., "2020")
            target_schema: Pydantic model defining output structure
                          (auto-detected if None)

        Returns:
            (validated_data, llm_output, errors)
            - validated_data: Pydantic model instance if successful
            - llm_output: Raw LLM output string (for caching)
            - errors: List of validation errors if failed

        Process:
        1. Auto-detect schema if not provided
        2. Generate repair prompt with schema description
        3. Send to local LLM (temperature=0 for determinism)
        4. Parse LLM response as JSON
        5. Validate against Pydantic schema
        6. Reject if validation fails (no hallucinations)
        """
        errors = []

        # Auto-detect schema if not provided
        if target_schema is None:
            target_schema = get_schema_for_table(table_number)
            if target_schema is None:
                errors.append(f"No schema found for table {table_number}")
                return None, None, errors

        # Phase 8: Route operating schedules to chunked extraction
        # This avoids API token limits by extracting one schedule type per call (7 calls total)
        if table_number.startswith("A-8.4.3.2.(1)"):
            from bluesky.necb.build.tables.schemas import OperatingScheduleTable
            if target_schema == OperatingScheduleTable:
                if self.verbose:
                    print(f"\n{'='*80}")
                    print(f"LLM Repair: Table {table_number} (vintage {vintage})")
                    print(f"Schema: {target_schema.__name__}")
                    print(f"Using Phase 8 Chunked Extraction (7 API calls)")
                    print(f"{'='*80}\n")
                return self._extract_operating_schedule_chunked(
                    pymupdf_table=raw_table,
                    table_number=table_number,
                    vintage=vintage or "",
                    target_schema=target_schema
                )

        # Phase 16: Route Table C-1 (Climate Design Data) to chunked extraction by page
        # This 18-page table has 400+ locations - extract page by page then merge
        if table_number == "C-1":
            from bluesky.necb.build.tables.schemas import ClimateDesignDataTable
            if target_schema == ClimateDesignDataTable:
                if self.verbose:
                    print(f"\n{'='*80}")
                    print(f"LLM Repair: Table {table_number} (vintage {vintage})")
                    print(f"Schema: {target_schema.__name__}")
                    print(f"Using Phase 16 Chunked Extraction (by page)")
                    print(f"{'='*80}\n")
                return self._extract_climate_data_chunked(
                    pymupdf_table=raw_table,
                    table_number=table_number,
                    vintage=vintage or "",
                    target_schema=target_schema
                )

        # Phase 10: Large tables with JSON truncation - route to CSV extraction
        # These tables fail with JSON truncation at ~12k characters during LLM output
        LARGE_TABLE_CSV = [
            '4.3.2.10.-A',      # DaylightControlTable (20 rows × 3 cols)
            '5.2.12.1',         # Phase 14: NECB 2017 - PackagedHVACTable JSON truncation (line 208)
            '5.2.12.1.-H',      # PackagedHVACTable (25 rows × 5 cols)
            '5.3.2.7',          # Phase 15: NECB 2017 - TradeOffValueTable JSON truncation (line 323, char 7711)
            '5.3.2.8.-A',       # Phase 14: NECB 2017 - CoefficientTable JSON truncation
            '5.3.2.8.-R',       # Phase 14: NECB 2017 - CoefficientTable JSON truncation
            '5.3.2.8.-V',       # Phase 14: NECB 2017 - CoefficientTable JSON truncation
            '5.3.2.8.-Z',       # Phase 14: NECB 2017 - CoefficientTable JSON truncation
            '6.2.2.1',          # SWHEquipmentTable (8 rows × 18 cols)
            '8.5.1.1',          # ObjectivesTable (43 rows × 2 cols)
            'A-8.4.3.2.(2)-B',  # ModelingGuidanceTable (21 rows × 6 cols)
        ]

        if table_number in LARGE_TABLE_CSV:
            if self.verbose:
                print(f"\n{'='*80}")
                print(f"LLM Repair: Table {table_number} (vintage {vintage})")
                print(f"Schema: {target_schema.__name__}")
                print(f"Using Phase 10 CSV Extraction (compact output to avoid truncation)")
                print(f"{'='*80}\n")
            return self._extract_large_table_csv(
                pymupdf_table=raw_table,
                table_number=table_number,
                vintage=vintage or "",
                target_schema=target_schema
            )

        if self.verbose:
            print(f"\n{'='*80}")
            print(f"LLM Repair: Table {table_number} (vintage {vintage})")
            print(f"Schema: {target_schema.__name__}")
            print(f"{'='*80}\n")

        # Generate prompt
        context = {"vintage": vintage, "table_number": table_number}
        prompt = self.generate_repair_prompt(raw_table, target_schema, context)

        if self.verbose:
            print(f"Prompt length: {len(prompt)} characters\n")

        try:
            # Phase 6C: Check for table-specific model override and max_tokens
            model = None  # None means use backend's default
            max_tokens = None  # None means use backend's default (4096)

            # Phase 12: Document reference table needs more tokens (36 rows, 6 pages)
            if table_number == "1.3.1.2":
                max_tokens = 20000  # Large reference table with many standards
                if self.verbose:
                    print(f"Using increased max_tokens for document reference table: {max_tokens}\n")

            # Phase 12: Climate design data table uses CSV format (72 rows, 18 pages)
            # CSV format configured via table-specific instructions, no max_tokens override needed

            if self.config and self.config.table_specific_models:
                for pattern, override_model in self.config.table_specific_models.items():
                    if table_number.startswith(pattern):
                        model = override_model
                        # Operating schedules need more tokens for CSV output
                        # Phase 7: CSV format is much more compact but still needs room
                        if pattern == "A-8.4.3.2.(1)":
                            max_tokens = 16384  # Increased to ensure CSV output is not truncated
                        if self.verbose:
                            print(f"Using model override: {model} (matched pattern '{pattern}')")
                            if max_tokens:
                                print(f"Using max_tokens: {max_tokens}\n")
                        break

            # Query LLM via backend abstraction
            llm_output = self.backend.generate(
                prompt=prompt,
                model=model,  # Use overridden model if specified, otherwise None = backend default
                temperature=self.temperature,
                timeout=self.timeout,
                max_tokens=max_tokens,  # Use custom max_tokens for operating schedules
            )

            if self.verbose:
                print(f"LLM output length: {len(llm_output)} characters\n")
                print(f"First 500 chars:\n{llm_output[:500]}\n")

            # Validate output (with Phase 6A table number normalization)
            validated_data, validation_errors = self.validate_output(
                llm_output, target_schema, vintage
            )

            if validated_data:
                if self.verbose:
                    print(f"✅ Validation successful!")
                return validated_data, llm_output, []
            else:
                errors.extend(validation_errors)
                if self.verbose:
                    print(f"❌ Validation failed:")
                    for error in validation_errors:
                        print(f"  - {error}")
                return None, llm_output, errors

        except Exception as e:
            error_msg = f"LLM request failed: {str(e)}"
            errors.append(error_msg)
            if self.verbose:
                print(f"❌ {error_msg}")
            return None, None, errors

    def generate_repair_prompt(
        self,
        raw_table: str,
        target_schema: type[BaseModel],
        context: dict[str, str],
    ) -> str:
        """
        Create detailed prompt for LLM repair

        Args:
            raw_table: Raw table markdown with potential issues
            target_schema: Target Pydantic schema
            context: Metadata (vintage, table_number)

        Returns:
            Formatted prompt string

        Prompt structure:
        - Role definition
        - Input table (with issues highlighted)
        - Target schema with field descriptions
        - Strict rules (no hallucination, reject if ambiguous)
        - Output format (JSON matching schema)
        - Examples (few-shot learning)
        """
        vintage = context["vintage"]
        table_number = context["table_number"]

        # Get schema as JSON
        schema_json = json.dumps(target_schema.model_json_schema(), indent=2)

        # Generate table-specific instructions
        instructions = self._get_table_specific_instructions(table_number)

        # Build prompt
        # Phase 12 FIX: For Table C-1, restructure to emphasize CSV over JSON
        # Problem: Showing "Target Schema (JSON)" confuses LLM into outputting JSON
        # Solution: De-emphasize JSON, put CSV instructions LAST
        if table_number == "C-1":
            template = f'''You are a building code data extraction assistant.

**Task**: Extract data from NECB {vintage} Table {table_number}.

**Input Table** (Markdown with potential issues):
```markdown
{raw_table}
```

**Target Fields** (for reference only - DO NOT use JSON format):
vintage, table_number, title, location, elevation_m, design_temp_jan_2_5_pct,
design_temp_jan_1_pct, design_temp_july_dry, design_temp_july_wet,
degree_days_below_18c, degree_days_below_15c, wind_pressure_1_10, wind_pressure_1_50

{instructions}

**CRITICAL - OUTPUT FORMAT REQUIREMENTS**:
You MUST output CSV format as shown in the instructions above.
DO NOT output JSON - the table is too large (72 rows) and JSON will truncate.

Your output must start EXACTLY like this (no code fences, no {{ }} braces):

vintage: 2020
table_number: C-1
title: Climate Design Data for Locations in Canada

location,elevation_m,design_temp_jan_2_5_pct,design_temp_jan_1_pct,design_temp_july_dry,design_temp_july_wet,degree_days_below_18c,degree_days_below_15c,wind_pressure_1_10,wind_pressure_1_50
Abbottsford,60,-9,-12,29,20,2970,2210,0.28,0.37
...additional rows...
'''
        else:
            # Default JSON-based prompt for all other tables
            template = f'''You are a building code data extraction assistant.

**Task**: Extract data from NECB {vintage} Table {table_number}.

**Input Table** (Markdown with potential issues):
```markdown
{raw_table}
```

**Target Schema** (JSON):
```json
{schema_json}
```

{instructions}

**Strict Rules**:
1. Extract ONLY the data rows specified in the instructions
2. Ignore merged description cells, captions, footnotes, and empty rows
3. All numeric values must be valid floats within the schema's range constraints
4. If any data is ambiguous, missing, or unclear, return {{"error": "reason"}}
5. Output ONLY valid JSON matching the schema EXACTLY (no explanation, no markdown)
6. Do NOT hallucinate or invent values - if data is unclear, return error

**Output Format**:
Return ONLY the JSON object, nothing else. Start with {{ and end with }}.
'''

        return template

    def _get_table_specific_instructions(self, table_number: str) -> str:
        """Get table-specific extraction instructions"""
        instructions = {
            "3.2.2.2": """**Table-Specific Instructions**:
- Extract ONLY rows for "Walls", "Roofs", and "Floors" (case-insensitive)
- Normalize column headers: "Zone 4:(2)" → "zone_4_max_u", "Zone 5:(2)" → "zone_5_max_u", etc.
- U-values must be in W/(m²·K), range 0.05-2.0
- Each zone column contains a single U-value (float)
- Expected output: 3 assemblies (Walls, Roofs, Floors) with 6 U-values each

**Example Output**:
```json
{
  "vintage": "2020",
  "table_number": "3.2.2.2",
  "assemblies": [
    {
      "assembly_type": "Walls",
      "zone_4_max_u": 0.315,
      "zone_5_max_u": 0.278,
      "zone_6_max_u": 0.247,
      "zone_7a_max_u": 0.210,
      "zone_7b_max_u": 0.210,
      "zone_8_max_u": 0.183
    },
    {
      "assembly_type": "Roofs",
      "zone_4_max_u": 0.193,
      "zone_5_max_u": 0.156,
      "zone_6_max_u": 0.156,
      "zone_7a_max_u": 0.138,
      "zone_7b_max_u": 0.138,
      "zone_8_max_u": 0.121
    },
    {
      "assembly_type": "Floors",
      "zone_4_max_u": 0.227,
      "zone_5_max_u": 0.183,
      "zone_6_max_u": 0.183,
      "zone_7a_max_u": 0.162,
      "zone_7b_max_u": 0.162,
      "zone_8_max_u": 0.142
    }
  ]
}
```""",
            "3.2.2.3": """**Table-Specific Instructions**:
- Extract ONLY rows for fenestration assemblies: "Windows", "Doors", "Skylights"
- Normalize column headers: "Zone 4:(2)" → "zone_4_max_u", etc.
- U-values must be in W/(m²·K), range 0.05-2.0
- Expected output: 2-3 assemblies with 6 U-values each""",
            "3.2.1.4": """**Table-Specific Instructions**:
- Extract HDD ranges and corresponding FDWR values
- HDD ranges: "< 3000", "3000 to 3999", "4000 to 4999", etc.
- FDWR values are ratios (0.0-1.0)
- Convert HDD ranges to hdd_min/hdd_max integers
- Use hdd_max=None for open-ended ranges (e.g., "≥ 7000")""",
            "4.2.1.3": """**Table-Specific Instructions**:
- Extract building/space types and maximum LPD values
- LPD values in W/m²
- Handle hierarchical structure: building type → space type
- Some rows have building_type only, others have both building_type and space_type""",
            "5.2.5.3": """**Table-Specific Instructions**:
- Extract piping insulation requirements
- System types: heating, cooling
- Temperature ranges in °C - IMPORTANT: Extract numeric values only:
  * For "> 100°C", use temp_range_min=100, temp_range_max=999 (large number)
  * For "< 60°C", use temp_range_min=-50, temp_range_max=60
  * For "10 to 60°C", use temp_range_min=10, temp_range_max=60
- Pipe diameters in mm (may be ranges like "≤ 25" or "40 to 65" - keep as string)
- Insulation thickness in mm (must be numeric)

**Example Output**:
```json
{
  "vintage": "2017",
  "table_number": "5.2.5.3",
  "requirements": [
    {
      "system_type": "Heating",
      "temp_range_min": 10.0,
      "temp_range_max": 60.0,
      "pipe_diameter_mm": "≤ 25",
      "min_insulation_thickness_mm": 25.0
    }
  ]
}
```""",
            "5.2.6.2": """**Table-Specific Instructions**:
- Extract HVAC equipment efficiency requirements
- IMPORTANT: MUST extract all 5 fields for EVERY row:
  * equipment_category: Main category (e.g., "Chillers", "Boilers", "Heat Pumps")
  * equipment_type: Specific type (REQUIRED - e.g., "Air-cooled chiller", "Gas-fired boiler")
  * size_category: Size/capacity range (optional - e.g., "< 19 kW", "≥ 150 tons")
  * efficiency_metric: Metric name (e.g., "COP", "AFUE", "EER", "kW/ton")
  * minimum_efficiency: Numeric efficiency value (e.g., 2.8, 0.80, 12.0)
- Handle multi-row equipment entries (merged cells)
- If equipment_type cell is empty, use continuation from previous row

**Example Output**:
```json
{
  "vintage": "2011",
  "table_number": "5.2.6.2",
  "equipment": [
    {
      "equipment_category": "Chillers",
      "equipment_type": "Air-cooled chiller",
      "size_category": "< 528 kW",
      "efficiency_metric": "COP",
      "minimum_efficiency": 2.8
    }
  ]
}
```""",
            "8.4.4.8.A": """**Table-Specific Instructions**:
- Extract HVAC equipment performance requirements
- Equipment types, capacity ranges, performance metrics (COP, EER, etc.)
- Capacity may be in kW, tons, or other units
- Handle continuation rows (empty cells indicate continuation of previous row)""",
            "8.4.4.8.B": """**Table-Specific Instructions**:
- Extract HVAC equipment performance requirements
- Similar to 8.4.4.8.A but different equipment categories
- Handle merged cells and continuation rows
- Capacity ranges may span multiple rows""",
        }

        # Add HVAC coefficient table instructions (5.3.2.8.-A through -AA)
        # These tables have identical structure, so use pattern matching
        if table_number.startswith("5.3.2.8.-"):
            return """**Table-Specific Instructions**:
- Extract HVAC system performance curve coefficients
- Each row represents a performance curve (e.g., CAP_FT, EIR_FT, PLF)
- Coefficients A through F are polynomial coefficients (floats)
- Extract the curve name from the first column
- Extract numeric coefficients from subsequent columns
- Some rows may have minimum/maximum output bounds

**Example Output**:
```json
{
  "vintage": "2017",
  "table_number": "5.3.2.8.-A",
  "hvac_system_type": "HVAC-1",
  "system_description": "Built-up Variable-Volume",
  "coefficients": [
    {
      "curve_name": "CAP_FT",
      "description": "Cooling capacity as function of temperature",
      "coefficient_a": 0.942587793,
      "coefficient_b": 0.009543347,
      "coefficient_c": 0.000683770,
      "coefficient_d": -0.011042676,
      "coefficient_e": 0.000005249,
      "coefficient_f": -0.000009720,
      "minimum_value": null,
      "maximum_value": null
    },
    {
      "curve_name": "EIR_FT",
      "coefficient_a": 0.342414409,
      "coefficient_b": 0.034885008,
      "coefficient_c": null,
      "coefficient_d": null,
      "coefficient_e": null,
      "coefficient_f": null,
      "minimum_value": null,
      "maximum_value": null
    }
  ]
}
```"""

        # Add Objectives table instructions (x.5.1.1)
        if table_number.endswith(".5.1.1") or table_number == "10.2.1.1":
            section_names = {
                "3.5.1.1": "Building Envelope",
                "4.5.1.1": "Lighting",
                "5.5.1.1": "HVAC",
                "6.5.1.1": "Service Water Heating",
                "7.5.1.1": "Electrical Power",
                "8.5.1.1": "Building Energy Performance Compliance",
                "10.2.1.1": "Alternative Compliance Path",
            }
            section_name = section_names.get(table_number, "Unknown Section")
            return f"""**Table-Specific Instructions**:
- Extract section references and their associated objectives/functional statements
- The table maps NECB section references to National Building Code objectives
- First column: Section reference (e.g., "3.2.1.1.(1)")
- Second column: Objectives (e.g., "OE", "OE1.1")
- Third column (if present): Functional statements (e.g., "F81", "F82")
- This is the {section_name} objectives table

**Example Output**:
```json
{{
  "vintage": "2020",
  "table_number": "{table_number}",
  "section_name": "{section_name}",
  "objectives": [
    {{
      "section_reference": "3.2.1.1.(1)",
      "objectives": "OE",
      "functional_statements": "F81"
    }},
    {{
      "section_reference": "3.2.1.2.(1)",
      "objectives": "OE1.1",
      "functional_statements": "F82"
    }}
  ]
}}
```"""

        # Add Operating Schedule table instructions (A-8.4.3.2.(1)x)
        # Phase 6C: DISABLED - Replaced by Phase 7 CSV format (see line 1314)
        # Phase 7 uses CSV format to avoid token limit issues
        if False and "A-8.4.3.2.(1)" in table_number and "(2)" not in table_number:
            # Extract schedule letter (A, B, C, etc.)
            schedule_letter = table_number[-1] if table_number[-1].isalpha() else "A"
            building_types = {
                "A": "Office/Professional",
                "B": "Retail",
                "C": "School/University",
                "D": "Hotel/Motel",
                "E": "Healthcare (24-hour)",
                "F": "Restaurant",
                "G": "Warehouse",
                "H": "Religious",
                "I": "Sports/Recreation",
                "J": "Manufacturing",
                "K": "Multifamily Residential",
            }
            building_type = building_types.get(schedule_letter, "Unknown")
            return f"""**Table-Specific Instructions (Phase 6C Enhanced)**:
This is a multi-page hourly operating schedule table for {building_type} buildings.

TABLE STRUCTURE:
- 24 hourly columns (hours 0-23, representing midnight to 11pm)
- Rows grouped by system type (Occupancy, Lighting, Equipment, HVAC)
- Each system has rows for day types: Weekday, Weekend, Holiday (if present)
- Values are fractions 0.0 to 1.0 (0% to 100% of design/installed capacity)

CRITICAL JSON FORMATTING RULES:
1. Return ONLY valid, parseable JSON - no explanatory text before or after
2. Each hour entry MUST include both "hour" and "value" keys
3. Hours array MUST have exactly 24 entries (hours 0-23) with no gaps
4. If a value is unclear, use 0.0 as default (do NOT skip hours)
5. No trailing commas in arrays or objects
6. All arrays must be properly closed with ]
7. All objects must be properly closed with }}

HANDLING MULTI-PAGE TABLES:
- Ignore repeated header rows that say "Hour", "Weekday", "Weekend"
- If table continues across pages, extract all hours from all pages
- Combine into single complete 24-hour schedule

JSON STRUCTURE (FOLLOW EXACTLY):
{{
  "vintage": "2020",
  "table_number": "{table_number}",
  "schedule_name": "Operating Schedule {schedule_letter}",
  "building_type": "{building_type}",
  "systems": [
    {{
      "system_type": "Occupancy",
      "schedules": [
        {{
          "day_type": "Weekday",
          "hours": [
            {{"hour": 0, "value": 0.0}},
            {{"hour": 1, "value": 0.0}},
            {{"hour": 2, "value": 0.0}},
            {{"hour": 3, "value": 0.0}},
            {{"hour": 4, "value": 0.0}},
            {{"hour": 5, "value": 0.0}},
            {{"hour": 6, "value": 0.1}},
            {{"hour": 7, "value": 0.2}},
            {{"hour": 8, "value": 0.95}},
            {{"hour": 9, "value": 1.0}},
            {{"hour": 10, "value": 1.0}},
            {{"hour": 11, "value": 1.0}},
            {{"hour": 12, "value": 0.8}},
            {{"hour": 13, "value": 1.0}},
            {{"hour": 14, "value": 1.0}},
            {{"hour": 15, "value": 1.0}},
            {{"hour": 16, "value": 1.0}},
            {{"hour": 17, "value": 0.5}},
            {{"hour": 18, "value": 0.3}},
            {{"hour": 19, "value": 0.1}},
            {{"hour": 20, "value": 0.1}},
            {{"hour": 21, "value": 0.1}},
            {{"hour": 22, "value": 0.05}},
            {{"hour": 23, "value": 0.0}}
          ]
        }},
        {{
          "day_type": "Weekend",
          "hours": [
            {{"hour": 0, "value": 0.0}},
            {{"hour": 1, "value": 0.0}},
            {{"hour": 2, "value": 0.0}},
            {{"hour": 3, "value": 0.0}},
            {{"hour": 4, "value": 0.0}},
            {{"hour": 5, "value": 0.0}},
            {{"hour": 6, "value": 0.0}},
            {{"hour": 7, "value": 0.0}},
            {{"hour": 8, "value": 0.0}},
            {{"hour": 9, "value": 0.0}},
            {{"hour": 10, "value": 0.1}},
            {{"hour": 11, "value": 0.1}},
            {{"hour": 12, "value": 0.1}},
            {{"hour": 13, "value": 0.1}},
            {{"hour": 14, "value": 0.1}},
            {{"hour": 15, "value": 0.1}},
            {{"hour": 16, "value": 0.1}},
            {{"hour": 17, "value": 0.0}},
            {{"hour": 18, "value": 0.0}},
            {{"hour": 19, "value": 0.0}},
            {{"hour": 20, "value": 0.0}},
            {{"hour": 21, "value": 0.0}},
            {{"hour": 22, "value": 0.0}},
            {{"hour": 23, "value": 0.0}}
          ]
        }}
      ]
    }},
    {{
      "system_type": "Lighting",
      "schedules": [
        {{
          "day_type": "Weekday",
          "hours": [
            {{"hour": 0, "value": 0.05}},
            {{"hour": 1, "value": 0.05}},
            {{"hour": 2, "value": 0.05}},
            {{"hour": 3, "value": 0.05}},
            {{"hour": 4, "value": 0.05}},
            {{"hour": 5, "value": 0.05}},
            {{"hour": 6, "value": 0.1}},
            {{"hour": 7, "value": 0.3}},
            {{"hour": 8, "value": 0.9}},
            {{"hour": 9, "value": 1.0}},
            {{"hour": 10, "value": 1.0}},
            {{"hour": 11, "value": 1.0}},
            {{"hour": 12, "value": 0.8}},
            {{"hour": 13, "value": 1.0}},
            {{"hour": 14, "value": 1.0}},
            {{"hour": 15, "value": 1.0}},
            {{"hour": 16, "value": 1.0}},
            {{"hour": 17, "value": 0.5}},
            {{"hour": 18, "value": 0.3}},
            {{"hour": 19, "value": 0.2}},
            {{"hour": 20, "value": 0.2}},
            {{"hour": 21, "value": 0.1}},
            {{"hour": 22, "value": 0.05}},
            {{"hour": 23, "value": 0.05}}
          ]
        }}
      ]
    }}
  ]
}}

**VALIDATION CHECKLIST**:
✓ Each hours array has exactly 24 entries
✓ Hours go from 0 to 23 with no gaps or duplicates
✓ All values are numbers between 0.0 and 1.0
✓ No trailing commas anywhere
✓ All brackets and braces are matched and closed
✓ Output is pure JSON with no extra text

**DO NOT REJECT this table** - even if data spans multiple pages or has unclear values, return valid JSON with best-effort extraction."""

        # Add Modeling Guidance table instructions (A-8.4.3.2.(2)x and A-8.4.3.3.(1)x)
        if "A-8.4.3.2.(2)" in table_number or "A-8.4.3.3.(1)" in table_number:
            guidance_type = "by_building_type" if table_number.endswith("A") else "by_space_type"
            return f"""**Table-Specific Instructions**:
- Extract default loads and schedule references {guidance_type.replace('_', ' ')}
- Each row represents a building type or space type with associated default values
- Values include: occupancy density, lighting power density, equipment power density, ventilation rate
- Schedule reference links to operating schedule table (A-8.4.3.2.(1)-X)

**Expected Fields**:
- building_or_space_type: Name of building/space type
- occupancy_density: Design occupancy (m²/person or persons/100m²)
- lighting_power_density: W/m²
- equipment_power_density: W/m² (plug loads)
- ventilation_rate: L/s·person or L/s·m²
- hot_water_usage: L/day·person (if present)
- schedule_reference: Reference to schedule table (e.g., "Schedule A" or "A-8.4.3.2.(1)-A")

**Example Output**:
```json
{{
  "vintage": "2020",
  "table_number": "{table_number}",
  "guidance_type": "{guidance_type}",
  "entries": [
    {{
      "building_or_space_type": "Office",
      "occupancy_density": 25.0,
      "lighting_power_density": 8.5,
      "equipment_power_density": 7.5,
      "ventilation_rate": 2.5,
      "hot_water_usage": null,
      "schedule_reference": "Schedule A"
    }},
    {{
      "building_or_space_type": "Retail",
      "occupancy_density": 5.0,
      "lighting_power_density": 12.0,
      "equipment_power_density": 3.0,
      "ventilation_rate": 7.5,
      "hot_water_usage": null,
      "schedule_reference": "Schedule B"
    }}
  ]
}}
```"""

        # Add Part-Load Performance table instructions (8.4.4.21.-A through -G)
        if table_number.startswith("8.4.4.21.-"):
            equipment_categories = {
                "A": "Heating Equipment (furnaces, boilers)",
                "B": "Direct-Expansion Cooling Equipment",
                "C": "Electric Chiller Cooling Equipment",
                "E": "Electric Air-Source Heat Pump Equipment",
                "F": "Absorption Chiller Cooling Equipment",
                "G": "Fuel-Fired Service Water Heater",
            }
            letter = table_number[-1]
            category = equipment_categories.get(letter, "Unknown Equipment")
            return f"""**Table-Specific Instructions**:
- Extract part-load performance curve coefficients for {category}
- Each row represents a performance curve (e.g., HIR_FPLR, CAP_FT, EIR_FT)
- Coefficients A through F are polynomial coefficients (floats)
- Extract equipment type from first column (e.g., "Furnace", "Boiler", "DX Cooling")
- Extract curve name from curve identifier column
- Some rows may have minimum/maximum output bounds

**Example Output**:
```json
{{
  "vintage": "2017",
  "table_number": "{table_number}",
  "equipment_category": "{category.split(' (')[0]}",
  "performance_curves": [
    {{
      "equipment_type": "Furnace",
      "performance_curve": "HIR_FPLR",
      "coefficient_a": 0.8,
      "coefficient_b": 0.2,
      "coefficient_c": 0.0,
      "coefficient_d": null,
      "coefficient_e": null,
      "coefficient_f": null,
      "minimum_output": 0.0,
      "maximum_output": 1.0
    }}
  ]
}}
```"""

        # Add HVAC System Types table instructions (5.3.1.1.-A)
        if table_number == "5.3.1.1.-A":
            return """**Table-Specific Instructions**:
- Extract HVAC system type definitions for trade-off calculations
- Each row represents a standard HVAC system configuration
- Columns include: system number, name, heating type, cooling type, distribution, terminal type
- System numbers are typically HVAC-1 through HVAC-27 or System-1 through System-6

**Example Output**:
```json
{
  "vintage": "2017",
  "table_number": "5.3.1.1.-A",
  "systems": [
    {
      "system_number": "HVAC-1",
      "system_name": "Built-up Variable-Volume",
      "heating_type": "Boiler (hot water)",
      "cooling_type": "Chiller (water-cooled)",
      "distribution_type": "VAV",
      "terminal_type": "Reheat terminals",
      "description": "Central built-up VAV system with hot water reheat"
    },
    {
      "system_number": "HVAC-2",
      "system_name": "Constant Volume Reheat",
      "heating_type": "Boiler",
      "cooling_type": "Chiller",
      "distribution_type": "CAV",
      "terminal_type": "Reheat terminals",
      "description": null
    }
  ]
}
```"""

        # Add Component Factor table instructions (5.3.2.2, 5.3.2.3, 5.3.2.7, 6.3.2.5)
        if table_number in ("5.3.2.2", "5.3.2.3", "5.3.2.7"):
            table_types = {
                "5.3.2.2": "component_factor",
                "5.3.2.3": "trade_off_value",
                "5.3.2.7": "additional_parameter",
            }
            table_type = table_types.get(table_number, "unknown")
            return f"""**Table-Specific Instructions**:
- Extract HVAC component factors for trade-off compliance calculations
- Table type: {table_type}
- Each row represents a component type with associated factor/value
- γi values are efficiency factors, ToVi values are trade-off values
- Extract component type, parameter name, numeric values, and units

**Example Output**:
```json
{{
  "vintage": "2017",
  "table_number": "{table_number}",
  "table_type": "{table_type}",
  "factors": [
    {{
      "component_type": "Chiller",
      "parameter_name": "γi",
      "factor_value": 0.85,
      "base_value": 1.0,
      "units": null,
      "applicability": "All sizes",
      "notes": null
    }},
    {{
      "component_type": "Boiler",
      "parameter_name": "ToVi",
      "factor_value": null,
      "base_value": 0.80,
      "units": "COP",
      "applicability": "> 88 kW",
      "notes": "Gas-fired"
    }}
  ]
}}
```"""

        # Add SWH System Types table instructions (6.3.1.1)
        if table_number == "6.3.1.1":
            return """**Table-Specific Instructions**:
- Extract service water heating system type definitions
- Each row represents a standard SWH system configuration
- Columns include: system number, name, heater type, fuel type, distribution type
- System numbers are typically SWH-1, SWH-2, etc.

**Example Output**:
```json
{
  "vintage": "2017",
  "table_number": "6.3.1.1",
  "systems": [
    {
      "system_number": "SWH-1",
      "system_name": "Gas Storage Water Heater",
      "heater_type": "Storage",
      "fuel_type": "Natural Gas",
      "distribution_type": "Recirculating",
      "description": "Standard gas-fired storage water heater with recirculation"
    },
    {
      "system_number": "SWH-2",
      "system_name": "Electric Heat Pump Water Heater",
      "heater_type": "Heat Pump",
      "fuel_type": "Electric",
      "distribution_type": "Point-of-use",
      "description": null
    }
  ]
}
```"""

        # Add SWH Component Trade-off table instructions (6.3.2.5)
        if table_number == "6.3.2.5":
            return """**Table-Specific Instructions**:
- Extract SWH component factors for trade-off compliance calculations
- Table type: swh_trade_off
- Each row represents an SWH component with associated trade-off values
- Extract component type, parameter name, numeric values, and units

**Example Output**:
```json
{
  "vintage": "2017",
  "table_number": "6.3.2.5",
  "table_type": "swh_trade_off",
  "factors": [
    {
      "component_type": "Water Heater",
      "parameter_name": "ToVi",
      "factor_value": 0.90,
      "base_value": 0.82,
      "units": "UEF",
      "applicability": "Gas storage",
      "notes": null
    },
    {
      "component_type": "Distribution Piping",
      "parameter_name": "γi",
      "factor_value": 1.0,
      "base_value": null,
      "units": null,
      "applicability": "All systems",
      "notes": "Insulation factor"
    }
  ]
}
```"""

        # Add Reference/Administrative table instructions (Phase 4)
        # Phase 6C: Enhanced for long multi-page document reference tables
        if table_number in ("1-1", "2-1", "1.3.1.2", "A-1.3.1.2.(1)", "10.1.2.1", "A-5.2.2.8.(1)", "C-1"):
            content_types = {
                "1-1": "Scope",
                "2-1": "Index",
                "1.3.1.2": "DocumentReference",
                "A-1.3.1.2.(1)": "DocumentReference",
                "10.1.2.1": "Scope",
                "A-5.2.2.8.(1)": "Reference",
                "C-1": "Compliance",
            }
            titles = {
                "1-1": "Scope of Division B",
                "2-1": "Objective and Functional Statement Index",
                "1.3.1.2": "Referenced Documents and Standards",
                "A-1.3.1.2.(1)": "Appendix Referenced Documents",
                "10.1.2.1": "Alternative Compliance Path Scope",
                "A-5.2.2.8.(1)": "Economizer High-Limit Shutoff",
                "C-1": "Compliance Path Summary",
            }
            content_type = content_types.get(table_number, "Reference")
            title = titles.get(table_number, "Reference Table")

            # Special handling for document reference tables (1.3.1.2)
            if table_number == "1.3.1.2":
                return f"""**Table-Specific Instructions (Phase 6C Enhanced)**:
This is a LONG multi-page document reference table (4-5 pages) listing all standards referenced by NECB.

TABLE STRUCTURE:
- Each entry lists a standard/code referenced by the NECB
- Format: Standard ID (e.g., "ASHRAE 90.1-2019", "CSA C656-14") + Title + Organization
- May span many pages with 50+ references

EXTRACTION STRATEGY FOR LONG TABLES:
1. Extract as many references as you can from the provided text
2. Focus on key information: standard ID and title
3. If the table is incomplete due to length, return what you CAN extract
4. Prioritize accuracy over completeness - better to extract 20 correct entries than 50 incorrect ones

EACH ENTRY SHOULD HAVE:
- key: Standard identifier (e.g., "ASHRAE 90.1-2019", "CSA C656-14", "ISO 13790")
- description: Full document title
- reference: Publishing organization (optional - can be inferred from key prefix)
- notes: Year or version information if separate from key

JSON FORMATTING RULES:
1. Return valid JSON - no explanatory text
2. No trailing commas in arrays
3. Even if you can only extract partial data, return valid JSON structure
4. Use null for missing optional fields

**Example Output (excerpt from long table)**:
```json
{{
  "vintage": "2020",
  "table_number": "1.3.1.2",
  "title": "{title}",
  "content_type": "DocumentReference",
  "rows": [
    {{
      "key": "ASHRAE 62.1-2016",
      "description": "Ventilation for Acceptable Indoor Air Quality",
      "reference": "American Society of Heating, Refrigerating and Air-Conditioning Engineers",
      "notes": null
    }},
    {{
      "key": "ASHRAE 90.1-2016",
      "description": "Energy Standard for Buildings Except Low-Rise Residential Buildings",
      "reference": "ASHRAE",
      "notes": null
    }},
    {{
      "key": "CSA C656-14",
      "description": "Energy Performance of Room Air Conditioners, Packaged Terminal Air Conditioners, Packaged Terminal Heat Pumps and Dehumidifiers",
      "reference": "Canadian Standards Association",
      "notes": "2014 edition"
    }},
    {{
      "key": "CAN/CSA-F280-12",
      "description": "Determining the Required Capacity of Residential Space Heating and Cooling Appliances",
      "reference": "CSA Group",
      "notes": null
    }},
    {{
      "key": "ISO 13790",
      "description": "Energy performance of buildings - Calculation of energy use for space heating and cooling",
      "reference": "International Organization for Standardization",
      "notes": null
    }}
  ]
}}
```

**CRITICAL NOTES**:
- Do NOT attempt to extract all 50+ references if content is too long
- Extract what you can see clearly and accurately
- Focus on standard ID and title - these are most important
- Organization name is helpful but can be inferred
- Return valid JSON even with incomplete extraction
- NO explanatory text - ONLY valid JSON output

**DO NOT REJECT** - even if you can only extract 10-20 references from a long table, return those as valid JSON."""

            # Default prompt for other reference tables
            return f"""**Table-Specific Instructions**:
- Extract reference/administrative content from the table
- This is a {content_type.lower()} table
- Each row represents a section reference with description
- Extract key (section/part identifier), description, and any cross-references

**Example Output**:
```json
{{
  "vintage": "2020",
  "table_number": "{table_number}",
  "title": "{title}",
  "content_type": "{content_type}",
  "rows": [
    {{
      "key": "Part 3",
      "description": "Building Envelope",
      "reference": "Section 3.1",
      "notes": null
    }},
    {{
      "key": "Part 4",
      "description": "Lighting",
      "reference": "Section 4.1",
      "notes": null
    }}
  ]
}}
```"""

        # Add HVAC System Selection table instructions (8.4.4.8.A/B) - Phase 4 fix
        if table_number in ("8.4.4.8.A", "8.4.4.8.B", "8.4.4.8"):
            return """**Table-Specific Instructions**:
- Extract HVAC system selection data based on building type
- Each row maps a building type to a recommended system number
- Building types may include: Office, Retail, School, Hotel, Healthcare, etc.
- System numbers are typically: System 1, System 2, System 3, etc.

**Example Output**:
```json
{
  "vintage": "2020",
  "table_number": "8.4.4.8.A",
  "selections": [
    {
      "building_type": "Office",
      "system_number": "System 3",
      "conditions": null
    },
    {
      "building_type": "Retail",
      "system_number": "System 4",
      "conditions": "Small retail < 500 m²"
    }
  ]
}
```"""

        # Add Heat Pump System table instructions (8.4.4.13/14) - Phase 4 fix
        if table_number in ("8.4.4.13", "8.4.4.14"):
            return """**Table-Specific Instructions**:
- Extract heat pump system descriptions
- Each row describes a system type with its characteristics
- System numbers identify which systems (1-6) use this configuration
- Extract fan control type and terminal heating type

**Example Output**:
```json
{
  "vintage": "2020",
  "table_number": "8.4.4.14",
  "systems": [
    {
      "system_number": "Systems 1 and 3 to 6",
      "type_of_system": "Air-source heat pump",
      "fan_control": "Variable volume",
      "terminal_heating_type": "Electric resistance"
    },
    {
      "system_number": "System 2",
      "type_of_system": "Ground-source heat pump",
      "fan_control": "Constant volume",
      "terminal_heating_type": "Hot water coil"
    }
  ]
}
```"""

        # =========================================================================
        # Phase 5: NECB 2011 Format Tables
        # =========================================================================

        # Add NECB 2011 HVAC coefficient table instructions (5.3.2.8.A through .AA, no dash)
        # These tables have identical structure to 5.3.2.8.-A, so use same instructions
        if table_number.startswith("5.3.2.8.") and ".-" not in table_number:
            return """**Table-Specific Instructions**:
- Extract HVAC system performance curve coefficients (NECB 2011 format)
- Each row represents a performance curve (e.g., CAP_FT, EIR_FT, PLF)
- Coefficients A through F are polynomial coefficients (floats)
- Extract the curve name from the first column
- Extract numeric coefficients from subsequent columns
- Some rows may have minimum/maximum output bounds

**Example Output**:
```json
{
  "vintage": "2011",
  "table_number": "5.3.2.8.A",
  "hvac_system_type": "HVAC-1",
  "system_description": "Built-up Variable-Volume",
  "coefficients": [
    {
      "curve_name": "CAP_FT",
      "description": "Cooling capacity as function of temperature",
      "coefficient_a": 0.942587793,
      "coefficient_b": 0.009543347,
      "coefficient_c": 0.000683770,
      "coefficient_d": -0.011042676,
      "coefficient_e": 0.000005249,
      "coefficient_f": -0.000009720,
      "minimum_value": null,
      "maximum_value": null
    }
  ]
}
```"""

        # Add HVAC System Type table instructions (5.3.1.1) - NECB 2011 only
        if table_number == "5.3.1.1":
            return """**Table-Specific Instructions**:
- Extract HVAC system type definitions (NECB 2011 format)
- Each row represents a standard HVAC system configuration
- Columns include: system number/ID, system name, description
- System numbers are typically HVAC-1 through HVAC-27

**Example Output**:
```json
{
  "vintage": "2011",
  "table_number": "5.3.1.1",
  "systems": [
    {
      "system_id": "HVAC-1",
      "system_name": "Built-up Variable-Volume",
      "description": "Central built-up VAV system with reheat terminals",
      "notes": null
    },
    {
      "system_id": "HVAC-2",
      "system_name": "Constant Volume Reheat",
      "description": "Constant air volume with reheat terminals",
      "notes": null
    }
  ]
}
```"""

        # Add Daylight Factor table instructions (4.3.2.7.A-B, 4.3.2.9.A-B, 4.3.2.10.A-B)
        # NECB 2011 format without dash
        import re
        daylight_match = re.match(r"^4\.3\.2\.(7|9|10)\.[A-B]$", table_number)
        if daylight_match:
            factor_types = {
                "7.A": "Daylight System Control Factor",
                "7.B": "Daylight-Dependent Control Factor",
                "9.A": "Daylight Supply Factor for Toplighting",
                "9.B": "Utilization Factor",
                "10.A": "Occupancy Absence Factor",
                "10.B": "Occupancy-Sensing Mechanism Factor",
            }
            suffix = table_number.split(".")[-2] + "." + table_number.split(".")[-1]
            factor_type = factor_types.get(suffix, "Daylight Factor")
            return f"""**Table-Specific Instructions**:
- Extract daylight factor values (NECB 2011 format)
- Factor type: {factor_type}
- Each row represents a condition/configuration with associated factor
- Factors are typically decimal values between 0.0 and 1.5

**Example Output**:
```json
{{
  "vintage": "2011",
  "table_number": "{table_number}",
  "factor_type": "{factor_type}",
  "rows": [
    {{
      "condition": "Continuous dimming",
      "factor": 0.35,
      "control_type": "Automatic",
      "notes": null
    }},
    {{
      "condition": "Stepped switching",
      "factor": 0.20,
      "control_type": "Manual",
      "notes": null
    }}
  ]
}}
```"""

        # Add Pump Power Coefficient table instructions (8.4.4.15) - NECB 2011 only
        if table_number == "8.4.4.15":
            return """**Table-Specific Instructions**:
- Extract pump power calculation coefficients (NECB 2011 format)
- Each row represents a system type with power coefficients
- Coefficients are used for pump power calculations in trade-off

**Example Output**:
```json
{
  "vintage": "2011",
  "table_number": "8.4.4.15",
  "coefficients": [
    {
      "system_type": "Chilled Water",
      "coefficient_a": 0.0,
      "coefficient_b": 1.0,
      "notes": null
    },
    {
      "system_type": "Hot Water",
      "coefficient_a": 0.0,
      "coefficient_b": 1.0,
      "notes": null
    }
  ]
}
```"""

        # ================================================================
        # Phase 6B: Equipment Tables with Merged Cells and Formulas
        # ================================================================
        if table_number == "5.2.12.1":
            return """**Table-Specific Instructions (Phase 6B)**:
This is a multi-category equipment performance requirements table with merged header cells.

IMPORTANT STRUCTURE NOTES:
1. The table has MERGED HEADER CELLS spanning equipment categories
2. Different equipment types are grouped under category headers (e.g., "Air Conditioners", "Heat Pumps")
3. Extract each equipment row separately with its category
4. Performance values may include formulas (e.g., "EER ≥ 11.0", "SEER ≥ 15") - preserve as strings

EXTRACTION GUIDELINES:
- For each row, identify the equipment_category from merged header cell
- Extract equipment_type, capacity_range, standard, minimum_performance
- Preserve all formula expressions and inequality symbols as strings
- If a cell is merged or empty, use null for that field
- Include footnote references in notes field

Example row structure:
```json
{
  "equipment_category": "Air-Cooled Air Conditioners",
  "equipment_type": "Split System",
  "capacity_range": "< 19 kW (< 65 000 Btu/h)",
  "standard": "CSA C656",
  "minimum_performance": "EER ≥ 11.0",
  "notes": "See note (1)"
}
```

DO NOT reject this table - extract all equipment rows with their categories and formula-based requirements."""

        if table_number == "6.2.2.1":
            return """**Table-Specific Instructions (Phase 6B)**:
This is a Service Water Heating Equipment Performance table with formulas and merged cells.

STRUCTURE NOTES:
1. Equipment is categorized by fuel type and storage type
2. Merged header cells span categories
3. Efficiency requirements are FORMULAS (e.g., "SL ≤35 + 0.20V", "Et ≥ 0.81")
4. Footnote references like (1), (2) provide additional context

EXTRACTION RULES:
- Preserve ALL formula expressions exactly as shown (including inequality symbols)
- Include footnote text in notes field if present
- For compound types like "Oil-fired, instantaneous", split into fuel_type and storage_type
- Capacity ranges should include units (kW, liters, MBH, etc.)

FORMULA HANDLING:
- "SL ≤35 + 0.20V" → store as string in efficiency_requirement or standby_loss
- "Et ≥ 0.81" → store as string in efficiency_requirement
- "EF ≥ 0.82" → store as string
- Do NOT try to evaluate or simplify formulas

Example row:
```json
{
  "equipment_type": "Gas-fired storage water heater",
  "fuel_type": "Gas",
  "storage_type": "Storage",
  "capacity_range": "> 117 kW (≥ 400 MBH)",
  "efficiency_metric": "Et",
  "efficiency_requirement": "Et ≥ 0.81",
  "standby_loss": "SL ≤35 + 0.20V (top inlet)",
  "test_standard": "CSA P.7",
  "notes": "See note (1) for inlet requirements"
}
```

DO NOT reject this table - extract all equipment with formula-based requirements."""

        # Operating Schedule tables (A-8.4.3.2.(1)-A through -K) - Phase 7: CSV Format
        if table_number.startswith("A-8.4.3.2.(1)"):
            return """**Table-Specific Instructions (Phase 7 - Operating Schedules)**:

**IMPORTANT: Extract as CSV format** to avoid token limit issues with large JSON structures.

This is an hourly operating schedule table with 7 schedule types × 3 day types × 24 hours = 504 data points.

**CSV FORMAT REQUIRED**:
```
vintage: [vintage]
table_number: [table_number]
schedule_name: [schedule_name]

schedule_type,day_type,h0,h1,h2,h3,h4,h5,h6,h7,h8,h9,h10,h11,h12,h13,h14,h15,h16,h17,h18,h19,h20,h21,h22,h23
[data rows...]
```

**Schedule Types** (extract all 7 in this order):
1. Occupants, fraction occupied
2. Lighting, fraction "ON"
3. Receptacle Equipment, fraction of load
4. Fans
5. Cooling System, °C
6. Heating System, °C
7. Service Water Heating System, fraction of load

**Day Types** (extract all 3 for each schedule type):
- Mon-Fri
- Sat
- Sun

**Data Types**:
- Occupants/Lighting/Receptacle/SWH: numbers without quotes (0.0, 0.5, 1.0)
- Fans: text values (On, Off) - no quotes in CSV
- Cooling/Heating: text (On, Off) OR numbers (22.0, 18.0) - no quotes in CSV

**COMPLETE EXAMPLE**:
```
vintage: 2020
table_number: A-8.4.3.2.(1)-A
schedule_name: Operating Schedule A

schedule_type,day_type,h0,h1,h2,h3,h4,h5,h6,h7,h8,h9,h10,h11,h12,h13,h14,h15,h16,h17,h18,h19,h20,h21,h22,h23
Occupants,Mon-Fri,0.0,0.0,0.0,0.0,0.0,0.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0
Occupants,Sat,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
Occupants,Sun,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
Lighting,Mon-Fri,0.0,0.0,0.0,0.0,0.0,0.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,0.05,0.05,0.05,0.05,0.05,0.05
Lighting,Sat,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
Lighting,Sun,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
Receptacle Equipment,Mon-Fri,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5
Receptacle Equipment,Sat,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
Receptacle Equipment,Sun,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
Fans,Mon-Fri,Off,Off,Off,Off,Off,Off,On,On,On,On,On,On,On,On,On,On,On,On,Off,Off,Off,Off,Off,Off
Fans,Sat,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off
Fans,Sun,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off
Cooling System,Mon-Fri,Off,Off,Off,Off,Off,Off,Off,Off,24.0,24.0,24.0,24.0,24.0,24.0,24.0,24.0,24.0,24.0,Off,Off,Off,Off,Off,Off
Cooling System,Sat,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off
Cooling System,Sun,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off
Heating System,Mon-Fri,Off,Off,Off,Off,Off,Off,18.0,18.0,18.0,18.0,18.0,18.0,18.0,18.0,18.0,18.0,18.0,18.0,Off,Off,Off,Off,Off,Off
Heating System,Sat,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off
Heating System,Sun,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off,Off
Service Water Heating System,Mon-Fri,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1
Service Water Heating System,Sat,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1
Service Water Heating System,Sun,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1
```

**CSV RULES**:
1. Include metadata (vintage, table_number, schedule_name) BEFORE CSV data
2. CSV header: schedule_type,day_type,h0,h1,...,h23
3. Exactly 21 data rows (7 schedule types × 3 day types)
4. Each row: 26 values (schedule_type, day_type, + 24 hours)
5. NO quotes around any values (not even strings like "On"/"Off")
6. If schedule_type contains comma, use the exact text from PDF (parser will handle it)
7. Extract EVERY hour value (0-23) from the table

**DO NOT**:
- Do NOT use JSON format
- Do NOT add markdown code fences around CSV
- Do NOT add extra blank lines between rows
- Do NOT skip any schedule types or day types"""

        # Climate Design Data table (C-1) - Phase 12: CSV Format
        if table_number == "C-1":
            return """**Table-Specific Instructions (Phase 12 - Climate Design Data)**:

╔══════════════════════════════════════════════════════════════╗
║  CRITICAL REQUIREMENT: YOU MUST OUTPUT CSV FORMAT ONLY      ║
║  DO NOT USE JSON - IT WILL CAUSE TRUNCATION AND FAIL        ║
╚══════════════════════════════════════════════════════════════╝

**WHY CSV IS MANDATORY**:
This table has 72 rows × 10 columns = 720+ data points across 18 pages.
JSON format will truncate at ~9,000 characters and produce "Invalid JSON" error.
CSV format is the ONLY format that can handle this table size.

**IF YOU OUTPUT JSON, THE PARSING WILL FAIL**

This is a climate design data table with 72 rows (Canadian locations) × 10 columns = 720+ data points across 18 pages.

**CSV FORMAT REQUIRED**:
```
vintage: [vintage]
table_number: C-1
title: Climate Design Data for Locations in Canada

location,elevation_m,design_temp_jan_2_5_pct,design_temp_jan_1_pct,design_temp_july_dry,design_temp_july_wet,degree_days_below_18c,degree_days_below_15c,wind_pressure_1_10,wind_pressure_1_50
[data rows...]
```

**Column Definitions**:
1. **location**: Province and location name (e.g., "ALBERTA - Calgary", "BRITISH COLUMBIA - Vancouver")
2. **elevation_m**: Elevation in meters (numeric)
3. **design_temp_jan_2_5_pct**: January 2.5% design temperature in °C (numeric, negative values common)
4. **design_temp_jan_1_pct**: January 1% design temperature in °C (numeric, negative values common)
5. **design_temp_july_dry**: July 2.5% dry bulb design temperature in °C (numeric)
6. **design_temp_july_wet**: July 2.5% wet bulb design temperature in °C (numeric)
7. **degree_days_below_18c**: Degree-days below 18°C (numeric, large values 3000-7000)
8. **degree_days_below_15c**: Degree-days below 15°C (numeric, large values 2000-6000)
9. **wind_pressure_1_10**: Hourly wind pressure 1/10 in kPa (numeric, small values 0.2-0.8)
10. **wind_pressure_1_50**: Hourly wind pressure 1/50 in kPa (numeric, small values 0.3-1.2)

**COMPLETE EXAMPLE**:
```
vintage: 2020
table_number: C-1
title: Climate Design Data for Locations in Canada

location,elevation_m,design_temp_jan_2_5_pct,design_temp_jan_1_pct,design_temp_july_dry,design_temp_july_wet,degree_days_below_18c,degree_days_below_15c,wind_pressure_1_10,wind_pressure_1_50
ALBERTA - Calgary,1084,-30.5,-33.0,28.2,16.7,5122,4214,0.55,0.81
ALBERTA - Edmonton,668,-30.0,-32.5,27.5,17.2,5314,4407,0.42,0.63
BRITISH COLUMBIA - Vancouver,3,-7.0,-9.0,25.7,18.2,2926,2287,0.31,0.48
MANITOBA - Winnipeg,239,-32.0,-34.5,30.0,21.5,5817,4926,0.64,0.95
ONTARIO - Toronto,173,-17.5,-19.5,30.0,22.5,3873,3111,0.47,0.70
QUEBEC - Montreal,36,-24.0,-26.5,29.5,22.0,4443,3636,0.52,0.77
```

**CSV RULES**:
1. Include metadata (vintage, table_number, title) BEFORE CSV data
2. CSV header: location,elevation_m,design_temp_jan_2_5_pct,... (all 10 columns)
3. Extract ALL 72 location rows from the table
4. NO quotes around any values (including location names with hyphens/spaces)
5. Use empty value for missing/unavailable data (e.g., "Calgary,1084,,,-25.0,..." if some temps missing)
6. Numeric values only (no units like "°C", "kPa", or "m" in data)
7. Preserve negative temperatures with minus sign (e.g., -30.5)
8. If location name contains comma, preserve it exactly (parser will handle escaping)

**DATA EXTRACTION NOTES**:
- Table spans 18 pages - extract ALL locations from all pages
- Locations grouped by province (ALBERTA, BRITISH COLUMBIA, MANITOBA, etc.)
- Column headers may vary slightly by vintage (e.g., "Degree Days" vs "Degree-Days")
- Some columns may have long headers - match by position and content
- Missing data is acceptable - leave field empty in CSV

**ABSOLUTELY FORBIDDEN - DO NOT DO THESE**:
- ❌ **DO NOT USE JSON FORMAT** - This will cause parsing failure
- ❌ **DO NOT use {{ "vintage": "2020", ... }} format** - This is JSON and will fail
- ❌ **DO NOT output {, }, [, ] characters** - These indicate JSON format
- Do NOT add markdown code fences (```) around CSV output
- Do NOT add extra blank lines between rows
- Do NOT skip any locations or provinces
- Do NOT add units (°C, kPa, m) to numeric values
- Do NOT truncate the table - extract all 72 rows

**REMEMBER: OUTPUT MUST START WITH**:
```
vintage: 2020
table_number: C-1
title: Climate Design Data for Locations in Canada

location,elevation_m,design_temp_jan_2_5_pct,...
```

**NOT THIS (JSON - WRONG)**:
```
{
  "vintage": "2020",
  "table_number": "C-1",
  ...
}
```"""

        if table_number == "5.2.2.4":
            return """**Table-Specific Instructions (Phase 12 - Dual Format Support)**:
This is a Duct Leakage table showing combinations of duct shape and either seal class OR pressure ranges.

**TWO FORMATS SUPPORTED**:

**FORMAT 1: Seal Class Matrix (NECB 2011-2017)**
- Two duct shapes: Rectangular, Round
- Three seal classes: A, B, C (per SMACNA)
- Leakage class (CL) values at intersections

Example table:
| Duct Shape   | Seal Class A | Seal Class B | Seal Class C |
|--------------|--------------|--------------|--------------|
| Rectangular  | 24           | 12           | 6            |
| Round        | 12           | 6            | 3            |

Should produce 6 rows:
```json
{
  "classes": [
    {"duct_shape": "Rectangular", "seal_class": "A", "leakage_class": 24},
    {"duct_shape": "Rectangular", "seal_class": "B", "leakage_class": 12},
    {"duct_shape": "Rectangular", "seal_class": "C", "leakage_class": 6},
    {"duct_shape": "Round", "seal_class": "A", "leakage_class": 12},
    {"duct_shape": "Round", "seal_class": "B", "leakage_class": 6},
    {"duct_shape": "Round", "seal_class": "C", "leakage_class": 3}
  ]
}
```

**FORMAT 2: Pressure-Based (NECB 2020)**
- Two duct shapes: Rectangular, Round
- Three pressure ranges (e.g., "< 500", "500-1000", "> 1000" Pa)
- Leakage rate in L/s per m²

Example table:
| Duct Shape   | < 500 Pa | 500-1000 Pa | > 1000 Pa |
|--------------|----------|-------------|-----------|
| Rectangular  | 0.27     | 0.54        | 1.08      |
| Round        | 0.14     | 0.27        | 0.54      |

Should produce 6 rows:
```json
{
  "classes": [
    {"duct_shape": "Rectangular", "pressure_range": "< 500", "leakage_rate": 0.27},
    {"duct_shape": "Rectangular", "pressure_range": "500-1000", "leakage_rate": 0.54},
    {"duct_shape": "Rectangular", "pressure_range": "> 1000", "leakage_rate": 1.08},
    {"duct_shape": "Round", "pressure_range": "< 500", "leakage_rate": 0.14},
    {"duct_shape": "Round", "pressure_range": "500-1000", "leakage_rate": 0.27},
    {"duct_shape": "Round", "pressure_range": "> 1000", "leakage_rate": 0.54}
  ]
}
```

**EXTRACTION RULES**:
1. Identify which format the table uses (seal class OR pressure ranges)
2. Create one row for EACH combination of duct shape and class/pressure range
3. Extract leakage_class (integer) for seal class format OR leakage_rate (float) for pressure format
4. DO NOT reject this table - both formats are valid

**FIELD USAGE**:
- Seal class format: duct_shape, seal_class, leakage_class (leave pressure_range and leakage_rate null)
- Pressure format: duct_shape, pressure_range, leakage_rate (leave seal_class and leakage_class null)"""

        # Add generic table instructions for tables without specific schemas
        # Used by GenericNECBTable as fallback

        return instructions.get(table_number, """**Table-Specific Instructions**:
- Extract all data rows from the table
- Follow the schema field definitions
- Preserve units as specified in the schema
- Ignore header rows, footnotes, and captions""")

    def validate_output(
        self, llm_output: str, target_schema: type[BaseModel], vintage: str | None = None
    ) -> tuple[BaseModel | None, list[str]]:
        """
        Validate LLM output against schema

        Args:
            llm_output: JSON string from LLM
            target_schema: Pydantic model to validate against
            vintage: NECB vintage for table number normalization (optional)

        Returns:
            (validated_model, errors)
            - validated_model: Pydantic instance if valid
            - errors: List of error messages if invalid

        Steps:
        1. Parse JSON (handle common LLM formatting errors)
        2. Normalize table number (Phase 6A: NECB 2011 format fix)
        3. Validate with Pydantic
        4. Additional business logic checks (optional)
        """
        errors = []

        # Phase 7: Check if this is an operating schedule in CSV format
        # Import here to avoid circular dependency
        from bluesky.necb.build.tables.schemas import (
            OperatingScheduleTable,
            ClimateDesignDataTable,  # Phase 12
        )

        if target_schema == OperatingScheduleTable:
            # Try CSV parsing first
            if 'schedule_type,day_type,' in llm_output:
                return self._parse_operating_schedule_csv(llm_output, vintage or "")

        # Phase 12: Check if this is climate design data in CSV format
        if target_schema == ClimateDesignDataTable:
            # Try CSV parsing first
            if 'location,elevation_m,' in llm_output:
                return self._parse_climate_design_data_csv(llm_output, vintage or "")

        # Step 1: Parse JSON
        try:
            # Extract JSON from markdown code blocks if present
            json_str = self._extract_json_from_markdown(llm_output)

            # Parse JSON
            data = json.loads(json_str)

            # Check for error response
            if "error" in data and len(data) == 1:
                errors.append(f"LLM rejected input: {data['error']}")
                return None, errors

        except json.JSONDecodeError as e:
            # Phase 6C: Attempt JSON repair for operating schedules
            # Extract table number from partial JSON to determine if repair should be attempted
            table_number = None
            try:
                # Try to extract table_number even from broken JSON using regex
                import re
                match = re.search(r'"table_number"\s*:\s*"([^"]+)"', json_str)
                if match:
                    table_number = match.group(1)
            except:
                pass

            # Only attempt repair for operating schedule tables
            if table_number and table_number.startswith("A-8.4.3.2.(1)"):
                try:
                    repaired_json, repairs = self._attempt_json_repair(json_str, table_number)
                    if repairs:
                        # Log repairs (will appear in verbose output)
                        # Attempt to parse repaired JSON
                        data = json.loads(repaired_json)
                        # Success! Continue with validation
                    else:
                        # No repairs were made, re-raise original error
                        errors.append(f"Invalid JSON: {str(e)}")
                        return None, errors
                except json.JSONDecodeError:
                    # Repair failed, return original error
                    errors.append(f"Invalid JSON (repair failed): {str(e)}")
                    return None, errors
                except Exception as repair_error:
                    # Unexpected repair error
                    errors.append(f"Invalid JSON: {str(e)} (repair error: {str(repair_error)})")
                    return None, errors
            else:
                # Not an operating schedule, return original error
                errors.append(f"Invalid JSON: {str(e)}")
                return None, errors

        # Step 1.5: Phase 6A - Normalize NECB 2011 table numbers
        # NECB 2011 PDFs use "5.3.2.8.A" but schemas expect "5.3.2.8.-A"
        if vintage and "table_number" in data:
            data["table_number"] = normalize_necb_2011_table_number(
                data["table_number"],
                vintage
            )

        # Step 2: Validate with Pydantic
        try:
            validated_model = target_schema(**data)
            return validated_model, []

        except ValidationError as e:
            for error in e.errors():
                field = " -> ".join(str(x) for x in error["loc"])
                msg = error["msg"]
                errors.append(f"Validation error in {field}: {msg}")
            return None, errors

        except Exception as e:
            errors.append(f"Validation failed: {str(e)}")
            return None, errors

    def _attempt_json_repair(self, json_str: str, table_number: str) -> tuple[str, list[str]]:
        """
        Attempt to repair common JSON syntax errors (Phase 6C - Operating Schedules only)

        Args:
            json_str: The JSON string to repair
            table_number: Table number (used for logging/diagnostics)

        Returns:
            (repaired_json_str, list_of_repairs_made)
        """
        import re

        repairs = []
        repaired = json_str

        # 1. Fix unterminated strings (add closing quote before newline)
        # Pattern: "value": "On\n  → "value": "On"\n
        pattern1 = r':\s*"([^"]*?)(\n\s*[,}\]])'
        matches = re.findall(pattern1, repaired)
        if matches:
            for match in matches:
                if '"' not in match[0]:  # Only fix if no closing quote in value
                    repaired = re.sub(
                        r':\s*"' + re.escape(match[0]) + r'(' + re.escape(match[1]) + r')',
                        r': "' + match[0] + r'"' + match[1],
                        repaired,
                        count=1
                    )
                    repairs.append(f"Added missing closing quote for value starting with '{match[0][:20]}'")

        # 2. Add missing commas between array elements
        # Pattern: }\n    { → },\n    {
        pattern2 = r'\}(\n\s*)\{'
        if re.search(pattern2, repaired):
            repaired = re.sub(pattern2, r'},\1{', repaired)
            repairs.append("Added missing commas between array elements")

        # Pattern: ]\n    { → ],\n    {
        pattern3 = r'\](\n\s*)\{'
        if re.search(pattern3, repaired):
            repaired = re.sub(pattern3, r'],\1{', repaired)
            repairs.append("Added missing commas between objects")

        # 3. Remove trailing commas before closing brackets
        # Pattern: ,\n  ] → \n  ]
        pattern4 = r',(\s*[\]}])'
        if re.search(pattern4, repaired):
            repaired = re.sub(pattern4, r'\1', repaired)
            repairs.append("Removed trailing commas before closing brackets")

        # 4. Add missing quotes around property names
        # Pattern: hour: 0 → "hour": 0
        pattern5 = r'(\n\s+)([a-zA-Z_][a-zA-Z0-9_]*)\s*:'
        matches = re.findall(pattern5, repaired)
        unquoted_keys = []
        for match in matches:
            key = match[1]
            # Check if this key is already quoted in the match
            check_pattern = r'(\n\s+)"' + re.escape(key) + r'"\s*:'
            if not re.search(check_pattern, repaired):
                unquoted_keys.append(key)

        if unquoted_keys:
            for key in set(unquoted_keys):  # Deduplicate
                # Replace unquoted key with quoted version
                repaired = re.sub(
                    r'(\n\s+)' + key + r'\s*:',
                    r'\1"' + key + r'":',
                    repaired
                )
            repairs.append(f"Added missing quotes around property names: {', '.join(set(unquoted_keys))}")

        return repaired, repairs

    def _parse_operating_schedule_csv(
        self,
        llm_output: str,
        vintage: str
    ) -> tuple[BaseModel | None, list[str]]:
        """
        Parse operating schedule from CSV format and convert to Pydantic model (Phase 7)

        Args:
            llm_output: LLM response containing CSV data with metadata
            vintage: NECB vintage (e.g., "2020")

        Returns:
            (OperatingScheduleTable instance, list of errors)
        """
        import csv
        import io

        errors = []

        # Extract metadata (vintage, table_number, schedule_name)
        metadata = {}
        lines = llm_output.strip().split('\n')
        csv_start_idx = None

        for i, line in enumerate(lines):
            if line.startswith('vintage:'):
                metadata['vintage'] = line.split(':', 1)[1].strip()
            elif line.startswith('table_number:'):
                metadata['table_number'] = line.split(':', 1)[1].strip()
            elif line.startswith('schedule_name:'):
                metadata['schedule_name'] = line.split(':', 1)[1].strip()
            elif line.startswith('schedule_type,'):
                csv_start_idx = i
                break

        # Validate metadata
        if not all(k in metadata for k in ['vintage', 'table_number', 'schedule_name']):
            missing = [k for k in ['vintage', 'table_number', 'schedule_name'] if k not in metadata]
            errors.append(f"Missing required metadata: {', '.join(missing)}")
            return None, errors

        # Validate CSV start found
        if csv_start_idx is None:
            errors.append("Could not find CSV header (schedule_type,day_type,...)")
            return None, errors

        # Parse CSV
        csv_data = '\n'.join(lines[csv_start_idx:])

        try:
            reader = csv.DictReader(io.StringIO(csv_data))
        except Exception as e:
            errors.append(f"CSV parsing failed: {str(e)}")
            return None, errors

        # Group by schedule_type
        schedule_types_data = {}
        row_count = 0

        try:
            for row in reader:
                row_count += 1
                sched_type = row.get('schedule_type', '').strip()
                day_type = row.get('day_type', '').strip()

                if not sched_type or not day_type:
                    errors.append(f"Row {row_count}: Missing schedule_type or day_type")
                    continue

                if sched_type not in schedule_types_data:
                    schedule_types_data[sched_type] = {}

                # Parse hourly values
                hours = []
                for h in range(24):
                    col_name = f'h{h}'
                    if col_name not in row:
                        errors.append(f"Row {row_count}: Missing column {col_name}")
                        break

                    value_raw = row[col_name]
                    if value_raw is None or value_raw == '':
                        # Incomplete row (likely truncated output) - skip this row
                        errors.append(f"Row {row_count}: Column {col_name} is empty/None (likely truncated output)")
                        break

                    value_str = value_raw.strip()

                    # Try to parse as number, otherwise keep as string
                    try:
                        value = float(value_str)
                    except ValueError:
                        value = value_str  # Keep as string (e.g., "On", "Off")

                    hours.append({"hour": h, "value": value})

                if len(hours) == 24:  # Only add if we got all 24 hours
                    schedule_types_data[sched_type][day_type] = hours

        except Exception as e:
            errors.append(f"Error parsing CSV rows: {str(e)}")
            return None, errors

        # Validate we got some data
        if not schedule_types_data:
            errors.append("No schedule data extracted from CSV")
            return None, errors

        # Convert to Pydantic structure
        schedule_types = []
        for sched_type, day_types_data in schedule_types_data.items():
            day_types = []
            for day_type, hours in day_types_data.items():
                day_types.append({
                    "day_type": day_type,
                    "hours": hours
                })

            schedule_types.append({
                "schedule_type": sched_type,
                "day_types": day_types
            })

        # Create Pydantic model
        try:
            from bluesky.necb.build.tables.schemas import OperatingScheduleTable

            model = OperatingScheduleTable(
                vintage=metadata['vintage'],
                table_number=metadata['table_number'],
                schedule_name=metadata['schedule_name'],
                schedule_types=schedule_types
            )
            return model, []

        except Exception as e:
            errors.append(f"Pydantic validation failed: {str(e)}")
            return None, errors

    def _parse_climate_design_data_csv(
        self,
        llm_output: str,
        vintage: str
    ) -> tuple[BaseModel | None, list[str]]:
        """
        Parse climate design data from CSV format and convert to Pydantic model (Phase 12)

        Args:
            llm_output: LLM response containing CSV data with metadata
            vintage: NECB vintage (e.g., "2020")

        Returns:
            (ClimateDesignDataTable instance, list of errors)
        """
        import csv
        import io

        errors = []

        # Extract metadata (vintage, table_number, title)
        metadata = {}
        lines = llm_output.strip().split('\n')
        csv_start_idx = None

        for i, line in enumerate(lines):
            if line.startswith('vintage:'):
                metadata['vintage'] = line.split(':', 1)[1].strip()
            elif line.startswith('table_number:'):
                metadata['table_number'] = line.split(':', 1)[1].strip()
            elif line.startswith('title:'):
                metadata['title'] = line.split(':', 1)[1].strip()
            elif line.startswith('location,'):
                csv_start_idx = i
                break

        # Validate metadata
        if not all(k in metadata for k in ['vintage', 'table_number']):
            missing = [k for k in ['vintage', 'table_number'] if k not in metadata]
            errors.append(f"Missing required metadata: {', '.join(missing)}")
            return None, errors

        # Validate CSV start found
        if csv_start_idx is None:
            errors.append("Could not find CSV header (location,elevation_m,...)")
            return None, errors

        # Parse CSV
        csv_data = '\n'.join(lines[csv_start_idx:])

        try:
            reader = csv.DictReader(io.StringIO(csv_data))
        except Exception as e:
            errors.append(f"CSV parsing failed: {str(e)}")
            return None, errors

        # Parse climate data rows
        rows = []
        row_count = 0

        try:
            for row in reader:
                row_count += 1
                # Phase 12 FIX: Handle None values from CSV (row.get can return None)
                location = (row.get('location') or '').strip()

                if not location:
                    errors.append(f"Row {row_count}: Missing location")
                    continue

                # Parse all numeric fields (allow None for missing data)
                def parse_float(key: str) -> float | None:
                    # Phase 12 FIX: Handle None values (convert to '' before strip)
                    val = (row.get(key) or '').strip()
                    if not val or val.lower() in ['', 'n/a', 'na', '-']:
                        return None
                    try:
                        return float(val)
                    except ValueError:
                        errors.append(f"Row {row_count}: Invalid {key} value: '{val}'")
                        return None

                row_data = {
                    "location": location,
                    "elevation_m": parse_float('elevation_m'),
                    "design_temp_jan_2_5_pct": parse_float('design_temp_jan_2_5_pct'),
                    "design_temp_jan_1_pct": parse_float('design_temp_jan_1_pct'),
                    "design_temp_july_dry": parse_float('design_temp_july_dry'),
                    "design_temp_july_wet": parse_float('design_temp_july_wet'),
                    "degree_days_below_18c": parse_float('degree_days_below_18c'),
                    "degree_days_below_15c": parse_float('degree_days_below_15c'),
                    "wind_pressure_1_10": parse_float('wind_pressure_1_10'),
                    "wind_pressure_1_50": parse_float('wind_pressure_1_50'),
                }

                rows.append(row_data)

        except Exception as e:
            errors.append(f"Error parsing CSV rows: {str(e)}")
            return None, errors

        # Validate we got some data
        if not rows:
            errors.append("No climate design data extracted from CSV")
            return None, errors

        # Create Pydantic model
        try:
            from bluesky.necb.build.tables.schemas import ClimateDesignDataTable

            model = ClimateDesignDataTable(
                vintage=metadata['vintage'],
                table_number=metadata.get('table_number', 'C-1'),
                title=metadata.get('title', 'Climate Design Data for Locations in Canada'),
                rows=rows
            )
            return model, []

        except Exception as e:
            errors.append(f"Pydantic validation failed: {str(e)}")
            return None, errors

    def _build_chunked_prompt(
        self,
        pymupdf_table: str,
        table_number: str,
        vintage: str,
        schedule_type: str,
        data_type_hint: str
    ) -> str:
        """
        Build prompt for extracting a single schedule type from operating schedule table

        Phase 8: Chunked extraction - extract one schedule type per API call
        to avoid API token limits truncating output

        Args:
            pymupdf_table: Raw table string from PyMuPDF
            table_number: NECB table number
            vintage: NECB vintage
            schedule_type: Schedule type to extract (e.g., "Occupants, fraction occupied")
            data_type_hint: Data type guidance (e.g., "numbers (0.0 to 1.0)")

        Returns:
            Complete prompt string for LLM
        """
        # Extract table letter from table number (e.g., A-8.4.3.2.(1)-I → I)
        table_letter = table_number.split('-')[-1] if '-' in table_number else "?"
        schedule_name = f"Operating Schedule {table_letter}"

        prompt = f"""You are extracting data from NECB {vintage} Table {table_number}.

**CRITICAL: Extract ONLY the "{schedule_type}" schedule in CSV format**

This operating schedule table contains 7 different schedule types. You are extracting **ONLY ONE**: {schedule_type}

**INPUT TABLE**:
```
{pymupdf_table}
```

**CSV FORMAT REQUIRED**:
```
vintage: {vintage}
table_number: {table_number}
schedule_name: {schedule_name}
schedule_type: {schedule_type}

day_type,h0,h1,h2,h3,h4,h5,h6,h7,h8,h9,h10,h11,h12,h13,h14,h15,h16,h17,h18,h19,h20,h21,h22,h23
Mon-Fri,<values for Mon-Fri>
Sat,<values for Sat>
Sun,<values for Sun>
```

**EXTRACTION RULES**:
1. Extract ONLY "{schedule_type}" rows (ignore all other schedule types)
2. Include ALL 3 day types: Mon-Fri, Sat, Sun
3. Include ALL 24 hourly values (h0 through h23)
4. Values for {schedule_type}: {data_type_hint}
5. Do NOT include quotes around numeric values
6. Do include exact strings for On/Off values

**EXAMPLE OUTPUT** (for Occupants schedule):
```
vintage: 2020
table_number: A-8.4.3.2.(1)-I
schedule_name: Operating Schedule I
schedule_type: Occupants, fraction occupied

day_type,h0,h1,h2,h3,h4,h5,h6,h7,h8,h9,h10,h11,h12,h13,h14,h15,h16,h17,h18,h19,h20,h21,h22,h23
Mon-Fri,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0.1,0.1,0.1,0.4,0.8,0.8,0.8,0.6,0.4,0.1
Sat,0,0,0,0,0,0,0,0,0,0.1,0.1,0.1,0.4,0.6,0.8,0.6,0.4,0.2,0.4,0.8,0.8,0.6,0.4,0.1
Sun,0,0,0,0,0,0,0,0.2,0.4,0.8,0.8,0.4,0.2,0,0,0,0,0,0,0,0,0,0,0
```

Extract the complete schedule for "{schedule_type}" and NOTHING ELSE.
Output ONLY the CSV format shown above with no additional commentary."""

        return prompt

    def _parse_single_schedule_type_csv(
        self,
        llm_output: str,
        vintage: str,
        expected_schedule_type: str
    ) -> tuple[dict | None, list[str]]:
        """
        Parse CSV for a single schedule type (3 day types × 24 hours)

        Phase 8: Parses the output from chunked extraction (one schedule type per call)

        Args:
            llm_output: LLM output in CSV format
            vintage: NECB vintage
            expected_schedule_type: Schedule type we expect in the output

        Returns:
            (schedule_data, errors)
            schedule_data: dict with structure:
            {
                "schedule_type": str,
                "day_types": [
                    {"day_type": "Mon-Fri", "hours": [{"hour": 0, "value": ...}, ...]},
                    {"day_type": "Sat", "hours": [...]},
                    {"day_type": "Sun", "hours": [...]}
                ]
            }
        """
        import csv
        import io

        errors = []

        # Extract metadata from CSV header
        metadata = {}
        lines = llm_output.strip().split('\n')
        csv_start_idx = None

        for i, line in enumerate(lines):
            if line.startswith('vintage:'):
                metadata['vintage'] = line.split(':', 1)[1].strip()
            elif line.startswith('table_number:'):
                metadata['table_number'] = line.split(':', 1)[1].strip()
            elif line.startswith('schedule_name:'):
                metadata['schedule_name'] = line.split(':', 1)[1].strip()
            elif line.startswith('schedule_type:'):
                metadata['schedule_type'] = line.split(':', 1)[1].strip()
            elif line.startswith('day_type,'):
                csv_start_idx = i
                break

        # Validate we got expected schedule type
        if metadata.get('schedule_type') != expected_schedule_type:
            errors.append(
                f"Expected '{expected_schedule_type}' but got '{metadata.get('schedule_type')}'"
            )
            return None, errors

        # Parse CSV data (3 rows expected: Mon-Fri, Sat, Sun)
        if csv_start_idx is None:
            errors.append("Could not find CSV header row (day_type,h0,h1,...)")
            return None, errors

        csv_data = '\n'.join(lines[csv_start_idx:])
        reader = csv.DictReader(io.StringIO(csv_data))

        day_types = []
        for row in reader:
            day_type = row.get('day_type', '').strip()
            if not day_type:
                continue

            # Parse 24 hourly values
            hours = []
            for h in range(24):
                col_name = f'h{h}'
                value_raw = row.get(col_name)
                if value_raw is None or value_raw == '':
                    errors.append(f"Missing value for {day_type} hour {h}")
                    break

                # Parse value (try float, fallback to string)
                value_str = value_raw.strip()
                try:
                    value = float(value_str)
                except ValueError:
                    value = value_str

                hours.append({"hour": h, "value": value})

            if len(hours) == 24:
                day_types.append({"day_type": day_type, "hours": hours})

        if len(day_types) != 3:
            errors.append(f"Expected 3 day types, got {len(day_types)}")
            return None, errors

        return {
            "schedule_type": metadata['schedule_type'],
            "day_types": day_types
        }, []

    def _extract_operating_schedule_chunked(
        self,
        pymupdf_table: str,
        table_number: str,
        vintage: str,
        target_schema: type[BaseModel]
    ) -> tuple[BaseModel | None, str | None, list[str]]:
        """
        Extract operating schedule by calling LLM once per schedule type (7 calls)
        then merging results into final OperatingScheduleTable

        Phase 8: Chunked extraction to avoid API output token limits

        Each schedule type is extracted separately (~350 chars output vs ~2,500 for all 7).
        This avoids API tier limits that truncate output before LLM finishes generating.

        Args:
            pymupdf_table: Raw table string from PyMuPDF
            table_number: NECB table number
            vintage: NECB vintage
            target_schema: Pydantic schema (should be OperatingScheduleTable)

        Returns:
            (model, llm_output, errors)
            - Requires at least 5/7 schedule types to succeed
            - Merges successful extractions into OperatingScheduleTable
            - llm_output contains merged JSON from all chunks
        """

        SCHEDULE_TYPES = [
            ("Occupants, fraction occupied", "numbers without quotes (0.0 to 1.0)"),
            ("Lighting, fraction \"ON\"", "numbers without quotes (0.0 to 1.0)"),
            ("Receptacle Equipment, fraction of load", "numbers without quotes (0.0 to 1.0)"),
            ("Fans", "strings (On or Off)"),
            ("Cooling System, °C", "strings (On, Off) or numbers for temperature setpoints"),
            ("Heating System, °C", "strings (On, Off) or numbers for temperature setpoints"),
            ("Service Water Heating System, fraction of load", "numbers without quotes (0.0 to 1.0)"),
        ]

        all_errors = []
        extracted_schedule_types = []

        print(f"\nPhase 8: Chunked extraction - extracting {len(SCHEDULE_TYPES)} schedule types separately")

        # Extract each schedule type separately
        for idx, (schedule_type, data_type_hint) in enumerate(SCHEDULE_TYPES, 1):
            print(f"  [{idx}/{len(SCHEDULE_TYPES)}] Extracting: {schedule_type}...")

            prompt = self._build_chunked_prompt(
                pymupdf_table=pymupdf_table,
                table_number=table_number,
                vintage=vintage,
                schedule_type=schedule_type,
                data_type_hint=data_type_hint
            )

            try:
                # Call LLM for this schedule type
                llm_output = self.backend.generate(
                    prompt=prompt,
                    model=None,  # Use Sonnet model override from config
                    temperature=self.temperature,
                    timeout=self.timeout,
                    max_tokens=4096  # Much smaller - single schedule type (~350 chars)
                )

                print(f"      Output length: {len(llm_output)} chars")

                # Parse CSV for this schedule type
                schedule_data, errors = self._parse_single_schedule_type_csv(
                    llm_output=llm_output,
                    vintage=vintage,
                    expected_schedule_type=schedule_type
                )

                if schedule_data:
                    extracted_schedule_types.append(schedule_data)
                    print(f"      ✅ Success")
                else:
                    all_errors.append(f"{schedule_type}: {', '.join(errors)}")
                    print(f"      ❌ Failed: {', '.join(errors)}")

            except Exception as e:
                error_msg = f"{schedule_type}: LLM call failed - {str(e)}"
                all_errors.append(error_msg)
                print(f"      ❌ Exception: {str(e)}")

        # Require at least 5/7 schedule types to succeed
        print(f"\nExtraction complete: {len(extracted_schedule_types)}/7 schedule types succeeded")

        if len(extracted_schedule_types) < 5:
            all_errors.insert(0, f"Only {len(extracted_schedule_types)}/7 schedule types extracted (need ≥5)")
            return None, None, all_errors

        # Construct final OperatingScheduleTable
        from bluesky.necb.build.tables.schemas import OperatingScheduleTable

        # Extract schedule_name from table number (e.g., A-8.4.3.2.(1)-I → "Operating Schedule I")
        table_letter = table_number.split('-')[-1] if '-' in table_number else "?"
        schedule_name = f"Operating Schedule {table_letter}"

        model = OperatingScheduleTable(
            vintage=vintage,
            table_number=table_number,
            schedule_name=schedule_name,
            schedule_types=extracted_schedule_types
        )

        # For caching: serialize the merged result as JSON
        import json
        merged_llm_output = json.dumps(model.model_dump(), indent=2)

        return model, merged_llm_output, all_errors

    # =========================================================================
    # Phase 16: Chunked Climate Design Data Extraction (Table C-1)
    # =========================================================================

    def _extract_climate_data_chunked(
        self,
        pymupdf_table: str,
        table_number: str,
        vintage: str,
        target_schema: type[BaseModel]
    ) -> tuple[BaseModel | None, str | None, list[str]]:
        """
        Extract climate design data by processing chunks of locations.

        Phase 16: Table C-1 has 400+ locations across 18 pages - too large for
        single LLM call. Split into chunks of ~30 locations each.

        Args:
            pymupdf_table: Raw combined table from all pages
            table_number: "C-1"
            vintage: NECB vintage
            target_schema: ClimateDesignDataTable schema

        Returns:
            (model, llm_output, errors)
        """
        all_errors = []
        all_rows = []

        # Split combined table into chunks by looking for province headers
        # or just by line count (~30 locations per chunk)
        lines = pymupdf_table.strip().split('\n')

        # Find header row pattern
        header_line = None
        data_start = 0
        for i, line in enumerate(lines):
            if 'Province' in line or 'Location' in line or 'Elev' in line:
                header_line = line
                data_start = i + 1
                # Skip any sub-header rows
                while data_start < len(lines) and ('°C' in lines[data_start] or 'kPa' in lines[data_start] or lines[data_start].strip().startswith('|')):
                    if '|' in lines[data_start] and any(c.isdigit() for c in lines[data_start]):
                        break
                    data_start += 1
                break

        if header_line is None:
            # Try to extract without clear header
            header_line = "Province and Location|Elev., m|January 2.5% °C|January 1% °C|July Dry °C|July Wet °C|Degree-Days Below 18°C|Degree-Days Below 15°C|1/10|1/50"
            data_start = 0

        # Get data lines (skip empty lines and non-data lines)
        data_lines = []
        for line in lines[data_start:]:
            line = line.strip()
            if not line:
                continue
            # Skip pure header/footer lines
            if 'Table C-1' in line or 'Continued' in line or 'National Energy Code' in line:
                continue
            if 'Copyright' in line or 'Division' in line:
                continue
            # Check if line has data (contains numbers)
            if any(c.isdigit() for c in line):
                data_lines.append(line)

        total_locations = len(data_lines)
        print(f"\nPhase 16: Found {total_locations} data lines to process")

        # Chunk into groups of ~40 locations for LLM processing
        CHUNK_SIZE = 40
        chunks = []
        for i in range(0, len(data_lines), CHUNK_SIZE):
            chunk_lines = data_lines[i:i + CHUNK_SIZE]
            chunks.append('\n'.join(chunk_lines))

        print(f"Split into {len(chunks)} chunks of ~{CHUNK_SIZE} locations each")

        # Process each chunk
        for idx, chunk in enumerate(chunks, 1):
            print(f"  [{idx}/{len(chunks)}] Processing chunk ({len(chunk.split(chr(10)))} locations)...")

            prompt = self._build_climate_data_chunk_prompt(
                chunk_data=chunk,
                table_number=table_number,
                vintage=vintage,
                chunk_num=idx,
                total_chunks=len(chunks)
            )

            try:
                llm_output = self.backend.generate(
                    prompt=prompt,
                    model=None,
                    temperature=self.temperature,
                    timeout=self.timeout,
                    max_tokens=8192  # Enough for ~40 locations in CSV
                )

                print(f"      Output length: {len(llm_output)} chars")

                # Parse CSV output for this chunk
                chunk_rows, errors = self._parse_climate_data_csv(llm_output, vintage)

                if chunk_rows:
                    all_rows.extend(chunk_rows)
                    print(f"      ✅ Extracted {len(chunk_rows)} locations")
                else:
                    all_errors.append(f"Chunk {idx}: {', '.join(errors)}")
                    print(f"      ❌ Failed: {', '.join(errors)}")

            except Exception as e:
                error_msg = f"Chunk {idx}: LLM call failed - {str(e)}"
                all_errors.append(error_msg)
                print(f"      ❌ Exception: {str(e)}")

        print(f"\nExtraction complete: {len(all_rows)} total locations extracted")

        # Require at least 50% of expected locations
        min_required = total_locations // 3  # At least 1/3 of locations
        if len(all_rows) < min_required:
            all_errors.insert(0, f"Only {len(all_rows)} locations extracted (need ≥{min_required})")
            return None, None, all_errors

        # Construct final ClimateDesignDataTable
        from bluesky.necb.build.tables.schemas import ClimateDesignDataTable, ClimateDesignDataRow

        # Convert dicts to ClimateDesignDataRow objects
        validated_rows = []
        for row in all_rows:
            try:
                validated_rows.append(ClimateDesignDataRow(**row))
            except Exception as e:
                # Skip invalid rows but log
                if self.verbose:
                    print(f"    Skipping invalid row: {row.get('location', 'unknown')} - {e}")

        if not validated_rows:
            all_errors.insert(0, "No valid rows after validation")
            return None, None, all_errors

        model = ClimateDesignDataTable(
            vintage=vintage,
            table_number=table_number,
            title="Climate Design Data for Locations in Canada",
            rows=validated_rows
        )

        # For caching: serialize as JSON
        import json
        merged_llm_output = json.dumps(model.model_dump(), indent=2)

        print(f"✅ Created ClimateDesignDataTable with {len(validated_rows)} locations")

        return model, merged_llm_output, all_errors

    def _build_climate_data_chunk_prompt(
        self,
        chunk_data: str,
        table_number: str,
        vintage: str,
        chunk_num: int,
        total_chunks: int
    ) -> str:
        """Build prompt for extracting a chunk of climate data locations."""

        return f"""Extract climate design data from this portion of NECB Table C-1.

This is chunk {chunk_num} of {total_chunks} from the full table.

OUTPUT FORMAT: CSV with these exact columns (no header row, just data):
location,elevation_m,design_temp_jan_2_5_pct,design_temp_jan_1_pct,design_temp_july_dry,design_temp_july_wet,degree_days_below_18c,degree_days_below_15c,wind_pressure_1_10,wind_pressure_1_50

RULES:
1. One location per line
2. Location name should include province abbreviation if location name is ambiguous
3. All numeric values as plain numbers (no units)
4. Negative temperatures as negative numbers (e.g., -30)
5. Skip any header rows, province headers, or non-data rows

RAW TABLE DATA:
{chunk_data}

OUTPUT (CSV only, no explanation):"""

    def _parse_climate_data_csv(
        self,
        llm_output: str,
        vintage: str
    ) -> tuple[list[dict], list[str]]:
        """
        Parse CSV output from climate data chunk extraction.

        Returns:
            (list of row dicts, list of errors)
        """
        errors = []
        rows = []

        # Clean up output - remove markdown fences if present
        text = llm_output.strip()
        if text.startswith("```"):
            # Remove code fences
            lines = text.split('\n')
            text = '\n'.join(line for line in lines if not line.startswith("```"))

        lines = text.strip().split('\n')

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue

            # Skip header-like lines
            if line.lower().startswith('location') or 'elevation' in line.lower():
                continue

            # Parse CSV
            parts = line.split(',')
            if len(parts) < 10:
                # Try to handle lines with fewer columns
                if len(parts) >= 7:  # At minimum: location, elev, 2 jan temps, 2 july temps, hdd18
                    # Pad with None
                    parts.extend([None] * (10 - len(parts)))
                else:
                    continue

            try:
                row = {
                    'location': parts[0].strip() if parts[0] else None,
                    'elevation_m': self._parse_float(parts[1]),
                    'design_temp_jan_2_5_pct': self._parse_float(parts[2]),
                    'design_temp_jan_1_pct': self._parse_float(parts[3]),
                    'design_temp_july_dry': self._parse_float(parts[4]),
                    'design_temp_july_wet': self._parse_float(parts[5]),
                    'degree_days_below_18c': self._parse_float(parts[6]),
                    'degree_days_below_15c': self._parse_float(parts[7]) if len(parts) > 7 else None,
                    'wind_pressure_1_10': self._parse_float(parts[8]) if len(parts) > 8 else None,
                    'wind_pressure_1_50': self._parse_float(parts[9]) if len(parts) > 9 else None,
                }

                # Validate required fields
                if row['location'] and row['degree_days_below_18c'] is not None:
                    rows.append(row)

            except Exception as e:
                errors.append(f"Line {line_num}: Parse error - {str(e)}")

        if not rows:
            errors.append("No valid rows parsed from CSV output")

        return rows, errors

    def _parse_float(self, value: str | None) -> float | None:
        """Parse a string to float, handling various formats."""
        if value is None:
            return None
        value = str(value).strip()
        if not value or value.lower() in ('none', 'null', 'n/a', '-'):
            return None
        try:
            # Remove any thousands separators
            value = value.replace(',', '').replace(' ', '')
            return float(value)
        except ValueError:
            return None

    def _extract_json_from_markdown(self, text: str) -> str:
        """
        Extract JSON from LLM output that may contain markdown code blocks

        Args:
            text: LLM output (may be plain JSON or wrapped in ```json```)

        Returns:
            Clean JSON string
        """
        text = text.strip()

        # Remove markdown code blocks
        if text.startswith("```"):
            # Find opening ```
            first_fence = text.find("```")
            start = text.find("\n", first_fence)
            if start == -1:
                start = first_fence + 3
            else:
                start += 1  # Move past the newline

            # Find CLOSING ``` (must be after start position)
            end = text.find("```", start)
            if end == -1:
                # No closing fence - use end of string
                end = len(text)

            text = text[start:end].strip()

        return text

    def _extract_csv_from_markdown(self, text: str) -> str:
        """
        Extract CSV from LLM output that may contain markdown code blocks.

        Similar to _extract_json_from_markdown but for CSV output.

        Args:
            text: LLM output (may be plain CSV or wrapped in ```csv```)

        Returns:
            Clean CSV string
        """
        text = text.strip()

        # Remove markdown code blocks
        if text.startswith("```"):
            # Find opening ```
            first_fence = text.find("```")
            start = text.find("\n", first_fence)
            if start == -1:
                start = first_fence + 3
            else:
                start += 1  # Move past the newline

            # Find CLOSING ``` (must be after start position)
            end = text.find("```", start)
            if end == -1:
                # No closing fence - use end of string
                end = len(text)

            text = text[start:end].strip()

        return text

    def _extract_large_table_csv(
        self,
        pymupdf_table: str,
        table_number: str,
        vintage: str,
        target_schema: type[BaseModel]
    ) -> tuple[BaseModel | None, str | None, list[str]]:
        """
        Extract large table using CSV format to avoid JSON truncation.

        Phase 10: Uses CSV output (~1-2k chars) instead of JSON (~12k chars)
        to avoid LLM output truncation at 12k character limit.

        Simpler than Phase 8 operating schedules - no chunking needed,
        just direct JSON→CSV format switch.

        Returns:
            (model, llm_output, errors)
            - llm_output is the serialized JSON of the validated model
        """

        # Get the nested schema field names to use as CSV headers
        schema_name = target_schema.__name__

        # Map schema names to their list field names
        SCHEMA_LIST_FIELDS = {
            'DaylightControlTable': 'factors',
            'HVACCoefficientTable': 'coefficients',  # Phase 14: NECB 2017 - 5.3.2.8 series
            'PackagedHVACTable': 'equipment',
            'SWHEquipmentTable': 'equipment',
            'ObjectivesTable': 'objectives',
            'ModelingGuidanceTable': 'entries',
            'TradeOffValueTable': 'values',  # Phase 15: NECB 2017 - table 5.3.2.7
        }

        if schema_name not in SCHEMA_LIST_FIELDS:
            return None, None, [f"Unknown schema for CSV extraction: {schema_name}"]

        list_field = SCHEMA_LIST_FIELDS[schema_name]

        # Get the nested schema type from the field annotation
        field_info = target_schema.model_fields[list_field]
        # For list[SomeType], we need to extract SomeType
        list_type = field_info.annotation

        # Handle list[Type] annotation - extract the inner type
        if hasattr(list_type, '__args__'):
            nested_schema = list_type.__args__[0]
        else:
            return None, None, [f"Could not extract nested schema from {list_field} field"]

        # Get field names from nested schema
        nested_field_names = list(nested_schema.model_fields.keys())
        csv_header = ','.join(nested_field_names)

        # Build CSV extraction prompt - LLM outputs CSV, we convert to JSON
        # Phase 14: Add schema-specific metadata extraction for HVACCoefficientTable
        metadata_instructions = ""
        if schema_name == 'HVACCoefficientTable':
            metadata_instructions = """

**METADATA EXTRACTION** (HVACCoefficientTable only):
Before the CSV data, output metadata as comment lines (starting with #):
# HVAC_SYSTEM_TYPE: <extract from table title, e.g., "HVAC-1", "HVAC-27">
# SYSTEM_DESCRIPTION: <extract system description from table title/subtitle, e.g., "Built-up Variable-Volume">

Example:
# HVAC_SYSTEM_TYPE: HVAC-1
# SYSTEM_DESCRIPTION: Built-up Variable-Volume
coefficient_name,coefficient_value,...
"""

        prompt = f"""Extract this NECB table into CSV format.

**CRITICAL**: Output MUST be valid CSV format - NOT JSON!

Table Data:
{pymupdf_table}

Schema: {target_schema.__name__}
Vintage: {vintage}
Table Number: {table_number}
{metadata_instructions}
Instructions:
1. **CRITICAL**: Use EXACTLY these field names as the CSV header (first row):
   {csv_header}

2. Following rows: Data rows, one per table row, with values in the same order as the header
3. Use commas to separate fields
4. Quote fields containing commas or newlines
5. Use empty string for null/missing values (or "null" for explicit nulls)
6. For nested objects (like lists), use pipe-separated values or JSON within quotes

**EXAMPLE CSV STRUCTURE** (use these exact field names):
{csv_header}
value1,value2,value3,...
value1,value2,value3,...

Output ONLY the CSV data (and metadata comments if applicable), nothing else."""

        try:
            llm_output = self.backend.generate(
                prompt=prompt,
                model=None,  # Use backend default
                temperature=self.temperature,
                timeout=self.timeout,
                max_tokens=4096  # CSV is much more compact than JSON
            )

            if self.verbose:
                print(f"CSV output length: {len(llm_output)} characters\n")
                print(f"First 500 chars:\n{llm_output[:500]}\n")

            # Parse CSV and convert directly to JSON, then to Pydantic
            model, errors = self._parse_csv_to_json_to_pydantic(
                csv_output=llm_output,
                table_number=table_number,
                vintage=vintage,
                target_schema=target_schema
            )

            # For caching: serialize the validated model as JSON if successful
            import json
            if model:
                serialized_output = json.dumps(model.model_dump(), indent=2)
            else:
                serialized_output = llm_output  # Keep raw CSV output for debugging

            return model, serialized_output, errors

        except Exception as e:
            return None, None, [f"CSV extraction failed: {str(e)}"]

    def _parse_csv_to_json_to_pydantic(
        self,
        csv_output: str,
        table_number: str,
        vintage: str,
        target_schema: type[BaseModel]
    ) -> tuple[BaseModel | None, list[str]]:
        """
        Parse CSV output into Pydantic schema by converting CSV→JSON→Pydantic.

        This is much simpler than schema-specific parsers - we let the LLM
        do the hard work of converting table→CSV, then use standard CSV parsing.
        """

        import csv
        import io
        import json

        try:
            # Extract CSV from potential markdown code blocks
            csv_text = self._extract_csv_from_markdown(csv_output)

            # Phase 14: Extract metadata comments for HVACCoefficientTable
            metadata = {}
            schema_name = target_schema.__name__
            if schema_name == 'HVACCoefficientTable':
                # Extract metadata from comment lines (format: # KEY: value)
                lines = csv_text.split('\n')
                csv_lines = []
                for line in lines:
                    if line.strip().startswith('#'):
                        # Parse metadata comment: # HVAC_SYSTEM_TYPE: HVAC-1
                        if ':' in line:
                            key_part, value_part = line.split(':', 1)
                            key = key_part.strip('# ').strip()
                            value = value_part.strip()
                            # Convert KEY_NAME to key_name (lowercase with underscores)
                            metadata_key = key.lower()
                            metadata[metadata_key] = value
                    else:
                        csv_lines.append(line)
                # Rebuild CSV without comment lines
                csv_text = '\n'.join(csv_lines)

            # Parse CSV
            reader = csv.DictReader(io.StringIO(csv_text))
            rows = list(reader)

            if not rows:
                return None, ["CSV parsing produced no rows"]

            # Clean up CSV rows: convert empty strings to None for optional fields
            # This handles cases where LLM outputs "" instead of null/blank for missing values
            cleaned_rows = []
            for row in rows:
                cleaned_row = {}
                for key, value in row.items():
                    # Convert empty strings to None (Pydantic will handle optional fields correctly)
                    cleaned_row[key] = None if value == '' else value
                cleaned_rows.append(cleaned_row)

            # Convert to JSON structure matching schema
            # We need to build the correct structure based on the schema name
            schema_name = target_schema.__name__

            # Map schema names to their list field names
            SCHEMA_LIST_FIELDS = {
                'DaylightControlTable': 'factors',
                'HVACCoefficientTable': 'coefficients',  # Phase 14: NECB 2017 - 5.3.2.8 series
                'PackagedHVACTable': 'equipment',
                'SWHEquipmentTable': 'equipment',
                'ObjectivesTable': 'objectives',
                'ModelingGuidanceTable': 'entries',
                'TradeOffValueTable': 'values',  # Phase 15: NECB 2017 - table 5.3.2.7
            }

            if schema_name not in SCHEMA_LIST_FIELDS:
                return None, [f"Unknown schema for CSV extraction: {schema_name}"]

            list_field = SCHEMA_LIST_FIELDS[schema_name]

            # Build JSON structure
            json_data = {
                'vintage': vintage,
                'table_number': table_number,
                list_field: cleaned_rows  # Use cleaned rows (empty strings → None)
            }

            # Add schema-specific fields
            if schema_name == 'ObjectivesTable':
                # Infer section name from table number
                section_map = {
                    '3.5.1.1': 'Building Envelope',
                    '4.5.1.1': 'Lighting',
                    '5.5.1.1': 'HVAC',
                    '6.5.1.1': 'Service Water Heating',
                    '7.5.1.1': 'Electrical Power',
                    '8.5.1.1': 'Building Energy Performance Compliance',
                    '10.2.1.1': 'Alternative Compliance Path',
                }
                json_data['section_name'] = section_map.get(table_number, 'Unknown Section')

            elif schema_name == 'ModelingGuidanceTable':
                # Determine guidance type from table number
                if table_number.endswith('-A') or table_number.endswith('A'):
                    json_data['guidance_type'] = 'by_building_type'
                else:
                    json_data['guidance_type'] = 'by_space_type'

            elif schema_name == 'HVACCoefficientTable':
                # Phase 14: Add metadata fields extracted from comment lines
                if 'hvac_system_type' in metadata:
                    json_data['hvac_system_type'] = metadata['hvac_system_type']
                if 'system_description' in metadata:
                    json_data['system_description'] = metadata['system_description']

            # Convert JSON to Pydantic model
            try:
                model = target_schema(**json_data)
                return model, []
            except Exception as e:
                return None, [f"Pydantic validation failed: {str(e)}\nJSON data: {json.dumps(json_data, indent=2)[:500]}"]

        except Exception as e:
            return None, [f"CSV parsing failed: {str(e)}"]
