"""
Command-line interface for scraping OpenStudio documentation

Usage:
    python -m bluesky.mcp.scrapers [--output OUTPUT] [--concurrent N]
"""

import argparse
import asyncio
from pathlib import Path

from .db_builder import build_database
from .openstudio_docs_scraper import OpenStudioDocsScraper


async def main():
    parser = argparse.ArgumentParser(description="Scrape OpenStudio documentation and build database")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path(__file__).parent.parent / "data" / "openstudio-3.9.0.db",
        help="Output database path",
    )
    parser.add_argument(
        "--concurrent",
        "-c",
        type=int,
        default=50,
        help="Maximum concurrent HTTP requests",
    )
    parser.add_argument(
        "--version",
        "-v",
        default="3.9.0",
        help="OpenStudio version",
    )

    args = parser.parse_args()

    # Scrape classes
    async with OpenStudioDocsScraper(max_concurrent=args.concurrent) as scraper:
        classes = await scraper.scrape_all_classes()

    # Build database
    build_database(
        classes=classes,
        db_path=args.output,
        version=args.version,
        source_url=OpenStudioDocsScraper.BASE_URL,
    )


if __name__ == "__main__":
    asyncio.run(main())
