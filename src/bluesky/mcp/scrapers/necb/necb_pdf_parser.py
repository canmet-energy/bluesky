"""
NECB PDF Parser

Extracts structured data from NECB PDFs including:
- Table of contents and sections
- Tables (requirements, climate zones, U-values, etc.)
- Key requirements text

Implementation Notes:
- Uses Camelot-py for table extraction (as of 2025-11-07)
- Camelot (stream flavor) provides 100% data completeness vs. pdfplumber's 71%
- Critical fix: NECB 2017 Table 3.2.2.2 now extracts 14 rows instead of 4
- Parsing time: ~10 minutes per vintage (acceptable for batch operation)

See: docs/necb/parser-evaluation-results.md for evaluation details
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict
from multiprocessing import Pool, cpu_count

import camelot
import pdfplumber
from rich.console import Console
from rich.progress import track

console = Console()


@dataclass
class NECBSection:
    """Represents a section in NECB"""
    vintage: str
    section_number: str
    title: str
    content: str
    page_number: int


@dataclass
class NECBTable:
    """Represents a table in NECB"""
    vintage: str
    table_number: str
    title: str
    headers: List[str]
    rows: List[List[str]]
    page_number: int


@dataclass
class NECBRequirement:
    """Represents a specific requirement"""
    vintage: str
    section: str
    requirement_type: str  # e.g., "envelope", "hvac", "lighting", "climate_zone"
    description: str
    value: Optional[str]
    unit: Optional[str]


class NECBPDFParser:
    """Parser for NECB PDF documents"""

    def __init__(self, pdf_path: Path, vintage: str):
        self.pdf_path = pdf_path
        self.vintage = vintage
        self.sections: List[NECBSection] = []
        self.tables: List[NECBTable] = []
        self.requirements: List[NECBRequirement] = []

    def parse(self) -> Dict:
        """
        Parse the NECB PDF and extract all data

        Returns:
            Dictionary with sections, tables, and requirements
        """
        console.print(f"[cyan]Parsing NECB {self.vintage} ({self.pdf_path.name})...[/cyan]")

        # Get total pages using pdfplumber
        with pdfplumber.open(self.pdf_path) as pdf:
            total_pages = len(pdf.pages)

        console.print(f"  Total pages: {total_pages}")
        console.print(f"  Method: Camelot (stream flavor)")

        # Parse each page
        for page_num in track(range(1, total_pages + 1), description=f"NECB {self.vintage}"):
            # Extract tables using Camelot
            self._extract_tables_from_page(page_num)

            # Extract sections using pdfplumber (good for text)
            with pdfplumber.open(self.pdf_path) as pdf:
                page = pdf.pages[page_num - 1]
                self._extract_sections_from_page(page, page_num)

        # Extract specific requirements from parsed data
        self._extract_requirements()

        console.print(
            f"[green]  Extracted: {len(self.sections)} sections, "
            f"{len(self.tables)} tables, {len(self.requirements)} requirements[/green]"
        )

        return {
            "vintage": self.vintage,
            "sections": self.sections,
            "tables": self.tables,
            "requirements": self.requirements,
        }

    def _extract_tables_from_page(self, page_number: int):
        """
        Extract tables from a page using Camelot

        Args:
            page_number: Page number (1-indexed)

        Note: This method now uses Camelot instead of pdfplumber for better
              accuracy on complex NECB tables (especially multi-part tables
              like NECB 2017 Table 3.2.2.2).
        """
        try:
            # Extract tables using Camelot (stream flavor works best for NECB)
            tables = camelot.read_pdf(
                str(self.pdf_path),
                pages=str(page_number),
                flavor='stream',  # Best for NECB tables (with/without lines)
                edge_tol=50,      # Tolerance for detecting table edges
                row_tol=2,        # Tolerance for detecting rows
                column_tol=0      # Strict column detection
            )

            # Get page text for table metadata extraction
            # (Still use pdfplumber for text extraction - it's good at that)
            with pdfplumber.open(self.pdf_path) as pdf:
                page = pdf.pages[page_number - 1]
                page_text = page.extract_text() or ""

            # Process each extracted table
            for table_idx, camelot_table in enumerate(tables):
                # Convert Camelot table to our format
                df = camelot_table.df

                if df.empty or len(df) < 2:
                    continue

                # Clean table structure (remove title/metadata rows, identify actual headers)
                headers, rows = self._clean_table_structure(df)

                if not headers or not rows:
                    # Skip tables with no valid data
                    continue

                # Extract table number and title from page text
                table_number, title = self._extract_table_metadata(
                    page_text, page_number, table_idx
                )

                # Store table
                self.tables.append(NECBTable(
                    vintage=self.vintage,
                    table_number=table_number,
                    title=title,
                    headers=headers,
                    rows=rows,
                    page_number=page_number,
                ))

        except Exception as e:
            console.print(f"[yellow]Warning: Error extracting tables from page {page_number}: {e}[/yellow]")
            # Continue to next page (don't fail entire parse)

    def _clean_table_structure(self, df) -> tuple[List[str], List[List[str]]]:
        """
        Clean table structure by identifying actual headers and data rows.

        Camelot extracts the entire table region including titles and metadata.
        This method identifies:
        - The actual header row (column names)
        - The data rows (excluding title/metadata rows)

        Args:
            df: pandas DataFrame from Camelot

        Returns:
            Tuple of (headers, data_rows)
        """
        if df.empty:
            return [], []

        # Convert all cells to strings
        df = df.astype(str)

        # Strategy: Find ONLY rows where first column is a building component (Walls, Roofs, Floors, etc.)
        # These are the actual data rows. Everything else is metadata/titles.

        # Exact assembly names we're looking for
        assembly_names = ['walls', 'roofs', 'floors', 'windows', 'doors', 'skylights']

        data_rows = []
        data_indices = []

        for idx, row in df.iterrows():
            first_col = str(row.iloc[0]).strip().lower()

            # Check if first column exactly matches an assembly name
            if first_col in assembly_names:
                # Also check that rest of row has numeric data
                has_numbers = any(
                    cell.replace('.', '').replace(',', '').replace('≥', '').replace('≤', '').replace(' ', '').isdigit()
                    for cell in row.iloc[1:] if str(cell).strip()
                )

                if has_numbers:
                    row_data = [str(cell).strip() for cell in row]
                    data_rows.append(row_data)
                    data_indices.append(idx)

        # If we found data rows, find the header
        if data_rows:
            # Header is likely a few rows before first data row
            first_data_idx = data_indices[0]

            # Look backwards for header row (should have good fill ratio and contain zones/ranges)
            header_idx = None
            for back_idx in range(max(0, first_data_idx - 10), first_data_idx):
                row = df.iloc[back_idx]
                # Count non-empty cells
                non_empty = sum(1 for cell in row if str(cell).strip() != '')
                fill_ratio = non_empty / len(row)

                # Check if this row looks like a header (contains zone numbers, ranges, or degree symbols)
                row_text = ' '.join(str(cell) for cell in row).lower()
                has_header_keywords = any(kw in row_text for kw in ['zone', '< ', '> ', 'to ', '°', 'degree'])

                if fill_ratio >= 0.5 and has_header_keywords:
                    header_idx = back_idx
                    # Don't break - keep looking, we want the last good header before data

            if header_idx is not None:
                headers = [str(cell).strip() for cell in df.iloc[header_idx]]
            else:
                # Fallback: use row just before first data row
                if first_data_idx > 0:
                    headers = [str(cell).strip() for cell in df.iloc[first_data_idx - 1]]
                else:
                    # Create generic headers
                    headers = [f"Column {i}" for i in range(len(data_rows[0]))]

            return headers, data_rows

        # Fallback: if no assembly rows found, use original approach
        # (for tables that don't follow the typical structure)
        headers = df.iloc[0].tolist()
        headers = [str(h).strip() for h in headers]

        rows = df.iloc[1:].values.tolist()
        rows = [[str(cell).strip() for cell in row] for row in rows]

        return headers, rows

    def _extract_table_metadata(self, page_text: str, page_number: int, table_idx: int) -> tuple[str, str]:
        """
        Extract table number and title from page text.

        NECB tables follow various patterns:
            Table X.X.X.X.                    (standard tables)
            Table A-X.X.X.X.                  (Appendix A tables)
            Table A-X.X.X.X.(1)               (Appendix A with suffix)
            Title Text Here
            (optional: Forming Part of ...)

        Args:
            page_text: Full text of the page
            page_number: Current page number
            table_idx: Index of this table on the page

        Returns:
            Tuple of (table_number, title)
        """
        # Default fallback values
        default_number = f"Table-{page_number}-{table_idx}"
        default_title = "Untitled Table"

        # Look for NECB table number patterns:
        # - Standard: "Table 3.2.2.2.", "Table 4.2.1.5.A."
        # - Appendix: "Table A-3.2.1.4.", "Table A-3.2.1.4.(1)"
        # - Notes: "Table A-4.2.2.1.(11)"
        table_pattern = r'Table\s+([A-Z]?-?\d+(?:\.\d+)*(?:\.[A-Z])?\.(?:\(\d+\))?)'

        matches = list(re.finditer(table_pattern, page_text))

        # If we found table numbers, try to extract the corresponding title
        if table_idx < len(matches):
            match = matches[table_idx]
            table_number = f"Table {match.group(1)}"

            # Extract title - typically on lines following the table number
            # Look for text between table number and "Forming Part" or next table/section
            start_pos = match.end()

            # Find the end of the title (usually before "Forming Part" or next major element)
            end_markers = [
                r'\nForming Part',
                r'\nNotes to Table',
                r'\n\d+\.\d+',  # Next section number
                r'\nTable \d+',  # Next table
            ]

            end_pos = len(page_text)
            for marker in end_markers:
                marker_match = re.search(marker, page_text[start_pos:])
                if marker_match:
                    end_pos = min(end_pos, start_pos + marker_match.start())

            # Extract and clean title
            title_text = page_text[start_pos:end_pos].strip()
            # Take first few lines as title (usually 1-3 lines)
            title_lines = [line.strip() for line in title_text.split('\n')[:3] if line.strip()]
            title = ' '.join(title_lines) if title_lines else default_title

            # Remove extra whitespace and limit length
            title = re.sub(r'\s+', ' ', title)
            if len(title) > 200:
                title = title[:197] + "..."

            return table_number, title

        return default_number, default_title

    def _extract_sections_from_page(self, page, page_number: int):
        """Extract sections from a page"""
        text = page.extract_text()
        if not text:
            return

        # Look for section patterns like "3.2.1.1." or "Part 3"
        section_pattern = r'^(\d+(?:\.\d+)*\.?)\s+(.+)$'

        lines = text.split('\n')
        current_section = None
        current_content = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this is a section header
            match = re.match(section_pattern, line)
            if match:
                # Save previous section
                if current_section:
                    self.sections.append(NECBSection(
                        vintage=self.vintage,
                        section_number=current_section[0],
                        title=current_section[1],
                        content='\n'.join(current_content),
                        page_number=page_number,
                    ))

                # Start new section
                current_section = (match.group(1), match.group(2))
                current_content = []
            elif current_section:
                current_content.append(line)

        # Save last section
        if current_section:
            self.sections.append(NECBSection(
                vintage=self.vintage,
                section_number=current_section[0],
                title=current_section[1],
                content='\n'.join(current_content),
                page_number=page_number,
            ))

    def _extract_requirements(self):
        """Extract specific requirements from parsed data"""

        # Climate zones (look for climate zone table)
        for table in self.tables:
            if any("climate" in h.lower() and "zone" in h.lower() for h in table.headers):
                for row in table.rows:
                    if len(row) >= 2:
                        self.requirements.append(NECBRequirement(
                            vintage=self.vintage,
                            section="climate_zones",
                            requirement_type="climate_zone",
                            description=f"Climate Zone: {row[0]}",
                            value=row[1] if len(row) > 1 else None,
                            unit=None,
                        ))

        # U-value requirements (look for tables with U-value or RSI)
        for table in self.tables:
            if any("u-value" in h.lower() or "rsi" in h.lower() or "thermal" in h.lower() for h in table.headers):
                for row in table.rows:
                    if len(row) >= 2 and row[0]:
                        self.requirements.append(NECBRequirement(
                            vintage=self.vintage,
                            section="envelope",
                            requirement_type="u_value",
                            description=row[0],
                            value=row[1] if len(row) > 1 else None,
                            unit="W/m²·K" if "u-value" in str(table.headers).lower() else "m²·K/W",
                        ))

        # Lighting power density (look for LPD tables)
        for table in self.tables:
            if any("lighting" in h.lower() or "lpd" in h.lower() for h in table.headers):
                for row in table.rows:
                    if len(row) >= 2 and row[0]:
                        self.requirements.append(NECBRequirement(
                            vintage=self.vintage,
                            section="lighting",
                            requirement_type="lighting_power_density",
                            description=row[0],
                            value=row[1] if len(row) > 1 else None,
                            unit="W/m²",
                        ))


def _parse_single_pdf(args: tuple) -> tuple[str, Dict]:
    """
    Helper function to parse a single PDF (for multiprocessing)

    Args:
        args: Tuple of (pdf_path, vintage)

    Returns:
        Tuple of (vintage, parsed_data)
    """
    pdf_path, vintage = args
    parser = NECBPDFParser(pdf_path, vintage)
    data = parser.parse()
    return vintage, data


def parse_all_necb_pdfs(pdf_dir: Path, parallel: bool = True, max_workers: int = None) -> Dict[str, Dict]:
    """
    Parse all NECB PDFs in a directory

    Args:
        pdf_dir: Directory containing NECB PDFs
        parallel: Use multiprocessing for parallel parsing (default: True)
        max_workers: Maximum number of parallel workers (default: cpu_count())

    Returns:
        Dictionary mapping vintage to parsed data
    """
    vintages = ["2011", "2015", "2017", "2020"]

    # Build list of PDFs to parse
    pdf_tasks = []
    for vintage in vintages:
        pdf_path = pdf_dir / f"NECB-{vintage}.pdf"

        if not pdf_path.exists():
            console.print(f"[yellow]Warning: {pdf_path.name} not found[/yellow]")
            continue

        pdf_tasks.append((pdf_path, vintage))

    if not pdf_tasks:
        console.print("[red]No NECB PDFs found[/red]")
        return {}

    # Parse PDFs (parallel or sequential)
    if parallel and len(pdf_tasks) > 1:
        num_workers = min(max_workers or cpu_count(), len(pdf_tasks))
        console.print(f"[cyan]Parsing {len(pdf_tasks)} PDFs in parallel ({num_workers} workers)...[/cyan]")

        with Pool(num_workers) as pool:
            parse_results = pool.map(_parse_single_pdf, pdf_tasks)

        results = dict(parse_results)
    else:
        # Sequential parsing (original behavior)
        console.print(f"[cyan]Parsing {len(pdf_tasks)} PDFs sequentially...[/cyan]")
        results = {}
        for pdf_path, vintage in pdf_tasks:
            parser = NECBPDFParser(pdf_path, vintage)
            results[vintage] = parser.parse()

    return results


if __name__ == "__main__":
    pdf_dir = Path(__file__).parent / "pdfs"
    results = parse_all_necb_pdfs(pdf_dir)

    console.print("\n[bold cyan]NECB Parsing Summary:[/bold cyan]")
    for vintage, data in results.items():
        console.print(f"\n[bold]NECB {vintage}:[/bold]")
        console.print(f"  Sections: {len(data['sections'])}")
        console.print(f"  Tables: {len(data['tables'])}")
        console.print(f"  Requirements: {len(data['requirements'])}")
