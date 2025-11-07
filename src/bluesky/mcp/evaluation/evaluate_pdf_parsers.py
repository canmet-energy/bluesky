"""
PDF Parser Evaluation

Compares multiple PDF parsing libraries on NECB tables to find the best method.

Tests:
- pdfplumber (current)
- camelot-py (specialized for tables)
- tabula-py (Java-based)
- PyMuPDF/fitz (low-level)

Usage:
    python -m bluesky.mcp.evaluation.evaluate_pdf_parsers
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

import pdfplumber
import fitz  # PyMuPDF
from rich.console import Console
from rich.table import Table as RichTable
from rich.panel import Panel

console = Console()

# Try to import optional libraries
try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False
    console.print("[yellow]Warning: camelot-py not available[/yellow]")

try:
    import tabula
    TABULA_AVAILABLE = True
except ImportError:
    TABULA_AVAILABLE = False
    console.print("[yellow]Warning: tabula-py not available[/yellow]")


@dataclass
class ExtractionResult:
    """Result from a PDF extraction method"""
    method: str
    tables: List[List[List[str]]]
    execution_time: float
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TableQualityScore:
    """Quality score for an extracted table"""
    method: str
    table_index: int
    total_score: float
    row_count: int
    col_count: int
    fill_ratio: float
    has_walls: bool
    has_roofs: bool
    has_floors: bool
    notes: List[str]


class PDFParserEvaluator:
    """Evaluates different PDF parsing methods"""

    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path

    def extract_with_pdfplumber(self, pages: List[int]) -> ExtractionResult:
        """Extract tables using pdfplumber (current method)"""
        import time
        start = time.time()

        try:
            all_tables = []
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num in pages:
                    page = pdf.pages[page_num - 1]  # 0-indexed
                    tables = page.extract_tables()
                    if tables:
                        all_tables.extend(tables)

            return ExtractionResult(
                method="pdfplumber",
                tables=all_tables,
                execution_time=time.time() - start,
                metadata={"pages": pages}
            )
        except Exception as e:
            return ExtractionResult(
                method="pdfplumber",
                tables=[],
                execution_time=time.time() - start,
                error=str(e)
            )

    def extract_with_pdfplumber_custom(self, pages: List[int]) -> ExtractionResult:
        """Extract with custom pdfplumber settings"""
        import time
        start = time.time()

        try:
            all_tables = []
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num in pages:
                    page = pdf.pages[page_num - 1]

                    # Custom table settings
                    table_settings = {
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "lines",
                        "intersection_tolerance": 5,
                        "join_tolerance": 5,
                    }

                    tables = page.extract_tables(table_settings=table_settings)
                    if tables:
                        all_tables.extend(tables)

            return ExtractionResult(
                method="pdfplumber_custom",
                tables=all_tables,
                execution_time=time.time() - start,
                metadata={"pages": pages, "settings": "lines-based"}
            )
        except Exception as e:
            return ExtractionResult(
                method="pdfplumber_custom",
                tables=[],
                execution_time=time.time() - start,
                error=str(e)
            )

    def extract_with_camelot(self, pages: List[int]) -> ExtractionResult:
        """Extract using camelot-py"""
        if not CAMELOT_AVAILABLE:
            return ExtractionResult(
                method="camelot",
                tables=[],
                execution_time=0,
                error="camelot-py not installed"
            )

        import time
        start = time.time()

        try:
            pages_str = ",".join(map(str, pages))
            tables_camelot = camelot.read_pdf(
                str(self.pdf_path),
                pages=pages_str,
                flavor='lattice'  # For tables with lines
            )

            all_tables = [t.df.values.tolist() for t in tables_camelot]

            return ExtractionResult(
                method="camelot_lattice",
                tables=all_tables,
                execution_time=time.time() - start,
                metadata={
                    "pages": pages,
                    "flavor": "lattice",
                    "table_count": len(tables_camelot)
                }
            )
        except Exception as e:
            return ExtractionResult(
                method="camelot_lattice",
                tables=[],
                execution_time=time.time() - start,
                error=str(e)
            )

    def extract_with_camelot_stream(self, pages: List[int]) -> ExtractionResult:
        """Extract using camelot-py with stream flavor (no lines)"""
        if not CAMELOT_AVAILABLE:
            return ExtractionResult(
                method="camelot_stream",
                tables=[],
                execution_time=0,
                error="camelot-py not installed"
            )

        import time
        start = time.time()

        try:
            pages_str = ",".join(map(str, pages))
            tables_camelot = camelot.read_pdf(
                str(self.pdf_path),
                pages=pages_str,
                flavor='stream'  # For tables without lines
            )

            all_tables = [t.df.values.tolist() for t in tables_camelot]

            return ExtractionResult(
                method="camelot_stream",
                tables=all_tables,
                execution_time=time.time() - start,
                metadata={
                    "pages": pages,
                    "flavor": "stream",
                    "table_count": len(tables_camelot)
                }
            )
        except Exception as e:
            return ExtractionResult(
                method="camelot_stream",
                tables=[],
                execution_time=time.time() - start,
                error=str(e)
            )

    def extract_with_tabula(self, pages: List[int]) -> ExtractionResult:
        """Extract using tabula-py"""
        if not TABULA_AVAILABLE:
            return ExtractionResult(
                method="tabula",
                tables=[],
                execution_time=0,
                error="tabula-py not installed"
            )

        import time
        start = time.time()

        try:
            all_tables = []
            for page_num in pages:
                dfs = tabula.read_pdf(
                    str(self.pdf_path),
                    pages=page_num,
                    multiple_tables=True,
                    lattice=True  # Use lattice mode for tables with lines
                )
                for df in dfs:
                    all_tables.append(df.values.tolist())

            return ExtractionResult(
                method="tabula_lattice",
                tables=all_tables,
                execution_time=time.time() - start,
                metadata={"pages": pages, "mode": "lattice"}
            )
        except Exception as e:
            return ExtractionResult(
                method="tabula_lattice",
                tables=[],
                execution_time=time.time() - start,
                error=str(e)
            )

    def extract_with_pymupdf(self, pages: List[int]) -> ExtractionResult:
        """Extract using PyMuPDF (fitz)"""
        import time
        start = time.time()

        try:
            all_tables = []
            doc = fitz.open(self.pdf_path)

            for page_num in pages:
                page = doc[page_num - 1]  # 0-indexed

                # Find tables (simple heuristic)
                tabs = page.find_tables()

                for tab in tabs:
                    # Extract table data
                    table_data = []
                    for row in tab.extract():
                        table_data.append([str(cell) if cell else "" for cell in row])

                    if table_data:
                        all_tables.append(table_data)

            doc.close()

            return ExtractionResult(
                method="pymupdf",
                tables=all_tables,
                execution_time=time.time() - start,
                metadata={"pages": pages}
            )
        except Exception as e:
            return ExtractionResult(
                method="pymupdf",
                tables=[],
                execution_time=time.time() - start,
                error=str(e)
            )

    def score_table_quality(self, table: List[List[str]], method: str, table_idx: int) -> TableQualityScore:
        """Score the quality of an extracted table"""
        score = 0
        notes = []

        if not table or len(table) < 2:
            return TableQualityScore(
                method=method,
                table_index=table_idx,
                total_score=0,
                row_count=0,
                col_count=0,
                fill_ratio=0,
                has_walls=False,
                has_roofs=False,
                has_floors=False,
                notes=["Empty or too few rows"]
            )

        row_count = len(table)
        col_count = max(len(row) for row in table) if table else 0

        # 1. Row count score (more rows = better, up to reasonable limit)
        row_score = min(row_count, 20)
        score += row_score
        notes.append(f"Rows: {row_count} (+{row_score})")

        # 2. Column count score
        col_score = min(col_count, 10) * 2
        score += col_score
        notes.append(f"Cols: {col_count} (+{col_score})")

        # 3. Fill ratio (less empty cells = better)
        total_cells = sum(len(row) for row in table)
        empty_cells = sum(1 for row in table for cell in row if not cell or str(cell).strip() == "")
        fill_ratio = 1 - (empty_cells / total_cells) if total_cells > 0 else 0
        fill_score = fill_ratio * 50
        score += fill_score
        notes.append(f"Fill: {fill_ratio:.1%} (+{fill_score:.1f})")

        # 4. Content checks (for NECB 3.2.2.2 specifically)
        table_str = str(table).lower()

        has_walls = "wall" in table_str
        has_roofs = "roof" in table_str
        has_floors = "floor" in table_str

        if has_walls:
            score += 20
            notes.append("Has 'Walls' (+20)")
        if has_roofs:
            score += 20
            notes.append("Has 'Roofs' (+20)")
        if has_floors:
            score += 20
            notes.append("Has 'Floors' (+20)")

        # 5. Check for climate zones
        if any(zone in table_str for zone in ['zone 4', 'zone 5', 'zone 6']):
            score += 10
            notes.append("Has climate zones (+10)")

        return TableQualityScore(
            method=method,
            table_index=table_idx,
            total_score=score,
            row_count=row_count,
            col_count=col_count,
            fill_ratio=fill_ratio,
            has_walls=has_walls,
            has_roofs=has_roofs,
            has_floors=has_floors,
            notes=notes
        )

    def evaluate_all_methods(self, pages: List[int]) -> List[ExtractionResult]:
        """Run all extraction methods"""
        console.print(f"\n[bold cyan]Evaluating PDF parsers on pages {pages}[/bold cyan]\n")

        methods = [
            ("pdfplumber (default)", self.extract_with_pdfplumber),
            ("pdfplumber (custom)", self.extract_with_pdfplumber_custom),
            ("camelot (lattice)", self.extract_with_camelot),
            ("camelot (stream)", self.extract_with_camelot_stream),
            ("tabula (lattice)", self.extract_with_tabula),
            ("PyMuPDF", self.extract_with_pymupdf),
        ]

        results = []
        for name, method in methods:
            console.print(f"Testing {name}...", end=" ")
            result = method(pages)

            if result.error:
                console.print(f"[red]❌ ERROR: {result.error}[/red]")
            else:
                console.print(f"[green]✓[/green] Found {len(result.tables)} tables in {result.execution_time:.2f}s")

            results.append(result)

        return results


def evaluate_necb_2017_table_322():
    """Evaluate parsers on NECB 2017 Table 3.2.2.2 (the problematic one)"""
    pdf_path = Path(__file__).parent.parent / "scrapers" / "necb" / "pdfs" / "NECB-2017.pdf"

    if not pdf_path.exists():
        console.print(f"[red]Error: PDF not found at {pdf_path}[/red]")
        return

    console.print(Panel.fit(
        "[bold]NECB 2017 Table 3.2.2.2 Evaluation[/bold]\n\n"
        "Known Issue: Missing Walls, Roofs, Floors data\n"
        "Pages: 74-75 (approx)\n"
        "Expected: 5+ rows with Wall/Roof/Floor thermal transmittance",
        border_style="cyan"
    ))

    evaluator = PDFParserEvaluator(pdf_path)

    # Test on pages 74-76 (to capture potential continuation)
    results = evaluator.evaluate_all_methods(pages=[74, 75, 76])

    # Score all extracted tables
    console.print("\n[bold]Quality Scores:[/bold]\n")

    all_scores = []
    for result in results:
        if result.error:
            continue

        for idx, table in enumerate(result.tables):
            score = evaluator.score_table_quality(table, result.method, idx)
            all_scores.append(score)

    # Sort by score
    all_scores.sort(key=lambda s: s.total_score, reverse=True)

    # Display top 10 results
    table = RichTable(title="Top 10 Extraction Results by Quality")
    table.add_column("Rank", style="cyan", width=6)
    table.add_column("Method", style="magenta")
    table.add_column("Table #", width=8)
    table.add_column("Score", justify="right", style="green")
    table.add_column("Rows", justify="right")
    table.add_column("Cols", justify="right")
    table.add_column("Fill", justify="right")
    table.add_column("W/R/F", width=8)  # Walls/Roofs/Floors
    table.add_column("Notes")

    for rank, score in enumerate(all_scores[:10], 1):
        wrf = f"{'✓' if score.has_walls else '✗'}/{' ✓' if score.has_roofs else '✗'}/{'✓' if score.has_floors else '✗'}"
        notes_str = ", ".join(score.notes[:2])  # First 2 notes

        style = "green" if score.total_score > 100 else "yellow" if score.total_score > 50 else "red"

        table.add_row(
            f"#{rank}",
            score.method,
            str(score.table_index),
            f"{score.total_score:.1f}",
            str(score.row_count),
            str(score.col_count),
            f"{score.fill_ratio:.0%}",
            wrf,
            notes_str,
            style=style
        )

    console.print(table)

    # Show best result details
    if all_scores:
        best = all_scores[0]
        console.print(f"\n[bold green]🏆 Best Method: {best.method} (Table #{best.table_index})[/bold green]")
        console.print(f"Score: {best.total_score:.1f}")
        console.print(f"Details:")
        for note in best.notes:
            console.print(f"  • {note}")

        # Find the actual table data
        best_result = next(r for r in results if r.method == best.method)
        best_table = best_result.tables[best.table_index]

        console.print(f"\n[bold]Extracted Table Preview:[/bold]")
        for i, row in enumerate(best_table[:10]):  # First 10 rows
            row_str = " | ".join([str(cell)[:30] for cell in row[:5]])  # First 5 cols
            console.print(f"  Row {i}: {row_str}")

        if len(best_table) > 10:
            console.print(f"  ... and {len(best_table) - 10} more rows")

    # Summary
    console.print("\n[bold]Summary:[/bold]")
    successful_methods = [r for r in results if not r.error and r.tables]
    console.print(f"  Successful methods: {len(successful_methods)}/{len(results)}")

    if successful_methods:
        best_method = max(all_scores, key=lambda s: s.total_score).method if all_scores else "None"
        console.print(f"  Best performing: {best_method}")

        complete_extractions = [s for s in all_scores if s.has_walls and s.has_roofs and s.has_floors]
        if complete_extractions:
            console.print(f"  [green]✓ {len(complete_extractions)} extractions found ALL required data (Walls/Roofs/Floors)[/green]")
        else:
            console.print(f"  [red]❌ NO extractions found all required data[/red]")
    else:
        console.print("  [red]❌ All methods failed[/red]")


def main():
    """Run PDF parser evaluation"""
    evaluate_necb_2017_table_322()


if __name__ == "__main__":
    main()
