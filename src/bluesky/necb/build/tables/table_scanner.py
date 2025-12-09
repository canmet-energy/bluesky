"""NECB Table Scanner - Core scanning logic

This module provides the NECBTableScanner class for automated detection
of all tables in NECB PDFs using formatting-based detection.

The scanner uses bold + centered text detection to find table titles,
then handles multi-page tables by scanning for continuation markers.

Features:
    - Automatic table title detection
    - Multi-page table support with continuation detection
    - Notes page detection and correction
    - Backward/forward scanning for accurate page ranges
    - Handles table number variants (e.g., "5.2.12.1.-N" vs "5.2.12.1-N")

Example:
    >>> from pathlib import Path
    >>> scanner = NECBTableScanner()
    >>> tables = scanner.scan_pdf(Path("NECB-2020.pdf"))
    >>> print(f"Found {len(tables)} tables")
"""

import re
from pathlib import Path
from typing import Any

import fitz

from .pymupdf_extractor import PyMuPDFTableExtractor


class NECBTableScanner:
    """Scanner for automated NECB table detection in PDFs"""

    def __init__(self, verbose: bool = False):
        """
        Initialize NECB table scanner

        Args:
            verbose: Enable detailed progress output
        """
        self.verbose = verbose
        self.extractor = PyMuPDFTableExtractor(verbose=False)

    @staticmethod
    def is_text_bold(span: dict) -> bool:
        """
        Check if text span is bold

        Args:
            span: PyMuPDF span dictionary

        Returns:
            True if text is bold
        """
        font_name = span.get("font", "")
        if "Bold" in font_name or "bold" in font_name:
            return True

        flags = span.get("flags", 0)
        if flags & (1 << 4):  # bit 4 = bold
            return True

        return False

    @staticmethod
    def is_text_centered(bbox: tuple, page_width: float, tolerance: float = 0.3) -> bool:
        """
        Check if text is approximately centered on page

        Args:
            bbox: Bounding box (x0, y0, x1, y1)
            page_width: Page width in points
            tolerance: Center tolerance as fraction of page width

        Returns:
            True if text is centered
        """
        text_center = (bbox[0] + bbox[2]) / 2
        page_center = page_width / 2
        distance_ratio = abs(text_center - page_center) / page_width
        return distance_ratio < tolerance

    @staticmethod
    def extract_table_number(text: str) -> str | None:
        """
        Extract table number from title text, PRESERVING letter suffixes

        Args:
            text: Table title text

        Returns:
            Table number (e.g., "3.2.2.2", "5.2.12.1.-A", "A-3.2.1.4.(1)")

        Examples:
            "Table 3.2.2.2." -> "3.2.2.2"
            "Table 5.2.12.1.-A" -> "5.2.12.1.-A" (KEEP the -A suffix!)
            "Table A-3.2.1.4.(1)" -> "A-3.2.1.4.(1)"
        """
        patterns = [
            r'Table\s+([\dA-Z][\d\.\-A-Z\(\)]+)',  # General pattern
            r'Table\s+(\d+\.\d+\.\d+\.\d+)',       # 4-part numbers
            r'Table\s+(\d+\.\d+\.\d+)',            # 3-part numbers
            r'Table\s+(A-\d+\.\d+\.\d+\.\d+\.\(\d+\))',  # Appendix with parens
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                table_num = match.group(1)
                # Clean up trailing dots and dashes (but KEEP letter suffixes like -A, -B)
                table_num = re.sub(r'[\.\-]+$', '', table_num)
                return table_num

        return None

    @staticmethod
    def find_table_start_page(
        pdf_doc: fitz.Document,
        table_number: str,
        continuation_page: int,
        max_scan_back: int = 20
    ) -> int:
        """
        When we find a table at a continuation page, scan backwards to find the actual start page

        Args:
            pdf_doc: Open PDF document
            table_number: Table number to look for
            continuation_page: Page where we found "(Continued)" (0-indexed)
            max_scan_back: Maximum pages to scan backwards

        Returns:
            Start page number (0-indexed), or continuation_page if start not found
        """
        table_num_normalized = table_number.strip().rstrip('.')

        # Scan backwards from continuation_page
        for page_num in range(continuation_page - 1, max(0, continuation_page - max_scan_back) - 1, -1):
            page = pdf_doc[page_num]
            page_text = page.get_text()

            # Look for table number WITHOUT "(Continued)"
            start_patterns = [
                f"Table {table_num_normalized}\n",
                f"Table {table_num_normalized}.",
                f"Table {table_num_normalized} ",
            ]

            # Also try with dot-dash variants
            if '.-' in table_num_normalized:
                alt_num = table_num_normalized.replace('.-', '-')
                start_patterns.extend([
                    f"Table {alt_num}\n",
                    f"Table {alt_num}.",
                    f"Table {alt_num} ",
                ])

            # Check if we find table WITHOUT continuation marker
            found_start = False
            for pattern in start_patterns:
                if pattern in page_text:
                    # Make sure this is NOT a continuation page
                    if f"Table {table_num_normalized} (Continued)" not in page_text and \
                       f"Table {table_num_normalized}. (Continued)" not in page_text:
                        found_start = True
                        break

            if found_start:
                return page_num

        # If we didn't find start page, return the continuation page (best effort)
        return continuation_page

    @staticmethod
    def find_table_start_from_notes_page(
        pdf_doc: fitz.Document,
        table_number: str,
        notes_page: int,
        max_scan_back: int = 10
    ) -> int:
        """
        When we find "Notes to Table X.X.X", scan backwards to find the actual table start

        Args:
            pdf_doc: Open PDF document
            table_number: Table number to look for
            notes_page: Page where we found "Notes to Table X.X.X" (0-indexed)
            max_scan_back: Maximum pages to scan backwards

        Returns:
            Start page number (0-indexed), or notes_page if table start not found
        """
        table_num_normalized = table_number.strip().rstrip('.')

        # Scan backwards from notes_page
        for page_num in range(notes_page - 1, max(0, notes_page - max_scan_back) - 1, -1):
            page = pdf_doc[page_num]
            page_text = page.get_text()

            # Look for table number WITHOUT "Notes to Table" prefix
            table_patterns = [
                f"Table {table_num_normalized}\n",
                f"Table {table_num_normalized}.",
                f"Table {table_num_normalized} ",
            ]

            # Also try with dot-dash variants
            if '.-' in table_num_normalized:
                alt_num = table_num_normalized.replace('.-', '-')
                table_patterns.extend([
                    f"Table {alt_num}\n",
                    f"Table {alt_num}.",
                    f"Table {alt_num} ",
                ])

            # Check if we find the actual table (not Notes page)
            found_table = False
            for pattern in table_patterns:
                if pattern in page_text:
                    # Make sure this is NOT a notes page
                    if f"Notes to Table {table_num_normalized}" not in page_text and \
                       f"Notes to Table {alt_num if '.-' in table_num_normalized else table_num_normalized}" not in page_text:
                        found_table = True
                        break

            if found_table:
                return page_num

        # If we didn't find the actual table, return the notes page (best effort)
        return notes_page

    @staticmethod
    def scan_for_continuation_pages(
        pdf_doc: fitz.Document,
        table_number: str,
        start_page: int,
        max_scan: int = 20
    ) -> list[int]:
        """
        Scan forward from start_page to find all continuation pages for a table

        Args:
            pdf_doc: Open PDF document
            table_number: Table number to look for (e.g., "5.2.12.1.-N")
            start_page: Page where table first appears (0-indexed)
            max_scan: Maximum pages to scan forward (safety limit)

        Returns:
            List of page numbers (0-indexed) including start_page and all continuations
            Example: [161, 162] for a 2-page table
        """
        pages = [start_page]
        current_page = start_page + 1
        total_pages = len(pdf_doc)

        # Normalize table number for matching (remove trailing dots)
        table_num_normalized = table_number.strip().rstrip('.')

        while current_page < total_pages and current_page < start_page + max_scan:
            page = pdf_doc[current_page]
            page_text = page.get_text()

            # Look for continuation marker with table number
            continuation_patterns = [
                f"Table {table_num_normalized} (Continued)",
                f"Table {table_num_normalized}. (Continued)",
                f"Table{table_num_normalized} (Continued)",  # No space
            ]

            # Also try with dot-dash variants (5.2.12.1.-N vs 5.2.12.1-N)
            if '.-' in table_num_normalized:
                alt_num = table_num_normalized.replace('.-', '-')
                continuation_patterns.extend([
                    f"Table {alt_num} (Continued)",
                    f"Table {alt_num}. (Continued)",
                ])
            elif '-' in table_num_normalized and '.-' not in table_num_normalized:
                alt_num = table_num_normalized.replace('-', '.-', 1)
                continuation_patterns.extend([
                    f"Table {alt_num} (Continued)",
                    f"Table {alt_num}. (Continued)",
                ])

            # Check if any continuation pattern is found
            found_continuation = False
            for pattern in continuation_patterns:
                if pattern in page_text:
                    pages.append(current_page)
                    found_continuation = True
                    break

            # If no continuation found, stop scanning
            if not found_continuation:
                break

            current_page += 1

        return pages

    def scan_pdf(
        self,
        pdf_path: Path,
        start_page: int = 0,
        end_page: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Scan PDF for ALL tables using formatting detection

        Args:
            pdf_path: Path to NECB PDF file
            start_page: Start scan from page (0-indexed)
            end_page: End scan at page (0-indexed), None for end of document

        Returns:
            List of table metadata dictionaries with keys:
                - table_number: str (e.g., "3.2.2.2")
                - page_num: int (first page, 0-indexed, legacy field)
                - page_display: int (first page, 1-indexed)
                - page_start: int (start page, 0-indexed)
                - page_end: int (end page, 0-indexed)
                - all_pages: list[int] (all pages, 0-indexed)
                - page_count: int (number of pages)
                - title_text: str (table title)
                - table_description: str | None (optional description)
                - references: str | None (optional references)
                - has_forming_part: bool
                - has_continuation: bool
                - estimated_rows: int
                - estimated_cols: int
                - confidence: float
                - score: int
        """
        doc = fitz.open(pdf_path)

        if end_page is None:
            end_page = len(doc)

        tables_found = []

        for page_num in range(start_page, min(end_page, len(doc))):
            page = doc[page_num]
            page_dict = page.get_text("dict")
            page_width = page.rect.width
            page_text = page.get_text()

            # Look for bold + centered text containing "Table"
            for block in page_dict.get("blocks", []):
                if block.get("type") != 0:  # Not text
                    continue

                # Collect all lines in this block with metadata
                block_lines = []
                for line in block.get("lines", []):
                    line_text = ""
                    has_bold = False
                    line_bbox = None

                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        line_text += span_text

                        if self.is_text_bold(span):
                            has_bold = True

                        if line_bbox is None:
                            line_bbox = list(span["bbox"])
                        else:
                            line_bbox[0] = min(line_bbox[0], span["bbox"][0])
                            line_bbox[1] = min(line_bbox[1], span["bbox"][1])
                            line_bbox[2] = max(line_bbox[2], span["bbox"][2])
                            line_bbox[3] = max(line_bbox[3], span["bbox"][3])

                    block_lines.append({
                        'text': line_text.strip(),
                        'bbox': tuple(line_bbox) if line_bbox else None,
                        'has_bold': has_bold
                    })

                # Iterate with index so we can look ahead
                for i, line_data in enumerate(block_lines):
                    line_text = line_data['text']
                    line_bbox = line_data['bbox']
                    has_bold = line_data['has_bold']

                    # Check if this looks like a table title
                    if line_text and line_bbox and "Table" in line_text:
                        is_centered = self.is_text_centered(line_bbox, page_width)

                        if has_bold and is_centered:
                            table_number = self.extract_table_number(line_text)

                            if table_number:
                                # Capture 3-line metadata structure
                                table_description = None
                                references = None

                                # Look for description (line 2)
                                if i + 1 < len(block_lines):
                                    next_line = block_lines[i + 1]
                                    if next_line['bbox'] and self.is_text_centered(next_line['bbox'], page_width):
                                        table_description = next_line['text']

                                        # Look for references (line 3)
                                        if i + 2 < len(block_lines):
                                            next_next_line = block_lines[i + 2]
                                            if next_next_line['bbox'] and self.is_text_centered(next_next_line['bbox'], page_width):
                                                references = next_next_line['text']

                                # Check for additional signals
                                has_forming_part = (
                                    "Forming Part of Sentences" in page_text or
                                    "Forming Part of Sentence" in page_text
                                )
                                has_continuation = "(Continued)" in line_text
                                has_notes = line_text.startswith("Notes to Table")

                                # Try to extract table from this page
                                try:
                                    page_tables = self.extractor.extract_tables_from_page(pdf_path, page_num)

                                    if page_tables:
                                        table_info = page_tables[0]

                                        # Find actual start page (handle continuation/notes pages)
                                        actual_start_page = page_num
                                        if has_continuation:
                                            actual_start_page = self.find_table_start_page(
                                                pdf_doc=doc,
                                                table_number=table_number,
                                                continuation_page=page_num,
                                                max_scan_back=20
                                            )

                                        if has_notes:
                                            actual_start_page = self.find_table_start_from_notes_page(
                                                pdf_doc=doc,
                                                table_number=table_number,
                                                notes_page=page_num,
                                                max_scan_back=10
                                            )

                                        # Scan for continuation pages from the actual start
                                        all_pages = self.scan_for_continuation_pages(
                                            pdf_doc=doc,
                                            table_number=table_number,
                                            start_page=actual_start_page,
                                            max_scan=20
                                        )

                                        # Update has_continuation flag based on actual scan
                                        has_continuation = len(all_pages) > 1

                                        # Calculate score
                                        score = 100
                                        if has_forming_part:
                                            score += 50
                                        if not has_continuation:
                                            score += 30
                                        if line_text.strip().startswith("Table"):
                                            score += 20

                                        tables_found.append({
                                            'table_number': table_number,
                                            'page_num': page_num,  # First page (legacy)
                                            'page_display': page_num + 1,
                                            'page_start': all_pages[0],  # Start page
                                            'page_end': all_pages[-1],  # End page
                                            'all_pages': all_pages,  # All pages list
                                            'page_count': len(all_pages),  # Total pages
                                            'title_text': line_text,
                                            'table_description': table_description,
                                            'references': references,
                                            'has_forming_part': has_forming_part,
                                            'has_continuation': has_continuation,
                                            'estimated_rows': table_info.estimated_rows,
                                            'estimated_cols': table_info.estimated_cols,
                                            'confidence': table_info.confidence,
                                            'score': score,
                                        })

                                except Exception:
                                    pass  # Skip tables that fail extraction

        doc.close()
        return tables_found
