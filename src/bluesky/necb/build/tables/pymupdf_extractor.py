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

    def extract_tables_from_pages(
        self, pdf_path: str | Path, page_nums: list[int]
    ) -> list[list[MarkdownTable]]:
        """
        Extract tables from multiple pages (for multi-page table handling)

        Args:
            pdf_path: Path to PDF file
            page_nums: List of page numbers (0-indexed)

        Returns:
            List of table lists, one per page
            Example: [[table1_p1], [table1_p2]] for 2-page table

        Example:
            >>> extractor = PyMuPDFTableExtractor()
            >>> pages_tables = extractor.extract_tables_from_pages('necb_2020.pdf', [161, 162])
            >>> print(f"Page 1: {len(pages_tables[0])} tables, Page 2: {len(pages_tables[1])} tables")
        """
        all_page_tables = []

        for page_num in page_nums:
            tables = self.extract_tables_from_page(pdf_path, page_num)
            all_page_tables.append(tables)

        if self.verbose:
            print(f"Extracted from {len(page_nums)} pages: " +
                  ", ".join(f"p{p+1}: {len(t)} tables" for p, t in zip(page_nums, all_page_tables)))

        return all_page_tables

    def _split_tables(self, markdown_text: str, page_num: int) -> list[MarkdownTable]:
        """
        Split markdown text into individual table blocks, including context before tables

        Args:
            markdown_text: Markdown content from page
            page_num: Page number for attribution

        Returns:
            List of MarkdownTable objects with table headings included
        """
        tables = []

        # Pattern: Match markdown tables (rows starting with |)
        # Also capture context lines before tables (e.g., "Table 3.2.2.3")
        lines = markdown_text.split("\n")
        current_table_lines = []
        context_lines = []  # Lines immediately before table
        in_table = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            if stripped.startswith("|"):
                # Start of table - include context if this is first row
                if not in_table:
                    # Add context lines (table title, etc.) before first table row
                    current_table_lines.extend(context_lines)
                    context_lines = []

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
                context_lines = []
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
                context_lines = []
            else:
                # Not in table - collect context lines
                # Keep last 3 non-blank lines as potential table context
                if stripped:
                    context_lines.append(line)
                    # Only keep last 3 non-blank lines
                    if len(context_lines) > 3:
                        context_lines.pop(0)
                # Don't reset context on blank lines - NECB PDFs have many blank lines
                # between table headings and tables

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

    def filter_table_by_number(
        self, tables: list[MarkdownTable], requested_table_number: str
    ) -> MarkdownTable | None:
        """
        Filter tables to find the one matching the requested table number

        Args:
            tables: List of extracted tables
            requested_table_number: Requested NECB table number (e.g., "5.2.12.1.-N")

        Returns:
            Matching MarkdownTable or None if not found

        Example:
            >>> tables = extractor.extract_tables_from_page('necb.pdf', 162)
            >>> table = extractor.filter_table_by_number(tables, "5.2.12.1.-N")
        """
        import re

        # Normalize requested table number for matching
        # Handle letter suffixes (e.g., "5.2.12.1.-N" or "5.2.12.1")
        normalized_requested = requested_table_number.strip()

        for table in tables:
            # Strip markdown bold markers to simplify matching
            # Markdown format: **Table** **5.2.12.1.-N**
            # We need: Table 5.2.12.1.-N
            clean_text = table.markdown_text.replace('**', ' ')

            # Extract table number from context lines
            # Pattern: "Table 5.2.12.1.-N" or "Table 5.2.12.1-N" or "Table A-3.2.1.4.(1)"
            patterns = [
                r'Table\s+([\dA-Z][\d\.\-A-Z\(\)]+)',  # General pattern
                r'Table\s+(\d+\.\d+\.\d+\.\d+[\.\-]*[A-Z]?)',  # 4-part with optional suffix
                r'Table\s+(A-\d+\.\d+\.\d+\.\d+\.\(\d+\))',  # Appendix with parens
            ]

            for pattern in patterns:
                match = re.search(pattern, clean_text, re.IGNORECASE)
                if match:
                    table_num = match.group(1)
                    # Clean up trailing dots
                    table_num = re.sub(r'[\.\-]+$', '', table_num)

                    # Check for exact match or normalized match
                    if table_num == normalized_requested:
                        return table

                    # Also try with dot before suffix (5.2.12.1.-N vs 5.2.12.1-N)
                    table_num_alt = re.sub(r'-([A-Z])$', r'.-\1', table_num)
                    if table_num_alt == normalized_requested:
                        return table

        return None

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

    def _table_contains_identifier(self, table: MarkdownTable, identifier: str) -> bool:
        """
        Check if a table's markdown contains the table identifier in a table caption

        Args:
            table: MarkdownTable to check
            identifier: Table identifier (e.g., "3.2.2.3")

        Returns:
            True if table markdown contains identifier in a table caption (not section refs)

        Note:
            Only matches table captions like "Table 3.2.2.3" or "**Table** **3.2.2.3**",
            not section references like "Division B 3.2.2.3" or identifiers in table data.
        """
        # Check only non-table rows (context lines before table)
        # Table rows start with |, so we check lines that DON'T start with |
        lines = table.markdown_text.split("\n")
        context_lines = [line.lower() for line in lines if not line.strip().startswith("|")]

        identifier_lower = identifier.lower()

        # Check for table caption patterns in context lines only
        # Must match: "Table X.X.X.X" or "TABLE X.X.X.X" (with optional markdown formatting)
        # Should NOT match: "Division B X.X.X.X" or other section references
        for line in context_lines:
            # Remove markdown formatting for cleaner matching
            cleaned = line.replace("*", "").replace("_", "").strip()

            # Look for "table" followed by the identifier within a reasonable distance
            # Pattern: "table" + optional whitespace/punctuation + identifier
            # Match "table 3.2.2.3" or "table 3.2.2.3" or "table:3.2.2.3" etc.
            pattern = rf'\btable\s*[:\-\s*_]*{re.escape(identifier_lower)}\b'
            if re.search(pattern, cleaned):
                # Also check it's not a division/section reference (exclude these keywords)
                if not any(keyword in cleaned for keyword in ["division", "part", "section", "clause"]):
                    return True

        return False

    def find_and_extract_table(
        self,
        pdf_path: str | Path,
        table_identifier: str,
        search_range: tuple[int, int] | None = None
    ) -> tuple[list[MarkdownTable], int | None]:
        """
        Automatically find and extract a table by searching for its identifier

        Args:
            pdf_path: Path to PDF file
            table_identifier: Table identifier to search for (e.g., "3.2.2.3", "Table 3.2.2.3")
            search_range: Optional (start_page, end_page) tuple to limit search (0-indexed)

        Returns:
            Tuple of (extracted_tables, page_number)
            - extracted_tables: List of MarkdownTable objects that contain the identifier
            - page_number: Page where table was found (0-indexed), or None if not found

        Example:
            >>> extractor = PyMuPDFTableExtractor(verbose=True)
            >>> tables, page = extractor.find_and_extract_table('necb_2020.pdf', '3.2.2.3')
            >>> if tables:
            >>>     print(f"Found table on page {page + 1}")

        Note:
            This method validates that extracted tables actually contain the identifier
            to avoid returning cross-references or unrelated tables.
        """
        import pymupdf  # Import PyMuPDF for text search

        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Open PDF for searching
        doc = pymupdf.open(str(pdf_path))

        # Prepare search patterns
        # Try multiple patterns to handle different formatting
        patterns = [
            f"Table {table_identifier}",
            f"TABLE {table_identifier}",
            f"table {table_identifier}",
            table_identifier,  # Just the number
        ]

        # Determine search range
        start_page = search_range[0] if search_range else 0
        end_page = search_range[1] if search_range else len(doc) - 1

        if self.verbose:
            print(f"Searching for table '{table_identifier}' in {pdf_path.name}")
            print(f"  Search range: pages {start_page + 1} to {end_page + 1}")

        # Store total pages before closing
        total_pages = len(doc)

        # Search each page for the table identifier
        # Continue searching even after finding first match to find the actual table
        candidate_pages = []
        for page_num in range(start_page, end_page + 1):
            page = doc[page_num]
            text = page.get_text()

            # Check if any pattern matches
            for pattern in patterns:
                if pattern in text:
                    candidate_pages.append(page_num)
                    if self.verbose:
                        print(f"  ✓ Found '{pattern}' on page {page_num + 1}")
                    break

        doc.close()

        # Try each candidate page and nearby pages
        for found_page in candidate_pages:
            # Extract tables from the found page
            tables = self.extract_tables_from_page(pdf_path, found_page)

            # Filter to only tables that contain the identifier
            matching_tables = [t for t in tables if self._table_contains_identifier(t, table_identifier)]

            if matching_tables:
                if self.verbose:
                    print(f"  ✓ Found {len(matching_tables)} matching table(s) on page {found_page + 1}")
                return matching_tables, found_page

            # If no matching tables on exact page, try nearby pages (±2)
            if self.verbose and tables:
                print(f"  Page {found_page + 1} has tables but none match '{table_identifier}'")
            if not matching_tables:
                if self.verbose:
                    print(f"  No matching tables on page {found_page + 1}, searching nearby pages...")

                for offset in [1, 2, -1, -2]:  # Check next 2 pages first, then previous
                    nearby_page = found_page + offset
                    if nearby_page < 0 or nearby_page >= total_pages:
                        continue

                    nearby_tables = self.extract_tables_from_page(pdf_path, nearby_page)
                    matching_nearby = [t for t in nearby_tables if self._table_contains_identifier(t, table_identifier)]

                    if matching_nearby:
                        if self.verbose:
                            print(f"  ✓ Found {len(matching_nearby)} matching table(s) on page {nearby_page + 1}")
                        return matching_nearby, nearby_page

        # No matching tables found
        if self.verbose:
            if candidate_pages:
                print(f"  ✗ Found text '{table_identifier}' on {len(candidate_pages)} page(s), but no tables contain it")
            else:
                print(f"  ✗ Table '{table_identifier}' not found")
        return [], None
