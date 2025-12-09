"""
Figure label and caption detection using spatial relationships.

Matches images with their labels and captions based on vertical positioning.
"""

import logging
from typing import List, Optional, Tuple

from . import figure_config as config
from .figure_models import TextBlock

logger = logging.getLogger(__name__)


# ============================================================
# LABEL DETECTION
# ============================================================

def find_figure_label(
    image_bbox: Tuple[float, float, float, float],
    text_blocks: List[TextBlock],
    page_height: float
) -> Optional[Tuple[str, TextBlock]]:
    """Find figure label within or below an image.

    Algorithm:
    1. First check text blocks WITHIN image (for embedded labels in vector graphics)
    2. Then check blocks BELOW image (for separate labels)
    3. Sort by vertical position (y0 ascending)
    4. Find first block matching FIGURE_LABEL_PATTERN
    5. Extract and normalize figure number

    Args:
        image_bbox: Image bounding box (x0, y0, x1, y1)
        text_blocks: List of TextBlock objects on the page
        page_height: Page height in points

    Returns:
        Tuple of (normalized_label, label_block) if found, None otherwise
    """
    image_top = image_bbox[1]
    image_bottom = image_bbox[3]

    # Strategy 1: Check for labels WITHIN the image bounding box
    # (common for vector graphics where label is part of the drawing)
    within_blocks = [
        block for block in text_blocks
        if block.y0 >= image_top and block.y0 <= image_bottom
    ]

    # Sort by vertical position (top to bottom)
    within_blocks.sort(key=lambda b: b.y0)

    # Look for figure label pattern within image
    for block in within_blocks:
        lines = block.text.split('\n')
        for line in lines:
            line = line.strip()
            match = config.FIGURE_LABEL_PATTERN.match(line)
            if match:
                figure_number = match.group(1)
                normalized_label = figure_number.rstrip('.')
                logger.debug(f"Found figure label WITHIN image: {normalized_label} at y={block.y0:.1f}")
                return (normalized_label, block)

    # Strategy 2: Check for labels BELOW the image
    # (traditional approach for separate label text)
    below_blocks = [
        block for block in text_blocks
        if block.is_below(image_bottom, tolerance=config.VERTICAL_TOLERANCE)
    ]

    # Sort by vertical position (top to bottom)
    below_blocks.sort(key=lambda b: b.y0)

    # Find first block matching figure label pattern
    for block in below_blocks:
        lines = block.text.split('\n')
        for line in lines:
            line = line.strip()
            match = config.FIGURE_LABEL_PATTERN.match(line)
            if match:
                figure_number = match.group(1)
                normalized_label = figure_number.rstrip('.')
                logger.debug(f"Found figure label BELOW image: {normalized_label} at y={block.y0:.1f}")
                return (normalized_label, block)

    logger.debug(f"No figure label found within or below image at {image_bbox}")
    return None


def find_all_figure_labels(
    image_bbox: Tuple[float, float, float, float],
    text_blocks: List[TextBlock],
    page_height: float
) -> List[Tuple[str, TextBlock]]:
    """Find ALL figure labels within or below an image.

    This handles cases where one large image contains multiple figures.

    Algorithm:
    1. Check text blocks WITHIN image bounding box
    2. Check text blocks BELOW image bounding box
    3. Find ALL blocks matching FIGURE_LABEL_PATTERN
    4. Return list of (label, block) tuples

    Args:
        image_bbox: Image bounding box (x0, y0, x1, y1)
        text_blocks: List of TextBlock objects on the page
        page_height: Page height in points

    Returns:
        List of (normalized_label, label_block) tuples (may be empty)
    """
    image_top = image_bbox[1]
    image_bottom = image_bbox[3]
    found_labels = []

    # Strategy 1: Check for labels WITHIN the image bounding box
    within_blocks = [
        block for block in text_blocks
        if block.y0 >= image_top and block.y0 <= image_bottom
    ]

    # Sort by vertical position (top to bottom)
    within_blocks.sort(key=lambda b: b.y0)

    # Look for ALL figure label patterns within image
    for block in within_blocks:
        lines = block.text.split('\n')
        for line in lines:
            line = line.strip()
            match = config.FIGURE_LABEL_PATTERN.match(line)
            if match:
                figure_number = match.group(1)
                normalized_label = figure_number.rstrip('.')
                logger.debug(f"Found figure label WITHIN image: {normalized_label} at y={block.y0:.1f}")
                found_labels.append((normalized_label, block))

    # Strategy 2: Check for labels BELOW the image
    below_blocks = [
        block for block in text_blocks
        if block.is_below(image_bottom, tolerance=config.VERTICAL_TOLERANCE)
    ]

    # Sort by vertical position (top to bottom)
    below_blocks.sort(key=lambda b: b.y0)

    # Find ALL blocks matching figure label pattern
    for block in below_blocks:
        lines = block.text.split('\n')
        for line in lines:
            line = line.strip()
            match = config.FIGURE_LABEL_PATTERN.match(line)
            if match:
                figure_number = match.group(1)
                normalized_label = figure_number.rstrip('.')
                logger.debug(f"Found figure label BELOW image: {normalized_label} at y={block.y0:.1f}")
                found_labels.append((normalized_label, block))

    if not found_labels:
        logger.debug(f"No figure labels found within or below image at {image_bbox}")

    return found_labels


