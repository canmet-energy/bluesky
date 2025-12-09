"""
NECB Index Parser Data Models

Pydantic models for representing parsed index entries.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ArticleReference(BaseModel):
    """A reference to an NECB article."""

    article_number: str = Field(description="Article number, e.g., '3.2.4.3'")
    suffix: Optional[str] = Field(
        default=None,
        description="Letter suffix for table variants, e.g., 'A' from '8.4.4.21.-A'"
    )
    division: Optional[str] = Field(
        default=None,
        description="Division marker from [A], [B], [C]"
    )

    @property
    def full_reference(self) -> str:
        """Get full reference string."""
        ref = self.article_number
        if self.suffix:
            ref += f".-{self.suffix}"
        if self.division:
            ref += f".[{self.division}]"
        return ref


class IndexEntry(BaseModel):
    """A single entry in the NECB alphabetical index."""

    term: str = Field(description="Main index term, e.g., 'Fenestration'")
    parent_term: Optional[str] = Field(
        default=None,
        description="Parent term for sub-entries, e.g., 'Boilers' for 'efficiency requirements'"
    )
    description: Optional[str] = Field(
        default=None,
        description="Description for sub-entries, e.g., 'allowable area of'"
    )
    article_references: List[str] = Field(
        default_factory=list,
        description="List of article numbers, e.g., ['3.2.4.3', '3.1.1.6']"
    )
    division_hints: List[str] = Field(
        default_factory=list,
        description="Division hints from [A]/[C] markers"
    )
    see_also: Optional[str] = Field(
        default=None,
        description="Cross-reference text, e.g., 'Doors; Windows'"
    )
    page: int = Field(description="Page number in PDF (1-indexed)")
    vintage: str = Field(description="NECB vintage, e.g., '2020'")

    @property
    def is_main_entry(self) -> bool:
        """Check if this is a main entry (not a sub-entry)."""
        return self.parent_term is None

    @property
    def is_cross_reference(self) -> bool:
        """Check if this is a cross-reference entry."""
        return self.see_also is not None and len(self.article_references) == 0

    @property
    def display_term(self) -> str:
        """Get display term (description for sub-entries, term for main)."""
        if self.description:
            return self.description
        return self.term


class IndexParseResult(BaseModel):
    """Result of parsing NECB index from a PDF."""

    vintage: str = Field(description="NECB vintage parsed")
    total_entries: int = Field(description="Total index entries extracted")
    total_main_terms: int = Field(description="Number of main terms")
    total_sub_terms: int = Field(description="Number of sub-terms")
    total_references: int = Field(description="Total article references")
    total_cross_references: int = Field(description="Number of 'see also' entries")
    pages_parsed: int = Field(description="Number of pages parsed")
    entries: List[IndexEntry] = Field(
        default_factory=list,
        description="All parsed index entries"
    )
    success: bool = Field(default=True, description="Whether parsing succeeded")
    error: Optional[str] = Field(default=None, description="Error message if failed")

    @classmethod
    def from_entries(
        cls,
        entries: List[IndexEntry],
        vintage: str,
        pages_parsed: int,
    ) -> "IndexParseResult":
        """Create result from list of entries with computed stats."""
        main_terms = [e for e in entries if e.is_main_entry]
        sub_terms = [e for e in entries if not e.is_main_entry]
        cross_refs = [e for e in entries if e.is_cross_reference]
        total_refs = sum(len(e.article_references) for e in entries)

        return cls(
            vintage=vintage,
            total_entries=len(entries),
            total_main_terms=len(main_terms),
            total_sub_terms=len(sub_terms),
            total_references=total_refs,
            total_cross_references=len(cross_refs),
            pages_parsed=pages_parsed,
            entries=entries,
            success=True,
        )

    @classmethod
    def failure(cls, vintage: str, error: str) -> "IndexParseResult":
        """Create a failed result."""
        return cls(
            vintage=vintage,
            total_entries=0,
            total_main_terms=0,
            total_sub_terms=0,
            total_references=0,
            total_cross_references=0,
            pages_parsed=0,
            entries=[],
            success=False,
            error=error,
        )
