"""Hybrid NECB PDF Parser - Orchestrates PyMuPDF → Marker → LLM pipeline

This module combines:
1. PyMuPDF (fast baseline extraction)
2. Marker (advanced layout analysis for complex tables) - FALLBACK (currently disabled)
3. LLM repair and normalization (Claude API or Ollama)

Architecture (3-stage pipeline with intelligent fallback):
    PDF → PyMuPDF → LLM Repair → Validated JSON
           ↓ (if no tables found OR confidence < threshold)
        Marker → LLM Repair → Validated JSON  [DISABLED - see note below]

IMPORTANT: Marker fallback is currently disabled by default due to upstream bug in
surya-ocr (Issue #465: SPECIAL_TOKENS undefined). The surya-ocr maintainer confirmed
models were updated but code is out-of-sync.
PyMuPDF + LLM repair achieves ~99% success rate for NECB 2020.
Marker can be re-enabled via enable_marker=True once upstream bug is resolved.
"""

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .cache import TableCacheManager, create_cache_entry
from .config import ParserConfig
from .custom_extractors import CustomTableExtractor
from .llm_repair import LLMTableRepairer
from .pymupdf_extractor import PyMuPDFTableExtractor
from .schemas import get_schema_for_table

# Optional marker import (has heavy dependencies)
try:
    from .marker_extractor import MarkerTableExtractor
    MARKER_AVAILABLE = True
except ImportError:
    MarkerTableExtractor = None  # type: ignore
    MARKER_AVAILABLE = False


@dataclass
class ParseResult:
    """Result of parsing a single table"""

    success: bool
    data: BaseModel | None  # Validated Pydantic model
    table_number: str
    vintage: str
    page_number: int

    # Metadata
    method_used: str  # "pymupdf", "marker", or "failed"
    llm_applied: bool
    errors: list[str]
    timing: dict[str, float]  # Stage durations in seconds

    # Quality metrics
    confidence: float  # PyMuPDF extraction confidence (0-1)
    validation_passed: bool

    # Cached extraction data (enables schema iteration without re-parsing PDFs)
    raw_markdown: str | None = None  # PyMuPDF or Marker extraction
    repaired_markdown: str | None = None  # LLM-repaired output


@dataclass
class DocumentParseResult:
    """Result of parsing entire document"""

    tables: list[ParseResult]
    success_rate: float  # Percentage of tables successfully parsed
    total_duration: float  # seconds
    method_distribution: dict[str, int]  # Count by method