# ============================================================
# CAPTION DETECTION
# ============================================================

def is_caption_stop_line(line: str) -> bool:
    """Check if a line indicates the caption has ended.

    Args:
        line: Text line to check

    Returns:
        True if line matches a stop pattern
    """
    line = line.strip()

    # Empty line is a cautious stop
    if not line:
        return True

    # Check against all stop patterns
    for pattern in config.CAPTION_STOP_PATTERNS:
        if pattern.match(line):
            return True

    return False


def find_figure_caption(
    label_block: TextBlock,
    text_blocks: List[TextBlock],
    max_lines: int = None
) -> Optional[str]:
    """Find caption text immediately below figure label.

    Algorithm:
    1. Filter blocks below label (block.y0 > label.y1)
    2. Capture next 1-3 non-blank lines
    3. Stop if Article/Section/Part/Figure pattern detected
    4. Join captured lines with space

    Args:
        label_block: TextBlock containing the figure label
        text_blocks: List of all TextBlock objects on the page
        max_lines: Maximum lines to capture (default from config)

    Returns:
        Caption text if found, None otherwise
    """
    if max_lines is None:
        max_lines = config.MAX_CAPTION_LINES

    label_bottom = label_block.y1

    # Filter blocks below the label
    below_blocks = [
        block for block in text_blocks
        if block.is_below(label_bottom, tolerance=config.VERTICAL_TOLERANCE)
    ]

    # Sort by vertical position
    below_blocks.sort(key=lambda b: b.y0)

    # Collect caption lines
    caption_lines = []
    lines_captured = 0

    for block in below_blocks:
        # Process each line in the block
        for line in block.text.split('\n'):
            line = line.strip()

            # Skip blank lines
            if not line:
                continue

            # Check if this is a stop line
            if is_caption_stop_line(line):
                # If we've already captured some lines, stop here
                if caption_lines:
                    break
                # Otherwise, skip this line and continue
                continue

            # Add line to caption
            caption_lines.append(line)
            lines_captured += 1

            # Check if we've reached max lines
            if lines_captured >= max_lines:
                break

        # Break outer loop if we stopped
        if lines_captured >= max_lines or (caption_lines and is_caption_stop_line(line)):
            break

    if not caption_lines:
        logger.debug("No caption found below label")
        return None

    # Join caption lines with space
    caption = " ".join(caption_lines)

    logger.debug(f"Found caption: {caption[:100]}...")

    return caption


# ============================================================
# IMAGE-METADATA ASSOCIATION
# ============================================================

def associate_image_with_metadata(
    image_bbox: Tuple[float, float, float, float],
    page_num: int,
    text_blocks: List[TextBlock],
    page_height: float
) -> Tuple[Optional[str], Optional[str]]:
    """Associate an image with its label and caption.

    Args:
        image_bbox: Image bounding box (x0, y0, x1, y1)
        page_num: Page number (0-indexed)
        text_blocks: List of TextBlock objects on the page
        page_height: Page height in points

    Returns:
        Tuple of (label, caption) - either may be None
    """
    # Find label
    label_result = find_figure_label(image_bbox, text_blocks, page_height)

    if not label_result:
        logger.warning(f"No label found for image at page {page_num}, bbox {image_bbox}")
        return (None, None)

    label, label_block = label_result

    # Find caption
    caption = find_figure_caption(label_block, text_blocks)

    if not caption:
        logger.warning(f"No caption found for figure {label} on page {page_num}")

    return (label, caption)


def filter_text_blocks_by_page(text_blocks_by_page: dict, page_num: int) -> List[TextBlock]:
    """Get text blocks for a specific page.

    Args:
        text_blocks_by_page: Dictionary mapping page numbers to text blocks
        page_num: Page number to retrieve

    Returns:
        List of TextBlock objects for that page
    """
    return text_blocks_by_page.get(page_num, [])


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def normalize_label(label: str) -> str:
    """Normalize a figure label for consistency.

    Args:
        label: Raw figure label

    Returns:
        Normalized label
    """
    # Remove "Figure" prefix if present
    label = label.strip()

    # Remove trailing dots
    label = label.rstrip('.')

    # Remove extra whitespace
    label = " ".join(label.split())

    return label


def validate_label_format(label: str) -> bool:
    """Validate that a label matches expected format.

    Args:
        label: Figure label to validate

    Returns:
        True if valid, False otherwise
    """
    if not label:
        return False

    # Should contain at least one digit
    if not any(c.isdigit() for c in label):
        return False

    # Should not be too long (sanity check)
    if len(label) > 50:
        return False

    return True
