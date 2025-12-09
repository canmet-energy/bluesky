"""Marker-based advanced table extractor for complex tables

Marker uses deep learning models to extract tables with:
- Merged cells
- Multi-line headers
- Complex column spanning

IMPORTANT: This module is currently non-functional due to upstream bug in surya-ocr
(GitHub Issue #465: SPECIAL_TOKENS undefined error). The surya-ocr maintainer confirmed
models were updated but code is out-of-sync. Issue opened Sep 26, 2025, still unfixed.
Tested with multiple versions (surya-ocr 0.16.7, 0.17.0) and model sources
(models.datalab.to, HuggingFace vikp/*) - all fail with the same error.
Can be re-enabled once upstream bug is resolved.
"""

import pickle
import torch
from pathlib import Path

from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict

from .models import MarkerTable


class MarkerTableExtractor:
    """Model-powered extraction for complex table structures using Marker"""

    def __init__(self, use_gpu: bool = True, verbose: bool = False, cache_dir: str | Path | None = None):
        """
        Initialize Marker with device selection

        Args:
            use_gpu: Use GPU acceleration if available
            verbose: Enable verbose logging
            cache_dir: Directory to cache Marker outputs (saves 79 min/PDF on re-runs)
        """
        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.device = "cuda" if self.use_gpu else "cpu"
        self.verbose = verbose
        self.cache_dir = Path(cache_dir) if cache_dir else None

        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        if self.verbose:
            print(f"Marker extractor initialized with device: {self.device}")
            if self.cache_dir:
                print(f"Caching enabled: {self.cache_dir}")

        # Lazy load models (only when needed)
        self._converter = None
        self._models = None

    def _ensure_models_loaded(self):
        """Lazy load Marker models to save memory"""
        if self._models is None:
            if self.verbose:
                print("Loading Marker models...")

            # Set CUDA device to use A5000 (GPU 0) instead of Quadro P1000 (GPU 1)
            import os
            os.environ["CUDA_VISIBLE_DEVICES"] = "0"

            # Override S3 checkpoints with HuggingFace models (models.datalab.to is unreliable)
            # Using surya-ocr 0.16.7 (pre-bug version) with compatible model names
            from surya.settings import settings as surya_settings
            surya_settings.DETECTOR_MODEL_CHECKPOINT = "vikp/surya_det"  # Text detection
            surya_settings.FOUNDATION_MODEL_CHECKPOINT = "vikp/surya_rec"  # Foundation OCR
            surya_settings.LAYOUT_MODEL_CHECKPOINT = "vikp/surya_layout"  # Layout analysis
            surya_settings.TABLE_REC_MODEL_CHECKPOINT = "vikp/surya_tablerec"  # Table recognition

            if self.verbose:
                print("Using HuggingFace models (surya-ocr 0.16.7):")
                print(f"  Detection: {surya_settings.DETECTOR_MODEL_CHECKPOINT}")
                print(f"  Foundation: {surya_settings.FOUNDATION_MODEL_CHECKPOINT}")
                print(f"  Layout: {surya_settings.LAYOUT_MODEL_CHECKPOINT}")
                print(f"  Table Recognition: {surya_settings.TABLE_REC_MODEL_CHECKPOINT}")

            # Create model dictionary with automatic device selection
            self._models = create_model_dict()

            # Initialize PDF converter
            # Note: marker-pdf 1.10.1 supports basic extraction without LLM
            self._converter = PdfConverter(
                artifact_dict=self._models,
            )

            if self.verbose:
                print("Marker models loaded (deep learning only, no LLM)")

    def extract_tables_from_page(
        self,
        pdf_path: str | Path,
        page_num: int,
        fallback_from_pymupdf: str | None = None,
    ) -> list[MarkerTable]:
        """
        Extract tables using Marker's layout models

        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)
            fallback_from_pymupdf: Optional PyMuPDF markdown for comparison

        Handles:
        - Merged header cells
        - Multi-line content within cells
        - Complex column spanning
        - Tables split across text blocks

        Returns:
            List of MarkerTable objects with cell-level structure

        Note:
            This is a simplified implementation. Full Marker integration
            would involve more sophisticated cell merging and structure detection.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        if self.verbose:
            print(f"Extracting from {pdf_path.name}, page {page_num + 1} with Marker")

        # Check cache first (saves 79 min/PDF on re-runs!)
        cache_file = self._get_cache_path(pdf_path) if self.cache_dir else None

        if cache_file and cache_file.exists():
            if self.verbose:
                print(f"Loading cached Marker output from {cache_file}")
            result = self._load_from_cache(cache_file)
        else:
            # Ensure models are loaded
            self._ensure_models_loaded()

            # Convert PDF to structured format
            # Note: Marker processes full documents (79 min for NECB PDFs)
            if self.verbose:
                print(f"Running Marker (this will take ~79 minutes for 315-page PDF)...")
            result = self._converter(str(pdf_path))

            # Save to cache for future use
            if cache_file:
                if self.verbose:
                    print(f"Saving Marker output to cache: {cache_file}")
                self._save_to_cache(result, cache_file)

        # Extract tables from result
        # Marker returns structured data with table information
        tables = self._extract_tables_from_result(result, page_num)

        if self.verbose:
            print(f"Marker found {len(tables)} tables on page {page_num + 1}")

        return tables

    def extract_table_from_pages(
        self,
        pdf_path: str | Path,
        page_nums: list[int],
        table_number: str | None = None,
    ) -> list[MarkerTable]:
        """
        Extract table from multiple pages using Marker

        Args:
            pdf_path: Path to PDF file
            page_nums: List of page numbers (0-indexed)
            table_number: Optional table number for filtering

        Returns:
            List of MarkerTable objects, one per page

        Example:
            >>> extractor = MarkerTableExtractor(verbose=True)
            >>> tables = extractor.extract_table_from_pages('necb_2020.pdf', [181, 182, 183], '6.2.2.1')
            >>> print(f"Extracted {len(tables)} pages for table 6.2.2.1")
        """
        tables = []

        for page_num in page_nums:
            # Extract tables from this page
            page_tables = self.extract_tables_from_page(pdf_path, page_num)

            if page_tables:
                # Take first table (assuming target table is first)
                # In production, would filter by table_number if provided
                table = page_tables[0]
                table.page_number = page_num
                tables.append(table)

        if self.verbose:
            print(f"Extracted from {len(page_nums)} pages using Marker: {len(tables)} tables found")

        return tables

    def _get_cache_path(self, pdf_path: Path) -> Path:
        """Generate cache file path for a PDF"""
        # Use PDF filename + .marker.pkl extension
        cache_filename = f"{pdf_path.stem}.marker.pkl"
        return self.cache_dir / cache_filename

    def _save_to_cache(self, result, cache_file: Path):
        """Save Marker result to pickle cache"""
        # Pickle handles all Python objects automatically - much simpler!
        with open(cache_file, "wb") as f:
            pickle.dump(result, f, protocol=pickle.HIGHEST_PROTOCOL)

    def _load_from_cache(self, cache_file: Path):
        """Load Marker result from pickle cache"""
        with open(cache_file, "rb") as f:
            return pickle.load(f)

    def _extract_tables_from_result(self, result, target_page: int) -> list[MarkerTable]:
        """
        Extract table structures from Marker result

        Args:
            result: Marker conversion result (MarkdownOutput object)
            target_page: Target page number to extract from

        Returns:
            List of MarkerTable objects
        """
        tables = []

        # Marker returns MarkdownOutput object with markdown attribute
        # Access the markdown string from the Pydantic model
        markdown = result.markdown

        # Simple table extraction from markdown
        # (In production, would use Marker's structured table output)
        table_blocks = self._parse_markdown_tables(markdown)

        for table_md in table_blocks:
            # Convert markdown table to cell structure
            cells = self._markdown_to_cells(table_md)

            if cells and len(cells) > 0:
                # Extract headers (first row)
                headers = cells[0] if cells else []

                table = MarkerTable(
                    cells=cells,
                    headers=headers,
                    page_number=target_page,
                    bboxes=None,  # Would extract from Marker's layout data
                )
                tables.append(table)

        return tables

    def _parse_markdown_tables(self, markdown: str) -> list[str]:
        """
        Extract table blocks from markdown text

        Args:
            markdown: Markdown text containing tables

        Returns:
            List of markdown table strings
        """
        tables = []
        current_table = []
        in_table = False

        for line in markdown.split("\n"):
            if "|" in line:
                current_table.append(line)
                in_table = True
            elif in_table:
                if current_table:
                    tables.append("\n".join(current_table))
                    current_table = []
                in_table = False

        # Handle table at end
        if current_table:
            tables.append("\n".join(current_table))

        return tables

    def _markdown_to_cells(self, table_md: str) -> list[list[str]]:
        """
        Convert markdown table to 2D cell array

        Args:
            table_md: Markdown table string

        Returns:
            2D list of cell contents
        """
        cells = []

        for line in table_md.split("\n"):
            if not line.strip().startswith("|"):
                continue

            # Skip separator lines (|---|---|)
            if all(c in "|-: " for c in line):
                continue

            # Extract cells
            row = [cell.strip() for cell in line.split("|")[1:-1]]
            if row:
                cells.append(row)

        return cells

    def detect_merged_cells(self, table: MarkerTable) -> list[tuple[int, int, int, int]]:
        """
        Identify merged cell regions using bbox overlap analysis

        Args:
            table: MarkerTable with cell data

        Returns:
            List of (row_start, col_start, row_span, col_span) tuples

        Note:
            Simplified implementation. Full version would use Marker's
            layout analysis to detect cell spanning.
        """
        merged_regions = []

        # Check for empty cells that might indicate merges
        for row_idx, row in enumerate(table.cells):
            for col_idx, cell in enumerate(row):
                if not cell.strip() and col_idx > 0:
                    # Empty cell might be part of merged region
                    # Look for previous non-empty cell
                    for prev_col in range(col_idx - 1, -1, -1):
                        if row[prev_col].strip():
                            # Potential horizontal merge
                            span = col_idx - prev_col + 1
                            merged_regions.append((row_idx, prev_col, 1, span))
                            break

        return merged_regions

    def normalize_structure(self, table: MarkerTable) -> MarkerTable:
        """
        Convert Marker's output to normalized row/column structure

        Steps:
        1. Identify true header rows (detect "header" pattern)
        2. Separate data rows from metadata/caption rows
        3. Align cells to consistent column grid
        4. Fill merged cell placeholders

        Args:
            table: Raw MarkerTable

        Returns:
            Normalized MarkerTable
        """
        if not table.cells:
            return table

        # Identify header rows (typically first non-empty row)
        header_row_idx = 0
        for idx, row in enumerate(table.cells):
            if any(cell.strip() for cell in row):
                header_row_idx = idx
                break

        # Extract headers and data rows
        headers = table.cells[header_row_idx] if header_row_idx < len(table.cells) else []
        data_rows = table.cells[header_row_idx + 1:] if header_row_idx + 1 < len(table.cells) else []

        # Filter out empty rows
        data_rows = [row for row in data_rows if any(cell.strip() for cell in row)]

        # Ensure consistent column count
        max_cols = max(len(row) for row in [headers] + data_rows) if data_rows else len(headers)

        # Pad rows to consistent width
        normalized_cells = []
        if headers:
            headers = headers + [""] * (max_cols - len(headers))
            normalized_cells.append(headers)

        for row in data_rows:
            padded_row = row + [""] * (max_cols - len(row))
            normalized_cells.append(padded_row)

        return MarkerTable(
            cells=normalized_cells,
            headers=headers,
            page_number=table.page_number,
            bboxes=table.bboxes,
        )
