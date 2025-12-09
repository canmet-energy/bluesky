"""
PDF image extraction using PyMuPDF.

Extracts both bitmap and vector images from NECB PDFs with coordinate information.
"""

import logging
from pathlib import Path
from typing import List, Tuple, Optional
from collections import defaultdict

import fitz  # PyMuPDF

from . import figure_config as config
from .figure_models import BitmapImage, VectorDrawing, TextBlock

logger = logging.getLogger(__name__)


# ============================================================
# PDF LOADING
# ============================================================

def load_pdf(pdf_path: Path) -> fitz.Document:
    """Load PDF document using PyMuPDF.

    Args:
        pdf_path: Path to PDF file

    Returns:
        PyMuPDF Document object

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        RuntimeError: If PDF cannot be loaded
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    try:
        doc = fitz.open(pdf_path)
        logger.info(f"Loaded PDF: {pdf_path} ({doc.page_count} pages)")
        return doc
    except Exception as e:
        raise RuntimeError(f"Failed to load PDF {pdf_path}: {e}")


# ============================================================
# BITMAP IMAGE EXTRACTION
# ============================================================

def extract_bitmap_images(page: fitz.Page, page_num: int, doc: fitz.Document) -> List[BitmapImage]:
    """Extract bitmap images from a PDF page.

    Args:
        page: PyMuPDF Page object
        page_num: Page number (0-indexed)
        doc: PyMuPDF Document object (for extract_image)

    Returns:
        List of BitmapImage objects
    """
    images = []

    # Get all images on page
    # Returns list of tuples: (xref, smask, width, height, bpc, colorspace, alt. colorspace, name, filter, bbox)
    image_list = page.get_images(full=True)

    for img_index, img_info in enumerate(image_list):
        try:
            xref = img_info[0]
            smask = img_info[1]
            width = img_info[2]
            height = img_info[3]
            bpc = img_info[4]
            colorspace = img_info[5]
            # bbox is the last element
            bbox = img_info[-1] if len(img_info) > 7 else None

            # Skip very small images (likely icons, bullets, etc.)
            if width < config.MIN_IMAGE_WIDTH or height < config.MIN_IMAGE_HEIGHT:
                logger.debug(f"Skipping small image on page {page_num}: {width}x{height}")
                continue

            # Extract image data
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]

            # Get bounding box from page if not in image_info
            if bbox is None:
                # Try to find bbox by searching page blocks
                # This is less accurate but better than nothing
                bbox = (0, 0, width, height)

            # Create BitmapImage object
            bitmap = BitmapImage(
                page=page_num,
                index=img_index,
                xref=xref,
                bbox=bbox,
                width=width,
                height=height,
                colorspace=colorspace,
                bpc=bpc,
                image_data=image_bytes,
                ext=image_ext
            )

            images.append(bitmap)
            logger.debug(f"Extracted bitmap image {img_index} from page {page_num}: {width}x{height} {image_ext}")

        except Exception as e:
            logger.error(f"Failed to extract image {img_index} from page {page_num}: {e}")

    return images


def save_bitmap_image(image: BitmapImage, output_path: Path) -> dict:
    """Save bitmap image to disk.

    Args:
        image: BitmapImage object
        output_path: Path to save image

    Returns:
        Dictionary with metadata: width, height, format, file_size
    """
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write image bytes to file
    with open(output_path, 'wb') as f:
        f.write(image.image_data)

    file_size = output_path.stat().st_size

    logger.debug(f"Saved bitmap image to {output_path} ({file_size} bytes)")

    return {
        "width": image.width,
        "height": image.height,
        "format": image.ext,
        "file_size": file_size
    }


# ============================================================
# VECTOR GRAPHICS EXTRACTION
# ============================================================

def extract_vector_drawings(page: fitz.Page, page_num: int) -> List[VectorDrawing]:
    """Detect vector graphics regions on a page.

    Args:
        page: PyMuPDF Page object
        page_num: Page number (0-indexed)

    Returns:
        List of VectorDrawing objects
    """
    drawings = []

    try:
        # Get all drawing paths
        paths = page.get_drawings()

        if not paths:
            return drawings

        # Group paths by proximity to identify figure regions
        # This is a simplified approach - group all drawings into one region per page
        # In a more sophisticated version, we'd cluster by spatial proximity

        # Get overall bounding box of all drawings
        if paths:
            # Calculate bounding box from all path rectangles
            all_rects = []
            for path in paths:
                if "rect" in path:
                    all_rects.append(path["rect"])

            if all_rects:
                # Combine all rectangles
                min_x0 = min(rect[0] for rect in all_rects)
                min_y0 = min(rect[1] for rect in all_rects)
                max_x1 = max(rect[2] for rect in all_rects)
                max_y1 = max(rect[3] for rect in all_rects)

                bbox = (min_x0, min_y0, max_x1, max_y1)
                width = max_x1 - min_x0
                height = max_y1 - min_y0

                # Skip very small regions
                if width < config.MIN_IMAGE_WIDTH or height < config.MIN_IMAGE_HEIGHT:
                    logger.debug(f"Skipping small vector region on page {page_num}: {width}x{height}")
                    return drawings

                vector = VectorDrawing(
                    page=page_num,
                    bbox=bbox,
                    element_count=len(paths),
                    width=width,
                    height=height
                )

                drawings.append(vector)
                logger.debug(f"Detected vector drawing on page {page_num}: {width}x{height}, {len(paths)} elements")

    except Exception as e:
        logger.error(f"Failed to extract vector drawings from page {page_num}: {e}")

    return drawings


def render_vector_to_image(page: fitz.Page, bbox: Tuple[float, float, float, float], dpi: int = None) -> bytes:
    """Render vector graphics region to PNG.

    Args:
        page: PyMuPDF Page object
        bbox: Bounding box to render (x0, y0, x1, y1)
        dpi: Resolution in DPI (default from config)

    Returns:
        PNG image bytes
    """
    if dpi is None:
        dpi = config.VECTOR_DPI

    try:
        # Create a clip rectangle from bbox
        clip = fitz.Rect(bbox)

        # Render the region to a pixmap
        pixmap = page.get_pixmap(clip=clip, dpi=dpi)

        # Convert to PNG bytes
        png_bytes = pixmap.tobytes("png")

        logger.debug(f"Rendered vector region {bbox} to PNG ({len(png_bytes)} bytes)")

        return png_bytes

    except Exception as e:
        logger.error(f"Failed to render vector region {bbox}: {e}")
        raise


def save_vector_image(vector: VectorDrawing, page: fitz.Page, output_path: Path, dpi: int = None) -> dict:
    """Render and save vector graphics to disk.

    Args:
        vector: VectorDrawing object
        page: PyMuPDF Page object
        output_path: Path to save image
        dpi: Resolution in DPI (default from config)

    Returns:
        Dictionary with metadata: width, height, format, file_size
    """
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Render to PNG
    png_bytes = render_vector_to_image(page, vector.bbox, dpi)

    # Write to file
    with open(output_path, 'wb') as f:
        f.write(png_bytes)

    file_size = output_path.stat().st_size

    logger.debug(f"Saved vector image to {output_path} ({file_size} bytes)")

    # Calculate actual pixel dimensions based on DPI
    if dpi is None:
        dpi = config.VECTOR_DPI

    scale = dpi / 72.0  # PDF uses 72 DPI natively
    pixel_width = int(vector.width * scale)
    pixel_height = int(vector.height * scale)

    return {
        "width": pixel_width,
        "height": pixel_height,
        "format": "png",
        "file_size": file_size
    }


# ============================================================
# TEXT BLOCK EXTRACTION (For Label/Caption Detection)
# ============================================================

def extract_text_blocks(page: fitz.Page, page_num: int) -> List[TextBlock]:
    """Extract text blocks with coordinates from a PDF page.

    Args:
        page: PyMuPDF Page object
        page_num: Page number (0-indexed)

    Returns:
        List of TextBlock objects
    """
    blocks = []

    # Get text blocks with coordinates
    # Block format: (x0, y0, x1, y1, "text", block_no, block_type)
    raw_blocks = page.get_text("blocks")

    for block in raw_blocks:
        x0, y0, x1, y1, text, block_no, block_type = block

        # Filter out image blocks (block_type == 1)
        if block_type == 1:
            continue

        # Create TextBlock
        text_block = TextBlock(
            page=page_num,
            x0=x0,
            y0=y0,
            x1=x1,
            y1=y1,
            text=text  # Keep original text with line breaks
        )

        blocks.append(text_block)

    logger.debug(f"Page {page_num}: Extracted {len(blocks)} text blocks")
    return blocks


# ============================================================
# COMBINED EXTRACTION PIPELINE
# ============================================================

def extract_all_images(doc: fitz.Document) -> Tuple[List[BitmapImage], List[VectorDrawing]]:
    """Extract both bitmap and vector images from entire document.

    Args:
        doc: PyMuPDF Document object

    Returns:
        Tuple of (bitmap_images, vector_drawings)
    """
    all_bitmaps = []
    all_vectors = []

    for page_num in range(doc.page_count):
        page = doc[page_num]

        # Extract bitmaps
        bitmaps = extract_bitmap_images(page, page_num, doc)
        all_bitmaps.extend(bitmaps)

        # Extract vectors
        vectors = extract_vector_drawings(page, page_num)
        all_vectors.extend(vectors)

        if (page_num + 1) % config.PROGRESS_INTERVAL == 0:
            logger.info(f"Extracted images from {page_num + 1}/{doc.page_count} pages")

    logger.info(f"Extraction complete: {len(all_bitmaps)} bitmaps, {len(all_vectors)} vectors")

    return all_bitmaps, all_vectors


def extract_all_text_blocks(doc: fitz.Document) -> dict:
    """Extract text blocks from entire document, organized by page.

    Args:
        doc: PyMuPDF Document object

    Returns:
        Dictionary mapping page_num to List[TextBlock]
    """
    text_blocks_by_page = {}

    for page_num in range(doc.page_count):
        page = doc[page_num]
        blocks = extract_text_blocks(page, page_num)
        text_blocks_by_page[page_num] = blocks

        if (page_num + 1) % config.PROGRESS_INTERVAL == 0:
            logger.info(f"Extracted text from {page_num + 1}/{doc.page_count} pages")

    total_blocks = sum(len(blocks) for blocks in text_blocks_by_page.values())
    logger.info(f"Text extraction complete: {total_blocks} blocks from {doc.page_count} pages")

    return text_blocks_by_page
