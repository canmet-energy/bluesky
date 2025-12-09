"""
Main orchestrator for NECB figure extraction pipeline.

Coordinates extraction, detection, storage, and organization of figures from NECB PDFs.
"""

import logging
import time
from pathlib import Path
from typing import List, Optional, Dict

import click

from . import figure_config as config
from . import figure_db as db
from . import figure_extractor as extractor
from . import figure_detector as detector
from . import crop_figures
from .figure_models import Figure, FigureParseResult
from bluesky.necb.build import get_division_for_page

logger = logging.getLogger(__name__)


# ============================================================
# FIGURE PROCESSING PIPELINE
# ============================================================

def process_image_with_multiple_figures(
    image_obj,
    image_type: str,
    vintage: str,
    page_num: int,
    text_blocks: List,
    page_height: float,
    doc,
    page,
    crop_coords: Optional[Dict[str, Dict[str, int]]] = None
) -> List[Figure]:
    """Process an image that may contain multiple figures.

    Some images (especially large vector graphics) contain multiple labeled figures.
    This function detects all figure labels within or below the image.

    Args:
        image_obj: BitmapImage or VectorDrawing object
        image_type: "bitmap" or "vector"
        vintage: NECB vintage year
        page_num: Page number (0-indexed)
        text_blocks: List of TextBlock objects on the page
        page_height: Page height in points
        doc: PyMuPDF Document (for bitmap extraction)
        page: PyMuPDF Page (for vector rendering)
        crop_coords: Optional dict of crop coordinates for auto-cropping

    Returns:
        List of Figure objects (may be empty if no labels found)
    """
    figures = []

    try:
        # Find ALL figure labels for this image
        label_results = detector.find_all_figure_labels(
            image_obj.bbox,
            text_blocks,
            page_height
        )

        if not label_results:
            logger.warning(f"No labels found for {image_type} image on page {page_num}")
            return figures

        # Process each detected label
        for label, label_block in label_results:
            try:
                # Find caption for this specific label
                caption = detector.find_figure_caption(label_block, text_blocks)

                # Determine output path
                output_path = config.get_figure_output_path(label, vintage, extension="png")

                # Save image to disk (same image for all labels, may overwrite)
                if image_type == "bitmap":
                    metadata = extractor.save_bitmap_image(image_obj, output_path)
                else:  # vector
                    metadata = extractor.save_vector_image(image_obj, page, output_path)

                # Auto-crop if coordinates exist
                if crop_coords and label in crop_coords:
                    try:
                        coords = crop_coords[label]
                        crop_tuple = (coords['x'], coords['y'], coords['width'], coords['height'])
                        if crop_figures.apply_crop(output_path, crop_tuple):
                            logger.info(f"Auto-cropped figure {label} using saved coordinates")
                            # Update metadata with cropped dimensions
                            metadata['width'] = coords['width']
                            metadata['height'] = coords['height']
                            # Update file size after crop
                            metadata['file_size'] = output_path.stat().st_size
                        else:
                            logger.warning(f"Failed to auto-crop figure {label}")
                    except Exception as e:
                        logger.error(f"Error auto-cropping figure {label}: {e}")

                # Create relative path for database storage
                relative_path = str(output_path.relative_to(config.FIGURE_OUTPUT_DIR.parent))

                # Determine division from page number
                division = get_division_for_page(page_num, vintage)

                # Create Figure object
                figure = Figure(
                    label=label,
                    caption=caption,
                    vintage=vintage,
                    division=division,
                    page=page_num,
                    bbox=image_obj.bbox,
                    image_path=relative_path,
                    image_type=image_type,
                    image_format=metadata["format"],
                    width=metadata["width"],
                    height=metadata["height"],
                    file_size=metadata["file_size"]
                )

                figures.append(figure)
                logger.info(f"Processed figure {label} ({image_type}) on page {page_num}")

            except Exception as e:
                logger.error(f"Failed to process label {label} on page {page_num}: {e}")
                continue

    except Exception as e:
        logger.error(f"Failed to process {image_type} image on page {page_num}: {e}")

    return figures


