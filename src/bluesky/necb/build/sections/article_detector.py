"""
Hierarchical article structure detection using regex patterns and state machine.

NECB Hierarchy:
    Division (A, B, C, D)
    └── Part (3)
        └── Section (3.5)
            └── Subsection (3.5.2)
                └── Article (3.5.2.1)
                    └── Sentence (3.5.2.1.(1))
                        └── Clause (3.5.2.1.(1)(a))
                            └── Subclause (3.5.2.1.(1)(a)(i))
"""

import logging
import re
from typing import List, Optional, Tuple

from . import config
from .article_models import Article, Sentence, Clause, Subclause, Part, Section, build_reference

logger = logging.getLogger(__name__)

# Pattern for page markers embedded in text: <<<PAGE:123>>>
PAGE_MARKER_PATTERN = re.compile(r'^<<<PAGE:(\d+)>>>$')


# ============================================================
# PATTERN MATCHING FUNCTIONS
# ============================================================

def detect_division(line: str) -> Optional[str]:
    """Detect Division pattern in line.

    Args:
        line: Text line to check

    Returns:
        Division letter (A, B, C, D) if matched, None otherwise
    """
    match = config.DIVISION_PATTERN.match(line.strip())
    if match:
        division = match.group(1).upper()
        logger.debug(f"Detected Division {division}")
        return division
    return None


def detect_part(line: str) -> Optional[Tuple[str, Optional[str]]]:
    """Detect Part pattern in line.

    Args:
        line: Text line to check

    Returns:
        Tuple of (part_number, title) if matched, None otherwise
    """
    match = config.PART_PATTERN.match(line.strip())
    if match:
        part_number = match.group(1)
        title = match.group(2) if match.group(2) else None
        logger.debug(f"Detected Part {part_number}: {title}")
        return (part_number, title)
    return None


def detect_section(line: str) -> Optional[Tuple[str, Optional[str]]]:
    """Detect Section pattern in line.

    Args:
        line: Text line to check

    Returns:
        Tuple of (section_number, title) if matched, None otherwise
    """
    match = config.SECTION_PATTERN.match(line.strip())
    if match:
        section_number = match.group(1)
        title = match.group(2) if match.group(2) else None
        logger.debug(f"Detected Section {section_number}: {title}")
        return (section_number, title)
    return None


def detect_subsection(line: str) -> Optional[Tuple[str, Optional[str]]]:
    """Detect Subsection pattern in line.

    Args:
        line: Text line to check

    Returns:
        Tuple of (subsection_number, title) if matched, None otherwise
    """
    match = config.SUBSECTION_PATTERN.match(line.strip())
    if match:
        subsection_number = match.group(1)
        title = match.group(2) if match.group(2) else None

        # Ensure it's not an article (4 parts = article, 3 parts = subsection)
        parts = subsection_number.split(".")
        if len(parts) == 3:
            logger.debug(f"Detected Subsection {subsection_number}: {title}")
            return (subsection_number, title)

    return None


def detect_article_number_only(line: str) -> Optional[str]:
    """Detect if line contains ONLY an article number (for multi-line headers).

    In NECB PDFs, article headers can appear as:
        "4.3.2.1."                              <- line 1 (article number only)
        "Determination of Operational Times"   <- line 2 (title)

    This function detects just the article number on its own line.

    Args:
        line: Text line to check

    Returns:
        Article number if matched, None otherwise
    """
    stripped = line.strip()
    match = config.ARTICLE_PATTERN.match(stripped)
    if match:
        article_number = match.group(1)
        title_text = match.group(2).strip() if match.group(2) else ""

        # Ensure it's an article (4+ parts)
        parts = article_number.split(".")
        if len(parts) >= 4:
            # Only match if there's NO title on this line
            if not title_text:
                logger.debug(f"Detected article number only: {article_number}")
                return article_number

    return None


def detect_article(line: str) -> Optional[Tuple[str, Optional[str]]]:
    """Detect Article pattern in line.

    Only matches article headers that have BOTH an article number AND a title
    ON THE SAME LINE. For multi-line headers where the title is on the next
    line, use detect_article_number_only() and look ahead.

    Args:
        line: Text line to check

    Returns:
        Tuple of (article_number, title) if matched, None otherwise
    """
    match = config.ARTICLE_PATTERN.match(line.strip())
    if match:
        article_number = match.group(1)
        title = match.group(2).strip() if match.group(2) else None

        # Ensure it's an article (4+ parts)
        parts = article_number.split(".")
        if len(parts) >= 4:
            # Only recognize as article header if there's a title on the same line
            if title and len(title) >= 3:
                logger.debug(f"Detected Article {article_number}: {title}")
                return (article_number, title)

    return None