class HybridNECBParser:
    """Orchestrates PyMuPDF → Marker → LLM pipeline for NECB PDF parsing"""

    def __init__(
        self,
        config: ParserConfig | None = None,
        verbose: bool = False,
        enable_marker: bool = False,
        marker_cache_dir: str | Path | None = None,
        llm_cache_dir: str | Path | None = None,
        use_llm_cache: bool = True,
    ):
        """
        Initialize hybrid parser

        Args:
            config: Parser configuration (uses defaults if None)
            verbose: Enable verbose logging
            enable_marker: Enable Marker fallback for complex tables (default: False)
                         NOTE: Marker is currently disabled by default due to upstream bug
                         in surya-ocr (Issue #465: SPECIAL_TOKENS undefined error).
                         The surya-ocr maintainer confirmed models were updated but code
                         is out-of-sync. Issue opened Sep 26, 2025, still unfixed.
                         Can be re-enabled once upstream bug is resolved.
            marker_cache_dir: Directory to cache Marker outputs (saves ~79 min/PDF on re-runs)
            llm_cache_dir: Directory to cache LLM outputs (enables DB rebuilds without LLM calls)
            use_llm_cache: Whether to use cached LLM outputs when available (default: True)
        """
        self.config = config or ParserConfig()
        self.verbose = verbose
        self.enable_marker = enable_marker
        self.use_llm_cache = use_llm_cache

        # Initialize extractors
        self.pymupdf = PyMuPDFTableExtractor(verbose=verbose)
        self.custom_extractor = CustomTableExtractor(self.pymupdf)
        self.llm = LLMTableRepairer(
            backend=self.config.llm_backend,
            model=self.config.llm_model,
            temperature=self.config.llm_temperature,
            timeout=self.config.llm_timeout,
            api_key=self.config.llm_api_key,
            verbose=verbose,
            config=self.config,  # Phase 6C: pass config for table-specific model overrides
        )

        # Initialize LLM cache manager
        self.llm_cache = None
        if llm_cache_dir:
            self.llm_cache = TableCacheManager(llm_cache_dir, verbose=verbose)

        # Initialize Marker (lazy loading - only loads models when needed)
        self.marker = None
        self.marker_cache_dir = marker_cache_dir
        if self.enable_marker and MARKER_AVAILABLE and MarkerTableExtractor is not None:
            self.marker = MarkerTableExtractor(
                use_gpu=True,
                verbose=verbose,
                cache_dir=marker_cache_dir,
            )

        if self.verbose:
            print(f"Hybrid parser initialized")
            print(f"  LLM backend: {self.config.llm_backend}")
            print(f"  LLM model: {self.config.llm_model or '(default)'}")
            print(f"  PyMuPDF confidence threshold: {self.config.pymupdf_min_confidence}")
            print(f"  Marker fallback: {'enabled' if self.enable_marker else 'disabled'}")
            if self.enable_marker and marker_cache_dir:
                print(f"  Marker cache: {marker_cache_dir}")

    def combine_table_pages(
        self,
        tables: list,
        table_number: str
    ):
        """
        Combine multiple table pages into single markdown

        Strategy:
        1. Keep header from first page only
        2. Concatenate all data rows
        3. Remove duplicate headers from continuation pages
        4. Set confidence to minimum of all pages

        Args:
            tables: List of MarkdownTable objects, one per page
            table_number: Table number for reference

        Returns:
            Combined MarkdownTable object

        Example:
            >>> tables = [page1_table, page2_table, page3_table]
            >>> combined = parser.combine_table_pages(tables, "6.2.2.1")
        """
        from .models import MarkdownTable

        if len(tables) == 1:
            return tables[0]

        if self.verbose:
            print(f"Combining {len(tables)} pages for table {table_number}")

        combined_lines = []
        seen_header = False

        for i, table in enumerate(tables):
            lines = table.markdown_text.split('\n')

            for line in lines:
                stripped = line.strip()

                # Skip table title on continuation pages
                if i > 0 and f"Table {table_number}" in line:
                    if self.verbose and i == 1:  # Only print once
                        print(f"  Skipping continuation title: {stripped[:60]}...")
                    continue

                # Skip "Continued" markers
                if "(Continued)" in line:
                    if self.verbose:
                        print(f"  Skipping continuation marker on page {i+1}")
                    continue

                # Skip markdown table separator after first occurrence
                if stripped.startswith('|---') and seen_header:
                    continue

                if stripped.startswith('|---'):
                    seen_header = True

                combined_lines.append(line)

        # Calculate combined metadata
        total_rows = sum(t.estimated_rows for t in tables)
        min_confidence = min(t.confidence for t in tables)

        combined_markdown = '\n'.join(combined_lines)

        if self.verbose:
            print(f"  Combined {len(tables)} pages:")
            print(f"    Total rows: {total_rows}")
            print(f"    Confidence: {min_confidence:.2f} (minimum across pages)")

        return MarkdownTable(
            markdown_text=combined_markdown,
            confidence=min_confidence,
            page_number=tables[0].page_number,  # First page
            estimated_rows=total_rows,
            estimated_cols=tables[0].estimated_cols,
        )

    def parse_table(
        self,
        pdf_path: str | Path,
        table_number: str,
        vintage: str,
        page_num: int | None = None,
        page_nums: list[int] | None = None,
        target_schema: type[BaseModel] | None = None,
    ) -> ParseResult:
        """
        Extract and normalize table using hybrid approach

        Flow:
        1. Extract with PyMuPDF (fast baseline or automatic discovery)
        2. Apply LLM repair and normalization
        3. Validate against Pydantic schema

        Args:
            pdf_path: Path to PDF file
            table_number: NECB table number (e.g., "3.2.2.2")
            vintage: NECB vintage (e.g., "2020")
            page_num: Optional page number (0-indexed). If not provided, automatically discovers table location
            target_schema: Pydantic model (auto-detected if None)

        Returns:
            ParseResult with success status, validated data, and metadata

        Example (automatic discovery):
            >>> parser = HybridNECBParser(verbose=True)
            >>> result = parser.parse_table(
            ...     pdf_path="NECB-2020.pdf",
            ...     table_number="3.2.2.3",
            ...     vintage="2020"
            ... )

        Example (with page number):
            >>> parser = HybridNECBParser(verbose=True)
            >>> result = parser.parse_table(
            ...     pdf_path="NECB-2020.pdf",
            ...     table_number="3.2.2.3",
            ...     vintage="2020",
            ...     page_num=72
            ... )
        """
        timing = {}
        errors = []
        confidence = 0.0
        auto_discovered = False

        # Step -1: Check for custom extractor (bypasses standard pipeline)
        if self.custom_extractor.has_custom_extractor(table_number):
            if self.verbose:
                print(f"\n{'='*80}")
                print(f"Custom PyMuPDF Extractor for Table {table_number}")
                print(f"Bypassing LLM repair - direct extraction to structured data")
                print(f"{'='*80}\n")

            start_time = time.time()

            # Use provided page or discover it
            extraction_page = page_num if page_num is not None else 0
            if page_num is None:
                # Auto-discover the table location
                discovered_tables, discovered_page = self.pymupdf.find_and_extract_table(
                    pdf_path=pdf_path,
                    table_identifier=table_number,
                )
                if discovered_page is not None:
                    extraction_page = discovered_page
                    if self.verbose:
                        print(f"Auto-discovered table on page {extraction_page + 1}")

            success, structured_data, extraction_errors = self.custom_extractor.extract(
                table_number, vintage, str(pdf_path), extraction_page
            )
            timing["custom_extraction"] = time.time() - start_time

            if success and structured_data:
                # Custom extractor already returns validated Pydantic model dict
                schema = get_schema_for_table(table_number)
                if schema:
                    try:
                        validated_data = schema(**structured_data)

                        if self.verbose:
                            print(f"\n✅ Custom extraction successful")
                            print(f"   Validation: PASSED")
                            print(f"   Time: {timing['custom_extraction']:.2f}s\n")

                        return ParseResult(
                            success=True,
                            data=validated_data,
                            table_number=table_number,
                            vintage=vintage,
                            page_number=extraction_page,
                            method_used="custom_pymupdf",
                            llm_applied=False,
                            errors=[],
                            timing=timing,
                            confidence=1.0,
                            validation_passed=True,
                            raw_markdown=None,
                            repaired_markdown=None,
                        )
                    except Exception as e:
                        if self.verbose:
                            print(f"⚠️  Custom extraction validation failed: {e}")
                            print(f"   Falling back to standard pipeline\n")
                        errors.append(f"Custom extractor validation error: {str(e)}")
                else:
                    if self.verbose:
                        print(f"⚠️  No schema found for table {table_number}")
                        print(f"   Falling back to standard pipeline\n")
            else:
                if self.verbose:
                    print(f"⚠️  Custom extraction failed: {extraction_errors}")
                    print(f"   Falling back to standard pipeline\n")
                errors.extend(extraction_errors)

        # Normalize page parameters into a list
        if page_nums:
            pages = page_nums
        elif page_num is not None:
            pages = [page_num]
        else:
            pages = None  # Will auto-discover

        # Handle multi-page tables
        if pages and len(pages) > 1:
            if self.verbose:
                print(f"\n{'='*80}")
                print(f"Multi-Page Table Extraction")
                print(f"Table {table_number}: {len(pages)} pages ({pages[0]+1}-{pages[-1]+1})")
                print(f"{'='*80}\n")

            # Extract from all pages
            start_time = time.time()
            try:
                all_page_tables = self.pymupdf.extract_tables_from_pages(
                    pdf_path=str(pdf_path),
                    page_nums=pages
                )
                timing["pymupdf_multi_page"] = time.time() - start_time

                # Filter each page to get the target table
                filtered_tables = []
                for i, page_tables in enumerate(all_page_tables):
                    if page_tables:
                        matched = self.pymupdf.filter_table_by_number(page_tables, table_number)
                        if matched:
                            filtered_tables.append(matched)
                            if self.verbose:
                                print(f"  Page {pages[i]+1}: Found table {table_number}")
                        else:
                            # Fallback to first table if no match
                            filtered_tables.append(page_tables[0])
                            if self.verbose:
                                print(f"  Page {pages[i]+1}: Using first table (no match for {table_number})")

                if not filtered_tables:
                    errors.append(f"No tables found on any of {len(pages)} pages")
                    return self._create_error_result(
                        table_number, vintage, pages[0], errors, timing
                    )

                # Combine all pages into single table
                combined_table = self.combine_table_pages(filtered_tables, table_number)
                confidence = combined_table.confidence

                if self.verbose:
                    print(f"\n✅ Combined {len(filtered_tables)} pages:")
                    print(f"  Total rows: {combined_table.estimated_rows}")
                    print(f"  Confidence: {confidence:.2f}\n")

                # Continue with LLM repair using combined table
                page_num = pages[0]  # Use first page for result attribution
                raw_markdown = combined_table.markdown_text

            except Exception as e:
                timing["pymupdf_multi_page"] = time.time() - start_time
                errors.append(f"Multi-page extraction error: {str(e)}")
                return self._create_error_result(
                    table_number, vintage, pages[0] if pages else 0, errors, timing
                )

            # Skip to LLM repair (Step 2)
            # We already have raw_markdown from multi-page extraction
            pymupdf_failed = False
            method_used = "pymupdf_multi_page"

        # Step 0: Automatic table discovery (if page_num not provided)
        elif pages is None:
            if self.verbose:
                print(f"\n{'='*80}")
                print(f"Automatic Table Discovery")
                print(f"Searching for Table {table_number} in {Path(pdf_path).name}")
                print(f"{'='*80}\n")

            start_time = time.time()
            try:
                discovered_tables, discovered_page = self.pymupdf.find_and_extract_table(
                    pdf_path=pdf_path,
                    table_identifier=table_number,
                )
                timing["auto_discovery"] = time.time() - start_time

                if not discovered_tables or discovered_page is None:
                    errors.append(f"Automatic discovery failed: Table {table_number} not found in PDF")
                    return self._create_error_result(
                        table_number, vintage, 0, errors, timing
                    )

                page_num = discovered_page
                auto_discovered = True

                if self.verbose:
                    print(f"✅ Found Table {table_number} on page {page_num + 1} (0-indexed: {page_num})")
                    print(f"Discovery time: {timing['auto_discovery']:.2f}s\n")

            except Exception as e:
                timing["auto_discovery"] = time.time() - start_time
                errors.append(f"Automatic discovery error: {str(e)}")
                return self._create_error_result(
                    table_number, vintage, 0, errors, timing
                )

        # Single-page extraction (only if not multi-page)
        if not (pages and len(pages) > 1):
            if self.verbose:
                print(f"\n{'='*80}")
                print(f"Parsing Table {table_number} (vintage {vintage})")
                print(f"PDF: {Path(pdf_path).name}, page {page_num + 1}")
                if auto_discovered:
                    print(f"Page discovered automatically")
                print(f"{'='*80}\n")

            # Step 1: PyMuPDF extraction (BEFORE schema check to enable caching for all tables)
            if self.verbose:
                print("Step 1: PyMuPDF Extraction")
                print("-" * 80)

            start_time = time.time()
            raw_markdown = None
            method_used = "pymupdf"

            try:
                tables = self.pymupdf.extract_tables_from_page(
                    pdf_path=str(pdf_path), page_num=page_num
                )
                timing["pymupdf_extraction"] = time.time() - start_time

                if not tables or len(tables) == 0:
                    if self.verbose:
                        print("⚠️  PyMuPDF found no tables on page")
                    pymupdf_failed = True
                else:
                    # Filter tables to find the one matching the requested table number
                    if len(tables) > 1:
                        # Try automatic matching
                        matched_table = self.pymupdf.filter_table_by_number(tables, table_number)
                        if matched_table:
                            table = matched_table
                            if self.verbose:
                                print(f"Found {len(tables)} tables on page, selected table {table_number}")
                        else:
                            # Fallback to first table if no match found
                            table = tables[0]
                            if self.verbose:
                                print(f"⚠️  Could not match table {table_number} from {len(tables)} tables, using first table")
                    else:
                        # Only one table on page, use it
                        table = tables[0]

                    confidence = table.confidence
                    pymupdf_failed = confidence < self.config.pymupdf_min_confidence

                    if self.verbose:
                        print(f"Extracted {len(tables)} tables")
                        print(
                            f"Table: {table.estimated_rows} rows × {table.estimated_cols} columns"
                        )
                        print(f"Confidence: {confidence:.2f}")

                    if pymupdf_failed:
                        if self.verbose:
                            print(f"⚠️  Confidence {confidence:.2f} below threshold {self.config.pymupdf_min_confidence}\n")
                    else:
                        raw_markdown = table.markdown_text
                        if self.verbose:
                            print("✅ PyMuPDF extraction successful\n")

            except Exception as e:
                timing["pymupdf_extraction"] = time.time() - start_time
                if self.verbose:
                    print(f"⚠️  PyMuPDF extraction error: {str(e)}\n")
                pymupdf_failed = True

        # Step 1.5: Marker fallback (if PyMuPDF failed OR table is in preferred list)
        use_marker = (
            (pymupdf_failed or table_number in self.config.marker_for_tables)
            and self.enable_marker
            and self.marker
        )

        if use_marker:
            if self.verbose:
                print("Step 1.5: Marker Fallback Extraction")
                print("-" * 80)
                if table_number in self.config.marker_for_tables:
                    print(f"Table {table_number} is in MARKER_PREFERRED_TABLES - using Marker...")
                else:
                    print("PyMuPDF failed/low confidence - trying Marker...")

            start_time = time.time()
            try:
                marker_tables = self.marker.extract_tables_from_page(
                    pdf_path=pdf_path,
                    page_num=page_num,
                )
                timing["marker_extraction"] = time.time() - start_time

                if not marker_tables or len(marker_tables) == 0:
                    errors.append("Both PyMuPDF and Marker found no tables on page")
                    return self._create_error_result(
                        table_number, vintage, page_num, errors, timing,
                        raw_markdown=raw_markdown  # Cache even if both extraction methods fail
                    )

                # Get first table and convert to markdown
                marker_table = marker_tables[0]
                raw_markdown = self._marker_table_to_markdown(marker_table)
                confidence = 0.9  # Marker is more sophisticated, assign high confidence
                method_used = "marker"

                if self.verbose:
                    print(f"✅ Marker extracted {len(marker_tables)} tables")
                    print(f"Table: {len(marker_table.cells)} rows\n")

            except Exception as e:
                timing["marker_extraction"] = time.time() - start_time
                if self.verbose:
                    print(f"⚠️  Marker extraction error:")
                    import traceback
                    traceback.print_exc()
                errors.append(f"Both PyMuPDF and Marker failed: {str(e)}")
                return self._create_error_result(
                    table_number, vintage, page_num, errors, timing,
                    raw_markdown=raw_markdown  # Cache even if Marker fails with exception
                )
        elif pymupdf_failed:
            # PyMuPDF failed but Marker is disabled
            errors.append("PyMuPDF found no tables and Marker fallback is disabled")
            return self._create_error_result(
                table_number, vintage, page_num, errors, timing,
                raw_markdown=raw_markdown  # Cache even if PyMuPDF fails (might be None)
            )

        # At this point, we should have raw_markdown from either PyMuPDF or Marker
        if raw_markdown is None:
            errors.append("No table data extracted from PDF")
            return self._create_error_result(
                table_number, vintage, page_num, errors, timing, confidence=confidence
            )

        # Step 1.75: Schema check (AFTER extraction so we cache data even without schemas)
        if target_schema is None:
            target_schema = get_schema_for_table(table_number)
            if target_schema is None:
                errors.append(f"No schema found for table {table_number}")
                return self._create_error_result(
                    table_number, vintage, page_num, errors, timing,
                    confidence=confidence, raw_markdown=raw_markdown  # Cache extraction!
                )

        # Step 2: LLM repair and normalization (with caching)
        if self.verbose:
            print("Step 2: LLM Repair and Normalization")
            print("-" * 80)

        # Check cache first (if enabled)
        llm_output = None
        if self.llm_cache and self.use_llm_cache:
            cached = self.llm_cache.load(vintage, table_number)
            if cached and cached.success:
                if self.verbose:
                    print(f"✅ Cache hit for {vintage}/{table_number}")
                # Validate cached JSON against current schema
                try:
                    import json
                    import re

                    # Extract JSON from markdown code fences if present
                    json_str = cached.repaired_json
                    if json_str.strip().startswith("```"):
                        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", json_str)
                        if json_match:
                            json_str = json_match.group(1)

                    data = json.loads(json_str)
                    validated_data = target_schema(**data)
                    timing["cache_load"] = 0.01
                    return ParseResult(
                        success=True,
                        data=validated_data,
                        table_number=table_number,
                        vintage=vintage,
                        page_number=cached.page_number,
                        method_used=f"cached_{cached.method_used}",
                        llm_applied=False,  # Not this run - loaded from cache
                        errors=[],
                        timing=timing,
                        confidence=cached.confidence,
                        validation_passed=True,
                        raw_markdown=cached.raw_markdown,
                        repaired_markdown=cached.repaired_json,
                    )
                except Exception as e:
                    if self.verbose:
                        print(f"⚠️  Cache validation failed, re-running LLM: {e}")
                    # Fall through to LLM call

        start_time = time.time()
        try:
            validated_data, llm_output, llm_errors = self.llm.repair_and_normalize(
                raw_table=raw_markdown,
                table_number=table_number,
                vintage=vintage,
                target_schema=target_schema,
            )
            timing["llm_repair"] = time.time() - start_time

            if llm_errors:
                errors.extend(llm_errors)

            if validated_data is None:
                if self.verbose:
                    print("❌ LLM repair failed\n")
                return self._create_error_result(
                    table_number,
                    vintage,
                    page_num,
                    errors,
                    timing,
                    confidence=confidence,
                    raw_markdown=raw_markdown,  # Cache extraction data even for LLM failures
                )

            if self.verbose:
                print("✅ LLM repair successful\n")

            # Save to cache (if enabled and successful)
            if self.llm_cache and llm_output:
                cache_entry = create_cache_entry(
                    vintage=vintage,
                    table_number=table_number,
                    raw_markdown=raw_markdown or "",
                    repaired_json=llm_output,
                    schema_name=target_schema.__name__,
                    confidence=confidence,
                    method_used=method_used,
                    llm_model=self.llm.backend.get_model_name(),
                    llm_backend=self.config.llm_backend,
                    page_number=page_num,
                    extraction_time_s=timing.get("pymupdf_extraction", 0.0),
                    llm_time_s=timing.get("llm_repair", 0.0),
                    success=True,
                )
                self.llm_cache.save(cache_entry)

        except Exception as e:
            timing["llm_repair"] = time.time() - start_time
            errors.append(f"LLM repair failed: {str(e)}")
            return self._create_error_result(
                table_number, vintage, page_num, errors, timing, confidence=confidence,
                raw_markdown=raw_markdown,  # Cache extraction data even for LLM exceptions
            )

        # Success!
        total_time = sum(timing.values())
        if self.verbose:
            print(f"{'='*80}")
            print(f"✅ Success! Table {table_number} parsed correctly")
            print(f"Total time: {total_time:.2f}s")
            print(f"  - PyMuPDF: {timing.get('pymupdf_extraction', 0):.2f}s")
            print(f"  - LLM repair: {timing.get('llm_repair', 0):.2f}s")
            print(f"{'='*80}\n")

        return ParseResult(
            success=True,
            data=validated_data,
            table_number=table_number,
            vintage=vintage,
            page_number=page_num,
            method_used=method_used,  # "pymupdf" or "marker"
            llm_applied=True,
            errors=[],
            timing=timing,
            confidence=confidence,
            validation_passed=True,
            raw_markdown=raw_markdown,  # Cache for schema iteration
            repaired_markdown=llm_output,  # LLM output for caching
        )

    def _marker_table_to_markdown(self, marker_table) -> str:
        """
        Convert Marker's MarkerTable to markdown format

        Args:
            marker_table: MarkerTable object with cells attribute

        Returns:
            Markdown-formatted table string
        """
        if not marker_table.cells or len(marker_table.cells) == 0:
            return ""

        markdown_lines = []

        # Add header row
        if len(marker_table.cells) > 0:
            header = marker_table.cells[0]
            markdown_lines.append("| " + " | ".join(header) + " |")
            # Add separator
            markdown_lines.append("| " + " | ".join(["---"] * len(header)) + " |")

        # Add data rows
        for row in marker_table.cells[1:]:
            # Pad row to match header length if needed
            padded_row = row + [""] * (len(marker_table.cells[0]) - len(row))
            markdown_lines.append("| " + " | ".join(padded_row) + " |")

        return "\n".join(markdown_lines)

    def _create_error_result(
        self,
        table_number: str,
        vintage: str,
        page_num: int,
        errors: list[str],
        timing: dict[str, float],
        confidence: float = 0.0,
        raw_markdown: str | None = None,
    ) -> ParseResult:
        """Create error result for failed parsing"""
        return ParseResult(
            success=False,
            data=None,
            table_number=table_number,
            vintage=vintage,
            page_number=page_num,
            method_used="failed",
            llm_applied=False,
            errors=errors,
            timing=timing,
            confidence=confidence,
            validation_passed=False,
            raw_markdown=raw_markdown,  # Cache even for failures
            repaired_markdown=None,
        )

    def parse_document(
        self,
        pdf_path: str | Path,
        vintage: str,
        table_specs: list[dict[str, Any]],
    ) -> DocumentParseResult:
        """
        Parse multiple tables in NECB document

        Args:
            pdf_path: Path to PDF file
            vintage: NECB vintage (e.g., "2020")
            table_specs: List of table specifications:
                [{"table_number": "3.2.2.2", "page_num": 72}, ...]
                or (with automatic discovery):
                [{"table_number": "3.2.2.2"}, ...]

        Returns:
            DocumentParseResult with all table results and statistics

        Example (with page numbers):
            >>> parser = HybridNECBParser()
            >>> result = parser.parse_document(
            ...     pdf_path="NECB-2020.pdf",
            ...     vintage="2020",
            ...     table_specs=[
            ...         {"table_number": "3.2.2.2", "page_num": 72},
            ...         {"table_number": "3.2.2.3", "page_num": 71}
            ...     ]
            ... )

        Example (automatic discovery):
            >>> parser = HybridNECBParser()
            >>> result = parser.parse_document(
            ...     pdf_path="NECB-2020.pdf",
            ...     vintage="2020",
            ...     table_specs=[
            ...         {"table_number": "3.2.2.2"},
            ...         {"table_number": "3.2.2.3"}
            ...     ]
            ... )
        """
        if self.verbose:
            print(f"\n{'='*80}")
            print(f"Parsing NECB {vintage} document")
            print(f"PDF: {Path(pdf_path).name}")
            print(f"Tables to parse: {len(table_specs)}")
            print(f"{'='*80}\n")

        start_time = time.time()
        results = []

        for spec in table_specs:
            table_number = spec["table_number"]
            page_num = spec.get("page_num")  # Optional: single page (legacy)
            page_nums = spec.get("all_pages")  # Optional: multiple pages (Phase 3)

            result = self.parse_table(
                pdf_path=pdf_path,
                table_number=table_number,
                vintage=vintage,
                page_num=page_num,
                page_nums=page_nums,  # Pass multi-page support
            )
            results.append(result)

        total_duration = time.time() - start_time

        # Calculate statistics
        successful = sum(1 for r in results if r.success)
        success_rate = (successful / len(results)) * 100 if results else 0

        method_distribution = {}
        for result in results:
            method = result.method_used
            method_distribution[method] = method_distribution.get(method, 0) + 1

        if self.verbose:
            print(f"\n{'='*80}")
            print(f"Document parsing complete")
            print(f"Success rate: {success_rate:.1f}% ({successful}/{len(results)})")
            print(f"Total duration: {total_duration:.2f}s")
            print(f"Method distribution: {method_distribution}")
            print(f"{'='*80}\n")

        return DocumentParseResult(
            tables=results,
            success_rate=success_rate,
            total_duration=total_duration,
            method_distribution=method_distribution,
        )