def extract_figures_from_pdf(pdf_path: Path, vintage: str) -> FigureParseResult:
    """Extract all figures from a NECB PDF.

    Args:
        pdf_path: Path to PDF file
        vintage: NECB vintage year

    Returns:
        FigureParseResult with extracted figures and statistics
    """
    start_time = time.time()

    result = FigureParseResult(
        vintage=vintage,
        total_pages=0,
        total_figures=0,
        total_bitmaps=0,
        total_vectors=0
    )

    try:
        # Load PDF
        logger.info(f"Loading PDF: {pdf_path}")
        doc = extractor.load_pdf(pdf_path)
        result.total_pages = doc.page_count

        # Extract text blocks from all pages (needed for label/caption detection)
        logger.info("Extracting text blocks from all pages...")
        text_blocks_by_page = extractor.extract_all_text_blocks(doc)

        # Load saved crop coordinates for auto-cropping
        crop_coords = crop_figures.load_crop_coordinates(vintage)
        if crop_coords:
            logger.info(f"Loaded {len(crop_coords)} saved crop coordinates for auto-cropping")
        else:
            logger.info("No saved crop coordinates found - figures will not be auto-cropped")

        # Process each page
        for page_num in range(doc.page_count):
            page = doc[page_num]
            page_height = page.rect.height
            text_blocks = text_blocks_by_page.get(page_num, [])

            # Extract bitmap images
            bitmaps = extractor.extract_bitmap_images(page, page_num, doc)
            for bitmap in bitmaps:
                figures = process_image_with_multiple_figures(
                    bitmap, "bitmap", vintage, page_num,
                    text_blocks, page_height, doc, page, crop_coords
                )
                for figure in figures:
                    result.figures.append(figure)
                    result.total_bitmaps += 1

            # Extract vector drawings
            vectors = extractor.extract_vector_drawings(page, page_num)
            for vector in vectors:
                figures = process_image_with_multiple_figures(
                    vector, "vector", vintage, page_num,
                    text_blocks, page_height, doc, page, crop_coords
                )
                for figure in figures:
                    result.figures.append(figure)
                    result.total_vectors += 1

            # Log progress
            if (page_num + 1) % config.PROGRESS_INTERVAL == 0:
                logger.info(f"Processed {page_num + 1}/{doc.page_count} pages")

        # Update totals
        result.total_figures = len(result.figures)

        # Close document
        doc.close()

        logger.info(f"Extraction complete: {result.total_figures} figures found")

    except Exception as e:
        error_msg = f"Failed to extract figures: {e}"
        logger.error(error_msg)
        result.errors.append(error_msg)
        result.success = False

    # Record processing time
    result.processing_time_seconds = time.time() - start_time

    return result


def save_figures_to_database(figures: List[Figure]) -> int:
    """Save extracted figures to database.

    Args:
        figures: List of Figure objects to save

    Returns:
        Number of figures successfully saved
    """
    logger.info(f"Saving {len(figures)} figures to database...")

    try:
        saved_count = db.insert_batch(figures)
        logger.info(f"Successfully saved {saved_count}/{len(figures)} figures")
        return saved_count
    except Exception as e:
        logger.error(f"Failed to save figures to database: {e}")
        return 0


# ============================================================
# MAIN PARSING FUNCTION
# ============================================================

def parse_figures(vintage: str, save_to_db: bool = True) -> FigureParseResult:
    """Main function to parse figures from NECB PDF.

    Args:
        vintage: NECB vintage year (2011, 2015, 2017, 2020)
        save_to_db: Whether to save figures to database

    Returns:
        FigureParseResult with extraction statistics
    """
    # Validate vintage
    if not config.is_valid_vintage(vintage):
        raise ValueError(f"Invalid vintage: {vintage}")

    # Get PDF path
    try:
        pdf_path = config.get_pdf_path(vintage)
    except FileNotFoundError as e:
        logger.error(str(e))
        raise

    # Initialize database if saving
    if save_to_db:
        logger.info("Initializing database...")
        db.init_figures_table()
        # Delete existing figures for this vintage to prevent duplicates
        deleted_count = db.delete_vintage(vintage)
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} existing figures for vintage {vintage}")

    # Extract figures from PDF
    result = extract_figures_from_pdf(pdf_path, vintage)

    # Save to database if requested
    if save_to_db and result.success and result.figures:
        saved_count = save_figures_to_database(result.figures)

        if saved_count != len(result.figures):
            result.warnings.append(
                f"Only {saved_count}/{len(result.figures)} figures saved to database"
            )

    return result


# ============================================================
# CLI INTERFACE
# ============================================================

@click.command()
@click.argument("vintage", type=click.Choice(["2011", "2015", "2017", "2020"]))
@click.option(
    "--no-db",
    is_flag=True,
    help="Skip saving to database (extract images only)",
    show_default=True
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
    show_default=True
)
def main(vintage: str, no_db: bool, verbose: bool):
    """Extract figures from NECB PDF.

    VINTAGE: NECB vintage year (2011, 2015, 2017, 2020)

    Examples:
        python -m bluesky.mcp.scrapers.necb.parsers.figures.figure_parser 2020
        python -m bluesky.mcp.scrapers.necb.parsers.figures.figure_parser 2020 --no-db
        python -m bluesky.mcp.scrapers.necb.parsers.figures.figure_parser 2020 -v
    """
    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger.info(f"Starting figure extraction for NECB {vintage}")
    logger.info(f"Output directory: {config.FIGURE_OUTPUT_DIR}")
    logger.info(f"Database: {'Enabled' if not no_db else 'Disabled'}")

    try:
        # Parse figures
        result = parse_figures(vintage, save_to_db=not no_db)

        # Print summary
        print("\n" + "=" * 70)
        print(result.get_summary())
        print("=" * 70)

        if not result.success:
            click.echo("\n❌ Extraction failed!", err=True)
            return 1

        if result.warnings:
            click.echo(f"\n⚠️  {len(result.warnings)} warnings encountered")

        click.echo("\n✅ Extraction complete!")

        # Show database info if saved
        if not no_db:
            db_info = db.get_database_info()
            if db_info.get("table_exists"):
                print(f"\nDatabase: {db_info['path']}")
                print(f"Total figures in DB: {db_info['total_figures']}")
                print("Figures by vintage:")
                for v, count in db_info['vintage_stats'].items():
                    print(f"  {v}: {count} figures")

        return 0

    except Exception as e:
        logger.exception("Fatal error during extraction")
        click.echo(f"\n❌ Fatal error: {e}", err=True)
        return 1


if __name__ == "__main__":
    main()