def is_likely_title(line: str) -> bool:
    """Check if a line looks like an article title.

    Article titles in NECB are typically:
    - Start with a capital letter
    - Don't start with numbers or clause patterns (1), a), etc.
    - Are at least 3 characters long
    - Don't contain functional statement codes like [F94-OE1.1]

    Args:
        line: Text line to check

    Returns:
        True if line looks like a title
    """
    stripped = line.strip()

    # Must have content
    if len(stripped) < 3:
        return False

    # Must start with a capital letter
    if not stripped[0].isupper():
        return False

    # Should not be a clause pattern (1), (2), etc.
    if stripped.startswith('(') and stripped[1].isdigit():
        return False

    # Should not contain functional codes like [F94-OE1.1]
    if '[F' in stripped or '[OS' in stripped:
        return False

    # Should not be a numbered sentence
    if detect_sentence(stripped):
        return False

    return True


def detect_sentence(line: str) -> Optional[Tuple[str, str]]:
    """Detect Sentence pattern in line.

    Sentences are numbered elements within an article (e.g., 3.5.2.1.(1))
    Pattern: "1)" or "1) Some text"

    Args:
        line: Text line to check

    Returns:
        Tuple of (sentence_number, text) if matched, None otherwise
    """
    match = config.SENTENCE_PATTERN.match(line.strip())
    if match:
        sentence_number = match.group(1)
        text = match.group(2)
        logger.debug(f"Detected Sentence {sentence_number})")
        return (sentence_number, text)
    return None


def detect_clause(line: str) -> Optional[Tuple[str, str]]:
    """Detect Clause pattern in line.

    Clauses are lettered elements within a sentence (e.g., 3.5.2.1.(1)(a))
    Pattern: "a)" or "a) Some text"

    Args:
        line: Text line to check

    Returns:
        Tuple of (clause_letter, text) if matched, None otherwise
    """
    match = config.CLAUSE_PATTERN.match(line.strip())
    if match:
        clause_letter = match.group(1)
        text = match.group(2)
        logger.debug(f"Detected Clause {clause_letter})")
        return (clause_letter, text)
    return None


def detect_subclause(line: str) -> Optional[Tuple[str, str]]:
    """Detect Subclause pattern (Roman numerals) in line.

    Subclauses are roman numeral elements within a clause (e.g., 3.5.2.1.(1)(a)(i))
    Pattern: "i)", "ii)", "iii)", etc.

    Args:
        line: Text line to check

    Returns:
        Tuple of (subclause_numeral, text) if matched, None otherwise
    """
    match = config.SUBCLAUSE_PATTERN.match(line.strip())
    if match:
        subclause_numeral = match.group(1).lower()
        text = match.group(2)
        logger.debug(f"Detected Subclause {subclause_numeral})")
        return (subclause_numeral, text)
    return None


def is_continuation_line(line: str) -> bool:
    """Check if line is a continuation (no numbering pattern).

    Args:
        line: Text line to check

    Returns:
        True if line appears to be continuation text
    """
    line = line.strip()

    # Empty lines are not continuation
    if not line:
        return False

    # Check if line starts with any numbering pattern
    if detect_division(line):
        return False
    if detect_part(line):
        return False
    if detect_section(line):
        return False
    if detect_subsection(line):
        return False
    if detect_article(line):
        return False
    if detect_sentence(line):
        return False
    if detect_clause(line):
        return False
    if detect_subclause(line):
        return False

    # No numbering detected - likely continuation
    return True


# ============================================================
# STATE MACHINE FOR PARSING
# ============================================================

