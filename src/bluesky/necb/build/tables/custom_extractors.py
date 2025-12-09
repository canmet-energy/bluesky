"""Custom table extractors for complex NECB tables

This module provides specialized extraction logic for tables that don't work well
with the standard PyMuPDF → LLM repair pipeline. These are typically:
- Pure matrix tables with numeric data
- Multi-page tables that need special merging logic
- Tables with complex structures that confuse the LLM

Custom extractors bypass LLM repair and directly convert PyMuPDF output to
structured Pydantic models.
"""

from typing import Any

import fitz

from .pymupdf_extractor import PyMuPDFTableExtractor
from .schemas import TradeOffComponentFactorTable, TradeOffValueTable, PartLoadPerformanceTable


class CustomTableExtractor:
    """Registry of custom extractors for specific NECB tables"""

    def __init__(self, pymupdf: PyMuPDFTableExtractor):
        self.pymupdf = pymupdf

    def has_custom_extractor(self, table_number: str) -> bool:
        """Check if a custom extractor exists for the given table"""
        return table_number in ("5.3.2.2", "8.4.4.21.-G")

    def extract(
        self,
        table_number: str,
        vintage: str,
        pdf_path: str,
        page_num: int,
    ) -> tuple[bool, dict[str, Any] | None, list[str]]:
        """
        Extract table using custom logic

        Returns:
            (success, structured_data, errors)
        """
        if table_number == "5.3.2.2":
            return self._extract_5_3_2_2(vintage, pdf_path, page_num)
        elif table_number == "5.3.2.7":
            return self._extract_5_3_2_7(vintage, pdf_path, page_num)
        elif table_number == "8.4.4.21.-G":
            return self._extract_8_4_4_21_G(vintage, pdf_path, page_num)
        else:
            return False, None, [f"No custom extractor for table {table_number}"]

    def _extract_5_3_2_2(
        self, vintage: str, pdf_path: str, page_num: int
    ) -> tuple[bool, dict[str, Any] | None, list[str]]:
        """Extract Table 5.3.2.2 - Component Factors γi for Trade-off Calculations

        This is a matrix table with:
        - Rows: Trade-off Values (ToV1, ToV2, ..., ToV32)
        - Columns: HVAC System IDs (1-27)
        - Values: Binary factors (0 or 1)
        """
        try:
            # Extract table from PDF
            tables = self.pymupdf.extract_tables_from_page(pdf_path, page_num)
            if not tables:
                return False, None, ["No tables found on page"]

            # Parse the markdown table
            table = tables[0]  # Should be only one table on this page
            lines = table.markdown_text.strip().split("\n")

            # Find header row with HVAC System IDs
            # Looking for a row like: |Trade-off Value|1|2|3|4|...|27|
            header_row = None
            data_start = 0
            for i, line in enumerate(lines):
                if "|" not in line:
                    continue

                cells = [c.strip() for c in line.split("|") if c.strip()]
                if len(cells) < 10:  # Need at least 10 columns
                    continue

                # Check if cells[1:] contains consecutive integers starting from 1
                # Skip first cell (Trade-off Value label)
                try:
                    numeric_cells = []
                    for cell in cells[1:]:
                        if cell.isdigit():
                            numeric_cells.append(int(cell))

                    # Check if we have consecutive integers starting from 1
                    if numeric_cells and numeric_cells[0] == 1 and len(numeric_cells) >= 20:
                        # Verify they're consecutive
                        is_consecutive = all(
                            numeric_cells[j] == j + 1
                            for j in range(len(numeric_cells))
                        )
                        if is_consecutive:
                            header_row = cells
                            data_start = i + 2  # Skip separator line
                            break
                except:
                    continue

            if not header_row:
                return False, None, ["Could not find HVAC System ID header row"]

            # Extract HVAC System IDs (should be 1-27)
            system_ids = []
            for cell in header_row[1:]:  # Skip first column (Trade-off Value)
                if cell.isdigit():
                    system_ids.append(cell)

            # Parse data rows
            factors = []
            for line in lines[data_start:]:
                if not line.strip() or "|" not in line:
                    continue

                cells = [c.strip() for c in line.split("|") if c.strip()]
                if len(cells) < 2:
                    continue

                tov_id = cells[0]  # Trade-off Value (ToV1, ToV2, etc.)
                if not tov_id.startswith("ToV"):
                    continue

                # Parse factor values
                hvac_factors = {}
                for i, system_id in enumerate(system_ids):
                    if i + 1 < len(cells):
                        val_str = cells[i + 1].strip()
                        try:
                            hvac_factors[system_id] = float(val_str)
                        except:
                            hvac_factors[system_id] = 0.0

                factors.append(
                    {"trade_off_value": tov_id, "hvac_system_factors": hvac_factors}
                )

            # Construct structured data
            data = {"vintage": vintage, "table_number": "5.3.2.2", "factors": factors}

            # Validate with schema
            validated = TradeOffComponentFactorTable(**data)
            return True, validated.model_dump(), []

        except Exception as e:
            return False, None, [f"Extraction error: {str(e)}"]

    def _extract_5_3_2_7(
        self, vintage: str, pdf_path: str, page_num: int
    ) -> tuple[bool, dict[str, Any] | None, list[str]]:
        """Extract Table 5.3.2.7 - Trade-off Values by HVAC System

        This is a multi-page matrix table with:
        - Rows: HVAC System IDs (27 down to 1)
        - Columns: Trade-off Values (ToV5, ToV6, ToV15, etc.)
        - Values: Decimal factors

        Table spans pages 173-174, extracted as separate sections.
        """
        try:
            # Extract table from PDF
            tables = self.pymupdf.extract_tables_from_page(pdf_path, page_num)
            if not tables:
                return False, None, ["No tables found on page"]

            # Parse the markdown table
            table = tables[0]
            lines = table.markdown_text.strip().split("\n")

            # Find header row with ToV columns
            header_row = None
            data_start = 0
            for i, line in enumerate(lines):
                if "|" in line and "ToV" in line:
                    cells = [c.strip() for c in line.split("|") if c.strip()]
                    if any("ToV" in c for c in cells):
                        header_row = cells
                        data_start = i + 2  # Skip separator line
                        break

            if not header_row:
                return False, None, ["Could not find ToV header row"]

            # Extract ToV column names
            tov_columns = []
            for cell in header_row[1:]:  # Skip first column (HVAC System ID)
                if "ToV" in cell:
                    tov_columns.append(cell)

            # Parse data rows
            values = []
            for line in lines[data_start:]:
                if not line.strip() or "|" not in line:
                    continue

                cells = [c.strip() for c in line.split("|") if c.strip()]
                if len(cells) < 2:
                    continue

                try:
                    system_id = cells[0]
                    # Validate it's a system ID (should be 1-27)
                    if not system_id.isdigit() or int(system_id) < 1 or int(system_id) > 27:
                        continue
                except:
                    continue

                # Parse ToV values
                tov_values = {}
                for i, tov_name in enumerate(tov_columns):
                    if i + 1 < len(cells):
                        val_str = cells[i + 1].strip().replace(" ", "")  # Remove spaces
                        try:
                            tov_values[tov_name] = float(val_str)
                        except:
                            tov_values[tov_name] = val_str  # Keep as string if not numeric

                values.append({"hvac_system_id": system_id, "trade_off_values": tov_values})

            # Construct structured data
            # Determine page section (1 for page 173, 2 for page 174)
            page_section = 1 if page_num == 172 else 2  # 0-indexed

            data = {
                "vintage": vintage,
                "table_number": "5.3.2.7",
                "values": values,
                "page_section": page_section,
            }

            # Validate with schema
            validated = TradeOffValueTable(**data)
            return True, validated.model_dump(), []

        except Exception as e:
            return False, None, [f"Extraction error: {str(e)}"]

    def _extract_8_4_4_21_G(
        self, vintage: str, pdf_path: str, page_num: int
    ) -> tuple[bool, dict[str, Any] | None, list[str]]:
        """Extract Table 8.4.4.21.-G - Fuel-Fired Service Water Heater Part-Load Performance

        This is a formula-based table with equations and coefficient values embedded in text.
        We extract the PyMuPDF table structure and use LLM to parse formulas into LaTeX format.

        Structure: 1 row × 2 columns
        - Column 1: Equipment/Curve type (string)
        - Column 2: Formula text with equations and coefficients (converted to LaTeX)
        """
        try:
            # Extract tables from PDF page
            tables = self.pymupdf.extract_tables_from_page(pdf_path, page_num)
            if not tables:
                return False, None, ["No tables found on page"]

            # Get first table (Table 8.4.4.21.-G)
            table = tables[0]

            # Parse markdown table to get the 2-column structure
            lines = table.markdown_text.strip().split("\n")

            # Find the data row (skip header separator)
            data_row = None
            for line in lines:
                if "|" in line and "---" not in line:
                    cells = [c.strip() for c in line.split("|") if c.strip()]
                    if len(cells) >= 2:
                        data_row = cells
                        break

            if not data_row or len(data_row) < 2:
                return False, None, ["Could not parse table structure"]

            # Column 1: Equipment/curve type
            equipment_curve_type = data_row[0].replace('\n', ' ')

            # Column 2: Formula text (needs LaTeX conversion via LLM)
            formula_text = data_row[1]

            # Use LLM to convert formulas to LaTeX
            from anthropic import Anthropic
            client = Anthropic()

            prompt = f"""Convert the following NECB building code formula text to LaTeX format.

Input text:
{formula_text}

Return ONLY the LaTeX representation of the formulas and definitions, preserving all equations, variables, and coefficient values. Use proper LaTeX syntax for fractions, subscripts, equations, etc.

Example format:
The fuel consumption at part-load conditions:
$$\\text{{Fuel}}_{{\\text{{partload}}}} = \\text{{Fuel}}_{{\\text{{design}}}} \\times \\text{{FHeatPLC}}$$

where FHeatPLC is:
$$\\text{{FHeatPLC}} = a + b \\times \\frac{{Q_{{\\text{{partload}}}}}}{{Q_{{\\text{{design}}}}}} + c \\times \\left(\\frac{{Q_{{\\text{{partload}}}}}}{{Q_{{\\text{{design}}}}}}\\right)^2$$

Coefficients: $a = 0.021826$, $b = 0.977630$, $c = 0.000543$
"""

            response = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=2048,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}]
            )

            latex_formula = response.content[0].text.strip()

            # Create performance curve row with formula_text
            performance_curve = {
                "equipment_type": equipment_curve_type,
                "performance_curve": "FHeatPLC",  # Fuel Heating Part-Load efficiency Curve
                "coefficient_a": None,  # Stored in formula_text instead
                "coefficient_b": None,
                "coefficient_c": None,
                "coefficient_d": None,
                "coefficient_e": None,
                "coefficient_f": None,
                "minimum_output": None,
                "maximum_output": None,
                "formula_text": latex_formula,
            }

            # Construct structured data
            data = {
                "vintage": vintage,
                "table_number": "8.4.4.21.-G",
                "equipment_category": "SWH",
                "performance_curves": [performance_curve],
            }

            # Validate with schema
            validated = PartLoadPerformanceTable(**data)
            return True, validated.model_dump(), []

        except Exception as e:
            import traceback
            return False, None, [f"Extraction error: {str(e)}\n{traceback.format_exc()}"]
