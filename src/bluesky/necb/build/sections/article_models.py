"""
Pydantic data models for NECB article extraction.

Defines validated data structures for hierarchical article parsing using
correct NECB terminology:

NECB Hierarchy:
    Division (A, B, C, D)
    └── Part (3)
        └── Section (3.5)
            └── Subsection (3.5.2)
                └── Article (3.5.2.1)
                    └── Sentence (3.5.2.1.(1))
                        └── Clause (3.5.2.1.(1)(a))
                            └── Subclause (3.5.2.1.(1)(a)(i))

Reference format: 3.5.2.1.(2)(a)(i) = Part 3, Section 5, Subsection 2,
                                       Article 1, Sentence 2, Clause a, Subclause i
"""

import json
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================
# REFERENCE BUILDER
# ============================================================

def build_reference(
    article_number: str,
    sentence: Optional[str] = None,
    clause: Optional[str] = None,
    subclause: Optional[str] = None
) -> str:
    """Build NECB reference string like 3.5.2.1.(2)(a)(i).

    Args:
        article_number: Base article number (e.g., '3.5.2.1')
        sentence: Sentence number (e.g., '2')
        clause: Clause letter (e.g., 'a')
        subclause: Subclause numeral (e.g., 'i')

    Returns:
        Full NECB reference string
    """
    ref = article_number
    if sentence:
        ref += f".({sentence})"
    if clause:
        ref += f"({clause})"
    if subclause:
        ref += f"({subclause})"
    return ref


# ============================================================
# SENTENCE, CLAUSE, AND SUBCLAUSE MODELS
# ============================================================

class Subclause(BaseModel):
    """A subclause within a clause (e.g., 3.5.2.1.(1)(a)(i)).

    Subclauses are identified by roman numerals: i), ii), iii), etc.
    """

    subclause_numeral: str = Field(..., description="Subclause identifier (e.g., 'i', 'ii', 'iii')")
    reference: str = Field(..., description="Full NECB reference (e.g., '3.5.2.1.(1)(a)(i)')")
    text: str = Field(..., description="Subclause text content")

    @field_validator("subclause_numeral")
    @classmethod
    def validate_subclause_numeral(cls, v: str) -> str:
        """Validate subclause numbering (Roman numerals)."""
        valid_numerals = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"]
        if v.lower() not in valid_numerals:
            raise ValueError(f"Invalid subclause numeral: {v}")
        return v.lower()


class Clause(BaseModel):
    """A clause within a sentence (e.g., 3.5.2.1.(1)(a)).

    Clauses are identified by lowercase letters: a), b), c), etc.
    """

    clause_letter: str = Field(..., description="Clause letter (e.g., 'a', 'b', 'c')")
    reference: str = Field(..., description="Full NECB reference (e.g., '3.5.2.1.(1)(a)')")
    text: str = Field(..., description="Clause text content")
    subclauses: List[Subclause] = Field(
        default_factory=list,
        description="Subclauses nested under this clause"
    )

    @field_validator("clause_letter")
    @classmethod
    def validate_clause_letter(cls, v: str) -> str:
        """Validate clause lettering (lowercase letters)."""
        if not v.islower() or len(v) != 1 or not v.isalpha():
            raise ValueError(f"Invalid clause letter: {v}. Must be single lowercase letter.")
        return v


class Sentence(BaseModel):
    """A numbered sentence within an article (e.g., 3.5.2.1.(1)).

    Sentences are identified by numbers: 1), 2), 3), etc.
    """

    sentence_number: str = Field(..., description="Sentence number (e.g., '1', '2', '3')")
    reference: str = Field(..., description="Full NECB reference (e.g., '3.5.2.1.(1)')")
    text: str = Field(..., description="Sentence text content")
    clauses: List[Clause] = Field(
        default_factory=list,
        description="Clauses nested under this sentence"
    )

    @field_validator("sentence_number")
    @classmethod
    def validate_sentence_number(cls, v: str) -> str:
        """Validate sentence numbering (positive integers)."""
        if not v.isdigit() or int(v) < 1:
            raise ValueError(f"Invalid sentence number: {v}. Must be positive integer.")
        return v