class ParsingState:
    """State machine for tracking hierarchical parsing context.

    Tracks the NECB hierarchy:
        Division (A, B, C, D)
        └── Part (3)
            └── Section (3.5)
                └── Subsection (3.5.2)
                    └── Article (3.5.2.1)
                        └── Sentence (3.5.2.1.(1))
                            └── Clause (3.5.2.1.(1)(a))
                                └── Subclause (3.5.2.1.(1)(a)(i))
    """

    def __init__(self, vintage: str):
        """Initialize parsing state.

        Args:
            vintage: NECB vintage year
        """
        self.vintage = vintage

        # Current hierarchy context
        self.current_division: Optional[str] = None  # A, B, C, or D
        self.current_part: Optional[Part] = None
        self.current_section: Optional[Section] = None
        self.current_subsection_number: Optional[str] = None
        self.current_article: Optional[Article] = None
        self.current_sentence: Optional[Sentence] = None
        self.current_clause: Optional[Clause] = None

        # Page tracking - updated when page markers are encountered
        self.current_page: int = 0

        # Accumulator for multi-line text
        self.accumulator: List[str] = []

        # Results
        self.articles: List[Article] = []
        self.parts: List[Part] = []

        # Deduplication: track articles by (division, article_number) -> index in articles list
        # Used to keep the version with more sentences when duplicates are found
        self._article_index: dict[tuple[str, str], int] = {}

    def set_division(self, division: str):
        """Set current division.

        Args:
            division: Division letter (A, B, C, or D)
        """
        self.finalize_current_article()  # Save previous article

        self.current_division = division.upper()

        # Reset all hierarchy context when entering new division
        self.current_part = None
        self.current_section = None
        self.current_subsection_number = None
        self.current_article = None
        self.current_sentence = None
        self.current_clause = None

        logger.info(f"Entered Division {self.current_division}")

    def start_new_part(self, part_number: str, title: Optional[str]):
        """Start tracking a new Part.

        Args:
            part_number: Part number
            title: Part title
        """
        self.finalize_current_article()  # Save previous article

        self.current_part = Part(
            part_number=part_number,
            title=title,
            vintage=self.vintage
        )
        self.parts.append(self.current_part)

        # Reset section/article context
        self.current_section = None
        self.current_subsection_number = None
        self.current_article = None
        self.current_sentence = None
        self.current_clause = None

        logger.info(f"Started Part {part_number}: {title}")

    def start_new_section(self, section_number: str, title: Optional[str]):
        """Start tracking a new Section.

        Args:
            section_number: Section number
            title: Section title
        """
        self.finalize_current_article()  # Save previous article

        self.current_section = Section(
            section_number=section_number,
            title=title,
            vintage=self.vintage,
            part_number=self.current_part.part_number if self.current_part else section_number.split('.')[0]
        )

        if self.current_part:
            self.current_part.sections.append(self.current_section)

        # Reset article context
        self.current_subsection_number = None
        self.current_article = None
        self.current_sentence = None
        self.current_clause = None

        logger.info(f"Started Section {section_number}: {title}")

    def start_new_subsection(self, subsection_number: str, title: Optional[str]):
        """Start tracking a new Subsection.

        Args:
            subsection_number: Subsection number
            title: Subsection title
        """
        self.finalize_current_article()  # Save previous article

        self.current_subsection_number = subsection_number

        # Reset article context
        self.current_article = None
        self.current_sentence = None
        self.current_clause = None

        logger.info(f"Started Subsection {subsection_number}: {title}")

    def start_new_article(self, article_number: str, title: Optional[str], page_num: int):
        """Start tracking a new Article.

        Args:
            article_number: Article number
            title: Article title
            page_num: Starting page number
        """
        self.finalize_current_article()  # Save previous article

        # Extract hierarchy from article number
        parts = article_number.split(".")
        part_number = parts[0] if len(parts) >= 1 else None
        section_number = ".".join(parts[:2]) if len(parts) >= 2 else None
        subsection_number = ".".join(parts[:3]) if len(parts) >= 3 else None

        self.current_article = Article(
            article_number=article_number,
            reference=article_number,  # Article reference is same as article_number
            title=title,
            vintage=self.vintage,
            division=self.current_division,
            hierarchy_level=config.HierarchyLevel.ARTICLE,
            part_number=part_number,
            section_number=section_number,
            subsection_number=subsection_number,
            full_text="",
            page_start=page_num
        )

        # Reset sentence/clause context
        self.current_sentence = None
        self.current_clause = None

        # Start accumulator with title if present
        self.accumulator = [f"{article_number} {title}"] if title else [article_number]

        logger.info(f"Started Article {article_number}: {title}")

    def add_sentence(self, sentence_number: str, text: str):
        """Add a sentence to current article.

        Sentences are numbered elements like 1), 2), 3)
        Full reference format: 3.5.2.1.(1)

        Args:
            sentence_number: Sentence number (e.g., "1", "2", "3")
            text: Sentence text
        """
        if not self.current_article:
            logger.warning(f"Sentence {sentence_number} found outside article context")
            return

        # Build full reference for this sentence
        reference = build_reference(
            self.current_article.article_number,
            sentence=sentence_number
        )

        self.current_sentence = Sentence(
            sentence_number=sentence_number,
            reference=reference,
            text=text
        )
        self.current_article.sentences.append(self.current_sentence)

        # Reset clause context
        self.current_clause = None

        # Add to accumulator
        self.accumulator.append(f"{sentence_number}) {text}")

    def add_clause(self, clause_letter: str, text: str):
        """Add a clause to current sentence.

        Clauses are lettered elements like a), b), c)
        Full reference format: 3.5.2.1.(1)(a)

        Args:
            clause_letter: Clause letter (e.g., "a", "b", "c")
            text: Clause text
        """
        if not self.current_sentence:
            logger.warning(f"Clause {clause_letter} found outside sentence context")
            return

        # Build full reference for this clause
        reference = build_reference(
            self.current_article.article_number,
            sentence=self.current_sentence.sentence_number,
            clause=clause_letter
        )

        self.current_clause = Clause(
            clause_letter=clause_letter,
            reference=reference,
            text=text
        )
        self.current_sentence.clauses.append(self.current_clause)

        # Add to accumulator
        self.accumulator.append(f"  {clause_letter}) {text}")

    def add_subclause(self, subclause_numeral: str, text: str):
        """Add a subclause to current clause.

        Subclauses are roman numeral elements like i), ii), iii)
        Full reference format: 3.5.2.1.(1)(a)(i)

        Args:
            subclause_numeral: Subclause numeral (e.g., "i", "ii", "iii")
            text: Subclause text
        """
        if not self.current_clause:
            logger.warning(f"Subclause {subclause_numeral} found outside clause context")
            return

        # Build full reference for this subclause
        reference = build_reference(
            self.current_article.article_number,
            sentence=self.current_sentence.sentence_number,
            clause=self.current_clause.clause_letter,
            subclause=subclause_numeral
        )

        subclause = Subclause(
            subclause_numeral=subclause_numeral,
            reference=reference,
            text=text
        )
        self.current_clause.subclauses.append(subclause)

        # Add to accumulator
        self.accumulator.append(f"    {subclause_numeral}) {text}")

    def add_continuation(self, text: str):
        """Add continuation text to current context.

        Continuation lines are appended to:
        1. The accumulator (for building full_text)
        2. The current lowest-level element (subclause > clause > sentence)

        Args:
            text: Continuation text
        """
        if text.strip():
            self.accumulator.append(text)

            # Also append to the current lowest-level element's text
            if self.current_clause and self.current_clause.subclauses:
                # Continuation of the last subclause
                last_subclause = self.current_clause.subclauses[-1]
                last_subclause.text = last_subclause.text + " " + text.strip()
            elif self.current_clause:
                # Continuation of the current clause
                self.current_clause.text = self.current_clause.text + " " + text.strip()
            elif self.current_sentence:
                # Continuation of the current sentence
                self.current_sentence.text = self.current_sentence.text + " " + text.strip()

    def finalize_current_article(self):
        """Finalize and save current article.

        Handles deduplication: if an article with the same (division, article_number)
        already exists, keeps the one with more content. This handles NECB's structure
        where the same article number appears in both:
        - Division B: actual code text with sentences and detailed content
        - Division C: functional statement index with just [F94-OE1.1] codes

        We compare by: (1) sentence count, then (2) text length as tiebreaker.
        """
        if self.current_article:
            # Set page_end to current page (the article ends on the page we're currently on)
            self.current_article.page_end = self.current_page

            # Join accumulated text
            self.current_article.full_text = "\n".join(self.accumulator)

            # Validate minimum length
            if len(self.current_article.full_text) >= config.MIN_ARTICLE_LENGTH:
                # Create key for deduplication
                key = (self.current_article.division or "", self.current_article.article_number)

                if key in self._article_index:
                    # Duplicate found - keep the one with more content
                    existing_idx = self._article_index[key]
                    existing = self.articles[existing_idx]

                    # Compare by sentence count first, then text length as tiebreaker
                    new_score = (len(self.current_article.sentences), len(self.current_article.full_text))
                    existing_score = (len(existing.sentences), len(existing.full_text))

                    if new_score > existing_score:
                        # New article has more content - replace
                        logger.info(
                            f"Replacing Article {key[1]} in Division {key[0] or 'unknown'}: "
                            f"new has {len(self.current_article.sentences)} sentences/{len(self.current_article.full_text)} chars vs "
                            f"existing {len(existing.sentences)} sentences/{len(existing.full_text)} chars"
                        )
                        self.articles[existing_idx] = self.current_article
                    else:
                        # Keep existing article (it has more or equal content)
                        logger.debug(
                            f"Skipping duplicate Article {key[1]} in Division {key[0] or 'unknown'}: "
                            f"existing has {len(existing.sentences)} sentences/{len(existing.full_text)} chars, "
                            f"new has {len(self.current_article.sentences)} sentences/{len(self.current_article.full_text)} chars"
                        )
                else:
                    # New article - add to list and index
                    self._article_index[key] = len(self.articles)
                    self.articles.append(self.current_article)
                    logger.info(f"Finalized Article {self.current_article.article_number}")
            else:
                logger.warning(
                    f"Article {self.current_article.article_number} too short ({len(self.current_article.full_text)} chars), skipping"
                )

            # Clear accumulator
            self.accumulator = []
            self.current_article = None


