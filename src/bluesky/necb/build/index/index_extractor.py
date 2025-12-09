"""
NECB Index Text Extractor

Extracts raw text from NECB PDF index pages using PyMuPDF.

The NECB index has this structure:
- Main terms start with uppercase and typically don't have article refs on same line
- Sub-terms start with lowercase and have article refs (e.g., "air leakage, 3.2.4.3.")
- Cross-references use "(see ...)" or "(see also ...)"
- Some entries span multiple lines
"""

import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple

import fitz  # PyMuPDF

from .config import (
    get_pdf_path,
    get_index_page_range,
    ARTICLE_REF_PATTERN,
    SEE_ALSO_PATTERN,
    extract_article_references,
    extract_see_also,
)
from .index_models import IndexEntry

logger = logging.getLogger(__name__)

# Words that typically start continuation lines (not new sub-terms)
CONTINUATION_WORDS = frozenset({
    'and', 'the', 'with', 'for', 'of', 'or', 'in', 'to', 'a', 'an',
    'by', 'on', 'at', 'from', 'into', 'through', 'during', 'including',
})


class IndexExtractor:
    """Extract index entries from NECB PDF pages."""

    def __init__(self, pdf_path: Path):
        """
        Initialize extractor with PDF path.

        Args:
            pdf_path: Path to NECB PDF file
        """
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        logger.info(f"Opened PDF: {pdf_path.name} ({self.doc.page_count} pages)")

    def close(self):
        """Close the PDF document."""
        if self.doc:
            self.doc.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def extract_pages(
        self,
        start_page: int,
        end_page: int,
    ) -> List[Tuple[int, str]]:
        """
        Extract text from a range of pages.

        Args:
            start_page: First page (0-indexed)
            end_page: Last page (0-indexed, inclusive)

        Returns:
            List of (page_number, text) tuples (1-indexed page numbers)
        """
        pages = []
        for page_num in range(start_page, end_page + 1):
            if page_num >= self.doc.page_count:
                logger.warning(f"Page {page_num} out of range")
                break

            page = self.doc[page_num]
            text = page.get_text("text")

            # Clean up the text
            text = self._clean_page_text(text, page_num + 1)

            pages.append((page_num + 1, text))  # 1-indexed page number

        logger.info(f"Extracted {len(pages)} pages ({start_page+1} to {end_page+1})")
        return pages

    def _clean_page_text(self, text: str, page_num: int) -> str:
        """
        Clean raw page text.

        Removes:
        - Page numbers and headers
        - Division marker footnotes
        - Empty lines
        """
        lines = text.split('\n')
        cleaned = []

        for line in lines:
            line = line.rstrip()

            # Skip empty lines
            if not line.strip():
                continue

            # Skip page number lines (just a number)
            if re.match(r'^\s*\d+\s*$', line):
                continue

            # Skip header lines (e.g., "Division B")
            if re.match(r'^Division [A-C]$', line.strip()):
                continue

            # Skip "Index" header
            if line.strip() == "Index":
                continue

            # Skip footer notes about division markers
            if "[A]" in line and "Division A" in line:
                continue
            if "[C]" in line and "Division C" in line:
                continue

            # Skip copyright/NRC lines
            if "National Research Council" in line:
                continue
            if "NECB" in line and ("2020" in line or "2017" in line or "2015" in line or "2011" in line):
                # Likely a header/footer
                if len(line.strip()) < 20:
                    continue

            cleaned.append(line)

        return '\n'.join(cleaned)

    def _has_unclosed_parenthesis(self, line: str) -> bool:
        """
        Check if line has unclosed parentheses - indicates continuation needed.

        Examples:
            "Air-conditioning systems (see Heating, ventilating" -> True (unclosed)
            "and air-conditioning (HVAC) systems)" -> False (has closing)
            "Fenestration (see Windows)" -> False (balanced)
        """
        return line.count('(') > line.count(')')

    def _ends_with_trailing_comma(self, line: str) -> bool:
        """
        Check if line ends with a trailing comma - indicates article ref on next line.

        Examples:
            "factors for occupancy control and personal control, " -> True
            "air leakage, 3.2.4.3." -> False (has article ref)
        """
        stripped = line.rstrip()
        return stripped.endswith(',') and not ARTICLE_REF_PATTERN.search(line)

    def _needs_continuation(self, line: str) -> bool:
        """
        Check if line needs continuation - incomplete entry that continues on next line.

        Detects:
        - Unclosed parentheses: "(see Heating, ventilating and"
        - Trailing comma without article ref: "factors for control, "
        - Line ends with word (no period/ref): "overall thermal " (word split)
        - Line ends with abbreviation in parens: "(HVAC)" followed by noun on next line

        Examples:
            "(see Heating, ventilating and air-conditioning " -> True
            "overall thermal " -> True (word continues on next line)
            "Heating, ventilating and air-conditioning (HVAC)" -> True (main term split)
            "air leakage, 3.2.4.3." -> False (complete with ref)
            "3.2.4.3." -> False (just a reference)
        """
        stripped = line.rstrip()

        # Unclosed parentheses
        if self._has_unclosed_parenthesis(stripped):
            return True

        # Trailing comma without article ref
        if self._ends_with_trailing_comma(stripped):
            return True

        # Line ends with abbreviation in parens like (HVAC) - main term may continue
        # This catches split main terms like "Heating, ventilating and air-conditioning (HVAC)\nequipment"
        if stripped.endswith(')') and not ARTICLE_REF_PATTERN.search(line):
            # Check if it ends with an abbreviation pattern like (HVAC), (SWH), etc.
            if re.search(r'\([A-Z]{2,}\)$', stripped):
                return True

        # Line ends with a word (not punctuation or article ref)
        # This catches word-wrap continuations like "overall thermal "
        if stripped and not stripped[-1] in '.)]' and not ARTICLE_REF_PATTERN.search(line):
            # Make sure it's not just a main term header
            # Main terms typically are short and capitalized
            if len(stripped) > 3:
                return True

        return False

    def _starts_with_continuation_word(self, line: str) -> bool:
        """
        Check if line starts with a common continuation word.

        These words typically indicate the line continues from the previous one,
        rather than starting a new sub-term entry.

        Examples:
            "and air-conditioning (HVAC) systems)" -> True
            "air leakage, 3.2.4.3." -> False (genuine sub-term)
        """
        if not line:
            return False
        words = line.split()
        if not words:
            return False
        first_word = words[0].lower().rstrip('.,;:')
        return first_word in CONTINUATION_WORDS

    def _is_article_ref_only(self, line: str) -> bool:
        """
        Check if line contains only article references (no descriptive text).

        Examples:
            "4.3.2.10." -> True
            "3.2.4.3., 8.4.3.9." -> True
            "air leakage, 3.2.4.3." -> False (has description)
        """
        # Remove article references and see what's left
        text_without_refs = ARTICLE_REF_PATTERN.sub('', line)
        text_without_refs = re.sub(r'[,.\s]+', '', text_without_refs)
        return len(text_without_refs) == 0 and ARTICLE_REF_PATTERN.search(line) is not None

    def _is_closing_parenthesis_fragment(self, line: str) -> bool:
        """
        Check if line is a closing parenthesis fragment from a multi-line (see also).

        Examples:
            "systems)" -> True (closes an open (see also ...)
            "and air-conditioning)" -> True
            "systems, 3.2.4.3." -> False (has article ref, is complete)
            "new term" -> False (doesn't close parens)
        """
        stripped = line.strip()
        # Must end with closing paren
        if not stripped.endswith(')'):
            return False
        # Must have more closing than opening (orphaned closer)
        if stripped.count(')') <= stripped.count('('):
            return False
        # Should not have article refs (would be complete)
        if ARTICLE_REF_PATTERN.search(stripped):
            return False
        return True

    def parse_entries(
        self,
        pages: List[Tuple[int, str]],
        vintage: str,
    ) -> List[IndexEntry]:
        """
        Parse index entries from extracted page text.

        The index has a specific structure:
        - Main term lines: Start with uppercase, typically no article refs
        - Sub-term lines: Start with lowercase, have article refs
        - Continuation lines: Article refs only, or "(see ...)" references

        Args:
            pages: List of (page_number, text) tuples
            vintage: NECB vintage

        Returns:
            List of IndexEntry objects
        """
        entries = []
        current_main_term = None
        pending_lines = []  # Buffer for multi-line entries
        pending_is_sub_term = False  # Track if pending buffer is a sub-term
        prev_line = None  # Track previous line for continuation detection

        for page_num, text in pages:
            lines = text.split('\n')

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue

                # Check what type of line this is, passing previous line for context
                # Use the last pending line if available, otherwise the actual previous line
                context_line = pending_lines[-1] if pending_lines else prev_line
                line_type = self._classify_line(stripped, context_line)

                if line_type == "main_term":
                    # Flush any pending lines first
                    if pending_lines:
                        entry = self._process_pending_lines(
                            pending_lines, current_main_term, page_num, vintage,
                            is_sub_term=pending_is_sub_term
                        )
                        if entry:
                            entries.append(entry)
                        pending_lines = []
                        pending_is_sub_term = False

                    # Start new main term
                    pending_lines = [stripped]
                    pending_is_sub_term = False
                    # Extract the main term name (without refs)
                    term_name = self._extract_term_name(stripped)
                    if term_name:
                        current_main_term = term_name

                elif line_type == "sub_term":
                    # Flush any pending lines first
                    if pending_lines:
                        entry = self._process_pending_lines(
                            pending_lines, current_main_term, page_num, vintage,
                            is_sub_term=pending_is_sub_term
                        )
                        if entry:
                            entries.append(entry)
                        pending_lines = []
                        pending_is_sub_term = False

                    # Check if this sub-term needs continuation
                    if self._needs_continuation(stripped):
                        # Buffer it for continuation
                        pending_lines = [stripped]
                        pending_is_sub_term = True
                    else:
                        # Process sub-term immediately
                        entry = self._parse_sub_term(
                            stripped, current_main_term, page_num, vintage
                        )
                        if entry:
                            entries.append(entry)

                elif line_type == "continuation":
                    # Add to pending lines
                    pending_lines.append(stripped)

                elif line_type == "see_also":
                    # Cross-reference, might be standalone or continuation
                    if pending_lines:
                        pending_lines.append(stripped)
                    else:
                        # Standalone cross-reference for current main term
                        entry = self._parse_see_also(
                            stripped, current_main_term, page_num, vintage
                        )
                        if entry:
                            entries.append(entry)

                # Track previous line for next iteration
                prev_line = stripped

        # Flush any remaining pending lines
        if pending_lines:
            entry = self._process_pending_lines(
                pending_lines, current_main_term, page_num, vintage,
                is_sub_term=pending_is_sub_term
            )
            if entry:
                entries.append(entry)

        logger.info(f"Parsed {len(entries)} index entries from {len(pages)} pages")
        return entries

    def _classify_line(self, line: str, prev_line: Optional[str] = None) -> str:
        """
        Classify a line into: main_term, sub_term, continuation, see_also, or unknown.

        Args:
            line: Current line to classify
            prev_line: Previous line (for detecting multi-line continuations)
        """
        # Check for "(see ...)" pattern at start of line
        if line.startswith('(see'):
            return "see_also"

        # Check if previous line needs continuation (unclosed parens, trailing comma, word-wrap)
        if prev_line and self._needs_continuation(prev_line):
            return "continuation"

        # Check if this is a closing parenthesis fragment (e.g., "systems)")
        # This catches orphaned closers from deeply nested multi-line (see also) patterns
        if self._is_closing_parenthesis_fragment(line):
            return "continuation"

        # Check if line is just article references
        refs = ARTICLE_REF_PATTERN.findall(line)
        text_without_refs = ARTICLE_REF_PATTERN.sub('', line).strip()
        text_without_refs = re.sub(r'[,.\s]+$', '', text_without_refs)

        if not text_without_refs and refs:
            # Line is only article references
            return "continuation"

        # Check if starts with uppercase (main term)
        if line[0].isupper():
            # Main terms typically don't have article refs on same line,
            # or have the term followed by refs
            has_refs = bool(refs)
            # Check if it looks like a main term with refs
            # e.g., "Access hatches, 3.2.2.4."
            if has_refs and ',' in line:
                # Could be main term with refs or sub-term
                # Main terms have the term before the comma
                before_comma = line.split(',')[0].strip()
                if before_comma[0].isupper() and len(before_comma) > 3:
                    return "main_term"
            return "main_term"

        # Starts with lowercase
        if line[0].islower():
            # Check if this looks like a continuation (starts with "and", "the", etc.)
            # Only treat as continuation if previous line exists and has pending content
            if prev_line and self._starts_with_continuation_word(line):
                return "continuation"
            # Otherwise it's a genuine sub-term
            return "sub_term"

        return "unknown"

    def _extract_term_name(self, line: str) -> Optional[str]:
        """Extract the term name from a main term line."""
        # Remove "(see ...)" pattern
        term = SEE_ALSO_PATTERN.sub('', line)

        # Remove article references
        term = ARTICLE_REF_PATTERN.sub('', term)

        # Remove trailing punctuation
        term = re.sub(r'[,.\s]+$', '', term)

        term = term.strip()
        return term if term and len(term) >= 2 else None

    def _process_pending_lines(
        self,
        lines: List[str],
        current_main_term: Optional[str],
        page_num: int,
        vintage: str,
        is_sub_term: bool = False,
    ) -> Optional[IndexEntry]:
        """Process accumulated lines into an entry.

        Args:
            lines: Buffered lines to process
            current_main_term: The current main term context
            page_num: Page number
            vintage: NECB vintage
            is_sub_term: If True, this is a buffered sub-term (has parent)
        """
        if not lines:
            return None

        # Join lines
        full_text = ' '.join(lines)

        # Check for cross-reference
        see_also = extract_see_also(full_text)

        # Extract article references from all lines
        refs = extract_article_references(full_text)
        article_refs = [r["article_number"] for r in refs]
        division_hints = list(set(r["division"] for r in refs if r["division"]))

        if is_sub_term:
            # This is a buffered sub-term - extract description
            desc = ARTICLE_REF_PATTERN.sub('', full_text)
            desc = SEE_ALSO_PATTERN.sub('', desc)
            desc = re.sub(r'[,.\s]+$', '', desc).strip()

            return IndexEntry(
                term=current_main_term or "Unknown",
                parent_term=current_main_term,
                description=desc if desc else None,
                article_references=article_refs,
                division_hints=division_hints,
                see_also=see_also,
                page=page_num,
                vintage=vintage,
            )
        else:
            # This is a main term
            term = self._extract_term_name(lines[0])
            if not term:
                return None

            return IndexEntry(
                term=term,
                parent_term=None,  # Main terms have no parent
                description=None,
                article_references=article_refs,
                division_hints=division_hints,
                see_also=see_also,
                page=page_num,
                vintage=vintage,
        )

    def _parse_sub_term(
        self,
        line: str,
        current_main_term: Optional[str],
        page_num: int,
        vintage: str,
    ) -> Optional[IndexEntry]:
        """Parse a sub-term line (starts with lowercase)."""
        # Extract article references
        refs = extract_article_references(line)
        article_refs = [r["article_number"] for r in refs]
        division_hints = list(set(r["division"] for r in refs if r["division"]))

        # Extract description (text before article refs)
        desc = ARTICLE_REF_PATTERN.sub('', line)
        desc = SEE_ALSO_PATTERN.sub('', desc)
        desc = re.sub(r'[,.\s]+$', '', desc).strip()

        # Check for cross-reference
        see_also = extract_see_also(line)

        if not desc and not article_refs and not see_also:
            return None

        return IndexEntry(
            term=current_main_term or "Unknown",
            parent_term=current_main_term,
            description=desc if desc else None,
            article_references=article_refs,
            division_hints=division_hints,
            see_also=see_also,
            page=page_num,
            vintage=vintage,
        )

    def _parse_see_also(
        self,
        line: str,
        current_main_term: Optional[str],
        page_num: int,
        vintage: str,
    ) -> Optional[IndexEntry]:
        """Parse a standalone (see also ...) line."""
        see_also = extract_see_also(line)
        if not see_also:
            return None

        return IndexEntry(
            term=current_main_term or "Unknown",
            parent_term=current_main_term,
            description=None,
            article_references=[],
            division_hints=[],
            see_also=see_also,
            page=page_num,
            vintage=vintage,
        )


def extract_index(
    vintage: str,
    pdf_path: Optional[Path] = None,
) -> List[IndexEntry]:
    """
    Extract index entries from a NECB PDF.

    Args:
        vintage: NECB vintage (e.g., "2020")
        pdf_path: Optional custom PDF path

    Returns:
        List of IndexEntry objects
    """
    if pdf_path is None:
        pdf_path = get_pdf_path(vintage)

    start_page, end_page = get_index_page_range(vintage)

    with IndexExtractor(pdf_path) as extractor:
        pages = extractor.extract_pages(start_page, end_page)
        entries = extractor.parse_entries(pages, vintage)

    return entries