# ============================================================
# ARTICLE MODEL
# ============================================================

class Article(BaseModel):
    """A complete NECB article with hierarchical structure."""

    # Identification
    article_number: str = Field(..., description="Article number (e.g., '8.1.1.2')")
    reference: str = Field(..., description="Full NECB reference (same as article_number for articles)")
    title: Optional[str] = Field(None, description="Article title if present")
    vintage: str = Field(..., description="NECB vintage year (2011, 2015, 2017, 2020)")
    division: Optional[str] = Field(None, description="Division (A, B, C, or D)")

    # Hierarchy
    hierarchy_level: str = Field(..., description="Level in hierarchy (part, section, article, etc.)")
    parent_id: Optional[int] = Field(None, description="Database ID of parent article")

    # Content
    full_text: str = Field(..., description="Complete article text with all sentences")
    sentences: List[Sentence] = Field(
        default_factory=list,
        description="Numbered sentences within this article"
    )

    # Metadata
    page_start: Optional[int] = Field(None, description="Starting page number in PDF")
    page_end: Optional[int] = Field(None, description="Ending page number in PDF")
    extracted_at: datetime = Field(default_factory=datetime.now, description="Extraction timestamp")

    # Database ID (set after insertion)
    id: Optional[int] = Field(None, description="Database primary key")

    @field_validator("article_number")
    @classmethod
    def validate_article_number(cls, v: str) -> str:
        """Validate article numbering format (e.g., 8.1.1.2)."""
        parts = v.split(".")
        if len(parts) < 2:
            raise ValueError(f"Invalid article number: {v}. Must have at least 2 parts.")

        # Check all parts are numeric
        for part in parts:
            if not part.isdigit():
                raise ValueError(f"Invalid article number: {v}. All parts must be numeric.")

        return v

    @field_validator("vintage")
    @classmethod
    def validate_vintage(cls, v: str) -> str:
        """Validate vintage year."""
        valid_vintages = ["2020"]
        if v not in valid_vintages:
            raise ValueError(f"Invalid vintage: {v}. Must be one of {valid_vintages}")
        return v

    @field_validator("hierarchy_level")
    @classmethod
    def validate_hierarchy_level(cls, v: str) -> str:
        """Validate hierarchy level."""
        valid_levels = ["part", "section", "subsection", "article", "sentence", "clause", "subclause"]
        if v not in valid_levels:
            raise ValueError(f"Invalid hierarchy level: {v}. Must be one of {valid_levels}")
        return v

    @property
    def part_number(self) -> Optional[str]:
        """Extract part number from article number (e.g., '8' from '8.1.1.2')."""
        parts = self.article_number.split(".")
        return parts[0] if len(parts) >= 1 else None

    @property
    def section_number(self) -> Optional[str]:
        """Extract section number from article number (e.g., '8.1' from '8.1.1.2')."""
        parts = self.article_number.split(".")
        return ".".join(parts[:2]) if len(parts) >= 2 else None

    @property
    def subsection_number(self) -> Optional[str]:
        """Extract subsection number from article number (e.g., '8.1.1' from '8.1.1.2')."""
        parts = self.article_number.split(".")
        return ".".join(parts[:3]) if len(parts) >= 3 else None

    def to_dict(self) -> dict:
        """Convert article to dictionary.

        Note: part_number, section_number, subsection_number are excluded
        as they are derivable from article_number.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "article_number": self.article_number,
            "title": self.title,
            "division": self.division,
            "hierarchy_level": self.hierarchy_level,
            "full_text": self.full_text,
            "sentences": [
                {
                    "sentence_number": sentence.sentence_number,
                    "reference": sentence.reference,
                    "text": sentence.text,
                    "clauses": [
                        {
                            "clause_letter": clause.clause_letter,
                            "reference": clause.reference,
                            "text": clause.text,
                            "subclauses": [
                                {
                                    "subclause_numeral": subclause.subclause_numeral,
                                    "reference": subclause.reference,
                                    "text": subclause.text,
                                }
                                for subclause in clause.subclauses
                            ]
                        }
                        for clause in sentence.clauses
                    ]
                }
                for sentence in self.sentences
            ],
            "page_start": self.page_start,
            "page_end": self.page_end,
            "extracted_at": self.extracted_at.isoformat(),
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert article to JSON string.

        Args:
            indent: JSON indentation level

        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ============================================================
# SECTION AND PART MODELS
# ============================================================

class Section(BaseModel):
    """A section containing multiple articles (e.g., Section 8.1)."""

    section_number: str = Field(..., description="Section number (e.g., '8.1')")
    title: Optional[str] = Field(None, description="Section title")
    vintage: str = Field(..., description="NECB vintage year")
    part_number: str = Field(..., description="Parent part number (e.g., '8')")
    articles: List[Article] = Field(default_factory=list, description="Articles in this section")

    @field_validator("section_number")
    @classmethod
    def validate_section_number(cls, v: str) -> str:
        """Validate section numbering format (e.g., 8.1)."""
        parts = v.split(".")
        if len(parts) != 2:
            raise ValueError(f"Invalid section number: {v}. Must have format X.Y")

        for part in parts:
            if not part.isdigit():
                raise ValueError(f"Invalid section number: {v}. All parts must be numeric.")

        return v


class Part(BaseModel):
    """A part containing multiple sections (e.g., Part 8)."""

    part_number: str = Field(..., description="Part number (e.g., '8')")
    title: Optional[str] = Field(None, description="Part title")
    vintage: str = Field(..., description="NECB vintage year")
    sections: List[Section] = Field(default_factory=list, description="Sections in this part")

    @field_validator("part_number")
    @classmethod
    def validate_part_number(cls, v: str) -> str:
        """Validate part numbering (positive integer)."""
        if not v.isdigit() or int(v) < 1:
            raise ValueError(f"Invalid part number: {v}. Must be positive integer.")
        return v


# ============================================================
# PARSING RESULT MODELS
# ============================================================

class ParseResult(BaseModel):
    """Result of parsing a single PDF document."""

    vintage: str = Field(..., description="NECB vintage year")
    total_pages: int = Field(..., description="Total pages processed")
    total_articles: int = Field(..., description="Total articles extracted")
    total_sentences: int = Field(..., description="Total sentences extracted")
    articles: List[Article] = Field(default_factory=list, description="All extracted articles")
    errors: List[str] = Field(default_factory=list, description="Parsing errors encountered")
    warnings: List[str] = Field(default_factory=list, description="Parsing warnings")

    processing_time_seconds: Optional[float] = Field(None, description="Total processing time")
    success: bool = Field(True, description="Whether parsing succeeded overall")

    def get_summary(self) -> str:
        """Get a human-readable summary of the parsing result.

        Returns:
            Formatted summary string
        """
        summary_lines = [
            f"NECB {self.vintage} Parsing Result",
            f"{'=' * 50}",
            f"Total Pages: {self.total_pages}",
            f"Total Articles: {self.total_articles}",
            f"Total Sentences: {self.total_sentences}",
            f"Errors: {len(self.errors)}",
            f"Warnings: {len(self.warnings)}",
            f"Success: {self.success}",
        ]

        if self.processing_time_seconds:
            summary_lines.append(f"Processing Time: {self.processing_time_seconds:.2f}s")

        if self.errors:
            summary_lines.append(f"\nErrors:")
            for error in self.errors[:5]:  # Show first 5 errors
                summary_lines.append(f"  - {error}")
            if len(self.errors) > 5:
                summary_lines.append(f"  ... and {len(self.errors) - 5} more")

        return "\n".join(summary_lines)
