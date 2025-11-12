"""PyMuPDF4LLM-based fast baseline table extractor"""

import re
from pathlib import Path

import pymupdf4llm

from .models import MarkdownTable, ValidationResult


class PyMuPDFTableExtractor:
    """Fast baseline table extraction using PyMuPDF4LLM"""

    def __init__(self, verbose: bool = False):
        """
        Initialize PyMuPDF extractor

        Args:
            verbose: Enable verbose logging
        """
        self.verbose = verbose

    def extract_tables_from_page(
        self, pdf_path: str | Path, page_num: int
    ) -> list[MarkdownTable]:
        """
        Extract all tables from a page as Markdown

        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)

        Returns:
            List of MarkdownTable objects with:
            - markdown_text: Raw table in MD format
            - estimated_rows: Number of data rows
            - estimated_cols: Number of columns
            - confidence: Quality score (0-1)
            - page_number: Page number

        Example:
            >>> extractor = PyMuPDFTableExtractor()
            >>> tables = extractor.extract_tables_from_page('necb_2020.pdf', 72)
            >>> print(f"Found {len(tables)} tables on page 73")
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        if self.verbose:
            print(f"Extracting from {pdf_path.name}, page {page_num + 1}")

        # Extract page as Markdown (PyMuPDF4LLM uses 0-indexed pages)
        try:
            md_text = pymupdf4llm.to_markdown(
                str(pdf_path), pages=[page_num], page_chunks=False
            )
        except Exception as e:
            if self.verbose:
                print(f"Extraction failed: {e}")
            return []

        # Split into individual tables
        tables = self._split_tables(md_text, page_num)

        if self.verbose:
            print(f"Found {len(tables)} tables on page {page_num + 1}")

        return tables

    def _split_tables(self, markdown_text: str, page_num: int) -> list[MarkdownTable]:
        """
        Split markdown text into individual table blocks

        Args:
            markdown_text: Markdown content from page
            page_num: Page number for attribution

        Returns:
            List of MarkdownTable objects
        """
        tables = []

        # Pattern: Match markdown tables (rows starting with |)
        # Tables are sequences of lines starting with | separated by blank lines
        lines = markdown_text.split("\n")
        current_table_lines = []
        in_table = False

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("|"):
                # Part of a table
                current_table_lines.append(line)
                in_table = True
            elif in_table and not stripped:
                # Blank line after table - end of table
                if current_table_lines:
                    table = self._parse_markdown_table(current_table_lines, page_num)
                    if table:
                        tables.append(table)
                    current_table_lines = []
                in_table = False
            elif in_table and stripped.startswith(("-", "=", "*")):
                # Separator line within table (common in markdown)
                current_table_lines.append(line)
            elif in_table:
                # Non-table line after table started - end table
                if current_table_lines:
                    table = self._parse_markdown_table(current_table_lines, page_num)
                    if table:
                        tables.append(table)
                    current_table_lines = []
                in_table = False

        # Handle table at end of text
        if current_table_lines:
            table = self._parse_markdown_table(current_table_lines, page_num)
            if table:
                tables.append(table)

        return tables

    def _parse_markdown_table(
        self, lines: list[str], page_num: int
    ) -> MarkdownTable | None:
        """
        Parse markdown table lines into MarkdownTable object

        Args:
            lines: Lines of markdown table
            page_num: Page number

        Returns:
            MarkdownTable object or None if invalid
        """
        if not lines:
            return None

        markdown_text = "\n".join(lines)

        # Count rows and columns
        data_rows = [
            line for line in lines if line.strip().startswith("|") and not self._is_separator(line)
        ]

        if not data_rows:
            return None

        # Estimate columns from first row
        first_row = data_rows[0]
        estimated_cols = first_row.count("|") - 1  # Subtract 1 for leading |

        # Estimated rows (exclude header and separator)
        estimated_rows = len(data_rows) - 1  # Assume first row is header

        # Calculate confidence score
        confidence = self._calculate_confidence(data_rows, estimated_cols)

        return MarkdownTable(
            markdown_text=markdown_text,
            estimated_rows=max(0, estimated_rows),
            estimated_cols=max(1, estimated_cols),
            confidence=confidence,
            page_number=page_num,
        )

    def _is_separator(self, line: str) -> bool:
        """Check if line is a markdown table separator (e.g., |---|---|)"""
        stripped = line.strip()
        if not stripped.startswith("|"):
            return False

        # Remove | characters and whitespace
        content = stripped.strip("|").strip()

        # Separator lines contain only - and : and whitespace
        return all(c in "-: " for c in content)

    def _calculate_confidence(self, rows: list[str], expected_cols: int) -> float:
        """
        Calculate extraction confidence based on table quality

        Args:
            rows: Table rows
            expected_cols: Expected number of columns

        Returns:
            Confidence score 0-1
        """
        if not rows:
            return 0.0

        # Check column consistency
        col_counts = [row.count("|") - 1 for row in rows]
        consistent_cols = all(count == expected_cols for count in col_counts)

        # Check for empty cells (potential extraction issues)
        empty_cell_pattern = re.compile(r"\|\s*\|")
        empty_cells = sum(len(empty_cell_pattern.findall(row)) for row in rows)
        total_cells = len(rows) * expected_cols
        empty_ratio = empty_cells / max(total_cells, 1)

        # Calculate confidence
        confidence = 1.0

        if not consistent_cols:
            confidence *= 0.7  # Inconsistent columns reduce confidence

        if empty_ratio > 0.2:  # More than 20% empty cells
            confidence *= 0.6

        if len(rows) < 2:  # Very short table
            confidence *= 0.5

        return max(0.0, min(1.0, confidence))

    def validate_extraction(
        self,
        table: MarkdownTable,
        min_rows: int = 1,
        min_cols: int = 2,
        min_confidence: float = 0.8,
    ) -> ValidationResult:
        """
        Validate extracted table against expected structure

        Args:
            table: Extracted MarkdownTable
            min_rows: Minimum expected data rows
            min_cols: Minimum expected columns
            min_confidence: Minimum confidence threshold

        Returns:
            ValidationResult with pass/fail status and errors

        Checks:
        - Column count matches minimum
        - Headers present and non-empty
        - Data rows >= minimum expected
        - No excessive blank cells (>20%)
        - Confidence above threshold
        """
        errors = []
        warnings = []

        # Check column count
        if table.estimated_cols < min_cols:
            errors.append(
                f"Too few columns: {table.estimated_cols} < {min_cols}"
            )

        # Check row count
        if table.estimated_rows < min_rows:
            errors.append(
                f"Too few rows: {table.estimated_rows} < {min_rows}"
            )

        # Check confidence
        if table.confidence < min_confidence:
            errors.append(
                f"Low confidence: {table.confidence:.2f} < {min_confidence}"
            )

        # Check for excessive empty cells
        empty_ratio = self._estimate_empty_ratio(table.markdown_text)
        if empty_ratio > 0.2:
            warnings.append(
                f"High empty cell ratio: {empty_ratio:.0%}"
            )

        # Check for malformed table
        if not table.markdown_text.strip().startswith("|"):
            errors.append("Malformed table: doesn't start with |")

        passed = len(errors) == 0

        return ValidationResult(
            passed=passed,
            errors=errors,
            warnings=warnings,
            confidence=table.confidence,
        )

    def _estimate_empty_ratio(self, markdown_text: str) -> float:
        """Estimate ratio of empty cells in markdown table"""
        # Count cells
        rows = [line for line in markdown_text.split("\n") if line.strip().startswith("|")]
        if not rows:
            return 0.0

        # Count empty cells (| |)
        empty_cell_pattern = re.compile(r"\|\s*\|")
        empty_cells = sum(len(empty_cell_pattern.findall(row)) for row in rows)

        # Estimate total cells
        total_cells = sum(row.count("|") - 1 for row in rows)

        return empty_cells / max(total_cells, 1)
