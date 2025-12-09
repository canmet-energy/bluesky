"""
NECB Section Parser - Article-level structured text extraction.

This module extracts hierarchical article structure from NECB PDF documents:

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

Key Components:
- article_parser: Main orchestration pipeline
- article_extractor: PyMuPDF text extraction
- article_detector: Structure detection with regex patterns
- header_footer_cleaner: Multi-layer cleaning pipeline
- article_models: Pydantic data models
- article_db: SQLite database operations
- config: Configuration constants and patterns

Example Usage:
    from bluesky.necb.build.sections import parse_pdf

    articles = parse_pdf("NECB-2020.pdf", vintage="2020")
    for article in articles:
        print(f"{article.article_number}: {article.title}")
"""

__version__ = "0.1.0"

# Import public API
from .article_parser import parse_pdf, parse_vintage, parse_all_vintages
from .article_models import (
    Article,
    Sentence,
    Clause,
    Subclause,
    Section,
    Part,
    ParseResult,
    build_reference,
)
from .article_db import (
    init_database,
    get_article_by_number,
    get_articles_by_vintage,
    get_vintage_stats,
    get_database_info,
)

# Public API
__all__ = [
    # Main parsing functions
    "parse_pdf",
    "parse_vintage",
    "parse_all_vintages",
    # Data models (using correct NECB terminology)
    "Article",
    "Sentence",      # Pattern: 1), 2), 3) - e.g., 3.5.2.1.(1)
    "Clause",        # Pattern: a), b), c) - e.g., 3.5.2.1.(1)(a)
    "Subclause",     # Pattern: i), ii), iii) - e.g., 3.5.2.1.(1)(a)(i)
    "Section",
    "Part",
    "ParseResult",
    "build_reference",
    # Database functions
    "init_database",
    "get_article_by_number",
    "get_articles_by_vintage",
    "get_vintage_stats",
    "get_database_info",
]
