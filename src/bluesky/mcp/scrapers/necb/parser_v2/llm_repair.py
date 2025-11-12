"""LLM-powered table repair and normalization

Uses local Ollama LLM to repair extraction errors and normalize table data
to target Pydantic schemas with strict validation.
"""

import json
from typing import Any

from ollama import Client
from pydantic import BaseModel, ValidationError

from .schemas import SCHEMA_REGISTRY, get_schema_for_table


class LLMTableRepairer:
    """LLM-powered table repair and schema mapping"""

    def __init__(
        self,
        model: str = "llama3.1:8b",
        temperature: float = 0.0,
        timeout: int = 30,
        verbose: bool = False,
    ):
        """
        Initialize LLM table repairer

        Args:
            model: Ollama model name (default: llama3.1:8b)
            temperature: Sampling temperature (0.0 for deterministic)
            timeout: Request timeout in seconds
            verbose: Enable verbose logging
        """
        self.client = Client()
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.verbose = verbose

        if self.verbose:
            print(f"LLM repairer initialized with model: {model}")

    def repair_and_normalize(
        self,
        raw_table: str,
        table_number: str,
        vintage: str,
        target_schema: type[BaseModel] | None = None,
    ) -> tuple[BaseModel | None, list[str]]:
        """
        Repair extracted table and map to target schema

        Args:
            raw_table: Extracted table (Markdown format from PyMuPDF)
            table_number: NECB table number (e.g., "3.2.2.2")
            vintage: NECB vintage (e.g., "2020")
            target_schema: Pydantic model defining output structure
                          (auto-detected if None)

        Returns:
            (validated_data, errors)
            - validated_data: Pydantic model instance if successful
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
                return None, errors

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
            # Query LLM
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": self.temperature,
                    "timeout": self.timeout,
                },
            )

            llm_output = response["response"]

            if self.verbose:
                print(f"LLM output length: {len(llm_output)} characters\n")
                print(f"First 500 chars:\n{llm_output[:500]}\n")

            # Validate output
            validated_data, validation_errors = self.validate_output(
                llm_output, target_schema
            )

            if validated_data:
                if self.verbose:
                    print(f"✅ Validation successful!")
                return validated_data, []
            else:
                errors.extend(validation_errors)
                if self.verbose:
                    print(f"❌ Validation failed:")
                    for error in validation_errors:
                        print(f"  - {error}")
                return None, errors

        except Exception as e:
            error_msg = f"LLM request failed: {str(e)}"
            errors.append(error_msg)
            if self.verbose:
                print(f"❌ {error_msg}")
            return None, errors

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
- Temperature ranges in °C
- Pipe diameters in mm (may be ranges like "≤ 25" or "40 to 65")
- Insulation thickness in mm""",
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

        return instructions.get(table_number, """**Table-Specific Instructions**:
- Extract all data rows from the table
- Follow the schema field definitions
- Preserve units as specified in the schema
- Ignore header rows, footnotes, and captions""")

    def validate_output(
        self, llm_output: str, target_schema: type[BaseModel]
    ) -> tuple[BaseModel | None, list[str]]:
        """
        Validate LLM output against schema

        Args:
            llm_output: JSON string from LLM
            target_schema: Pydantic model to validate against

        Returns:
            (validated_model, errors)
            - validated_model: Pydantic instance if valid
            - errors: List of error messages if invalid

        Steps:
        1. Parse JSON (handle common LLM formatting errors)
        2. Validate with Pydantic
        3. Additional business logic checks (optional)
        """
        errors = []

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
            errors.append(f"Invalid JSON: {str(e)}")
            return None, errors

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
            # Find first ```
            start = text.find("\n", text.find("```"))
            if start == -1:
                start = text.find("```") + 3

            # Find closing ```
            end = text.rfind("```")
            if end == -1:
                end = len(text)

            text = text[start:end].strip()

        return text