# ============================================================
# MAIN PARSING FUNCTION
# ============================================================

def parse_document_text(text: str, vintage: str, start_page: int = 0) -> List[Article]:
    """Parse document text into structured articles.

    Args:
        text: Complete document text (newline-separated)
        vintage: NECB vintage year
        start_page: Starting page number for tracking

    Returns:
        List of parsed Article objects
    """
    logger.info(f"Starting document parsing for NECB {vintage}")

    lines = text.split("\n")
    state = ParsingState(vintage)
    state.current_page = start_page

    for i, line in enumerate(lines):
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Check for page marker: <<<PAGE:123>>>
        page_match = PAGE_MARKER_PATTERN.match(line)
        if page_match:
            state.current_page = int(page_match.group(1))
            logger.debug(f"Page marker detected: now on page {state.current_page}")
            continue

        # Try to detect structure patterns (in order of hierarchy)
        division_match = detect_division(line)
        if division_match:
            state.set_division(division_match)
            continue

        part_match = detect_part(line)
        if part_match:
            state.start_new_part(part_match[0], part_match[1])
            continue

        section_match = detect_section(line)
        if section_match:
            state.start_new_section(section_match[0], section_match[1])
            continue

        subsection_match = detect_subsection(line)
        if subsection_match:
            state.start_new_subsection(subsection_match[0], subsection_match[1])
            continue

        # Try to detect article with title on same line
        article_match = detect_article(line)
        if article_match:
            state.start_new_article(article_match[0], article_match[1], state.current_page)
            continue

        # Try to detect article number only (title may be on next line)
        article_num_only = detect_article_number_only(line)
        if article_num_only:
            # Look ahead to next non-empty line for title
            title = None
            for j in range(i + 1, min(i + 3, len(lines))):  # Look up to 2 lines ahead
                next_line = lines[j].strip()
                if next_line and is_likely_title(next_line):
                    title = next_line
                    break
                elif next_line:
                    # Hit non-empty line that's not a title, stop looking
                    break

            if title:
                logger.debug(f"Multi-line article header: {article_num_only} + '{title}'")
                state.start_new_article(article_num_only, title, state.current_page)
                continue
            # If no title found, don't treat as article start (likely running header)

        sentence_match = detect_sentence(line)
        if sentence_match:
            state.add_sentence(sentence_match[0], sentence_match[1])
            continue

        clause_match = detect_clause(line)
        if clause_match:
            state.add_clause(clause_match[0], clause_match[1])
            continue

        subclause_match = detect_subclause(line)
        if subclause_match:
            state.add_subclause(subclause_match[0], subclause_match[1])
            continue

        # No pattern matched - treat as continuation
        state.add_continuation(line)

    # Finalize last article
    state.finalize_current_article()

    logger.info(f"Parsing complete: {len(state.articles)} articles extracted")
    return state.articles
