"""
Interactive figure cropping tool for NECB extracted figures.

Uses matplotlib's RectangleSelector for interactive rectangle selection with preview
to crop figures that include extra page content (tables, text, etc.).

Usage:
    # Interactive mode - crop figures one by one with preview
    python -m bluesky.mcp.scrapers.necb.parsers.figures.crop_figures 2020

    # Batch mode - re-apply saved crop coordinates
    python -m bluesky.mcp.scrapers.necb.parsers.figures.crop_figures 2020 --batch

    # Skip already cropped figures
    python -m bluesky.mcp.scrapers.necb.parsers.figures.crop_figures 2020 --resume

Interactive Workflow:
    1. Click and drag to select crop region
    2. Press ENTER to preview the crop
    3. View side-by-side comparison:
       - Left: Original with red box showing crop region
       - Right: Cropped result
    4. Choose:
       - 'y' to accept the crop
       - 'r' to retry (select again)
       - 'n' to skip this figure
    5. Press ESC at any time to skip

The crop coordinates are saved to 'crop_coordinates.json' in the figures directory
for reproducibility and batch processing. Coordinates are auto-saved after each
successful crop.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

import click
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.widgets import RectangleSelector
from PIL import Image

from . import figure_config as config

logger = logging.getLogger(__name__)


# ============================================================
# CROP COORDINATES MANAGEMENT
# ============================================================

def get_crop_coords_path(vintage: str) -> Path:
    """Get path to crop coordinates JSON file.

    Args:
        vintage: NECB vintage year

    Returns:
        Path to crop_coordinates_{vintage}.json in parsers/figures/crop_coords/
    """
    return config.get_crop_coords_path(vintage)


def load_crop_coordinates(vintage: str) -> Dict[str, Dict[str, int]]:
    """Load saved crop coordinates from JSON.

    Args:
        vintage: NECB vintage year

    Returns:
        Dictionary mapping figure labels to crop coordinates
        Format: {"A-1.1.4.1.(1)": {"x": 50, "y": 100, "width": 800, "height": 600}}
    """
    coords_path = get_crop_coords_path(vintage)

    if not coords_path.exists():
        logger.info(f"No saved crop coordinates found at {coords_path}")
        return {}

    try:
        with open(coords_path, 'r') as f:
            coords = json.load(f)
        logger.info(f"Loaded {len(coords)} crop coordinates from {coords_path}")
        return coords
    except Exception as e:
        logger.error(f"Failed to load crop coordinates: {e}")
        return {}


def save_crop_coordinates(vintage: str, coords: Dict[str, Dict[str, int]]) -> None:
    """Save crop coordinates to JSON.

    Args:
        vintage: NECB vintage year
        coords: Dictionary mapping labels to crop coordinates
    """
    coords_path = get_crop_coords_path(vintage)
    coords_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(coords_path, 'w') as f:
            json.dump(coords, f, indent=2, sort_keys=True)
        logger.info(f"Saved {len(coords)} crop coordinates to {coords_path}")
        print(f"✓ Crop coordinates saved to: {coords_path}")
    except Exception as e:
        logger.error(f"Failed to save crop coordinates: {e}")
        print(f"✗ Failed to save crop coordinates: {e}")


# ============================================================
# IMAGE CROPPING
# ============================================================

def extract_label_from_filename(filename: str) -> str:
    """Extract figure label from filename.

    Args:
        filename: e.g., "Figure_A-1.1.4.1.1.png"

    Returns:
        Label: e.g., "A-1.1.4.1.(1)" or "A-1.1.4.1.1"
    """
    # Remove "Figure_" prefix and ".png" extension
    label = filename.replace("Figure_", "").replace(".png", "")
    return label


def interactive_crop(image_path: Path) -> Optional[Tuple[int, int, int, int]]:
    """Interactively select crop region using matplotlib with preview.

    Args:
        image_path: Path to image file

    Returns:
        Tuple of (x, y, width, height) or None if cancelled
    """
    # Load image with PIL
    try:
        img = Image.open(image_path)
    except Exception as e:
        logger.error(f"Failed to load image: {image_path}: {e}")
        return None

    # Convert to RGB if needed
    if img.mode != 'RGB':
        img = img.convert('RGB')

    # Get image dimensions
    w, h = img.size

    while True:  # Loop to allow retry
        # Show instructions
        print(f"\n{'='*70}")
        print(f"Cropping: {image_path.name}")
        print(f"Image size: {w}x{h} pixels")
        print(f"{'='*70}")
        print("Instructions:")
        print("  1. Click and drag to select crop region")
        print("  2. Press ENTER to preview the crop")
        print("  3. Confirm or retry in the preview window")
        print("  4. Press ESC to skip this figure")
        print(f"{'='*70}\n")

        # Create figure and axis
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        ax.imshow(img)
        ax.set_title(f"Select crop region - {image_path.name}", fontsize=12)
        ax.set_xlabel("Press ENTER to preview, ESC to skip")

        # Store the selected rectangle coordinates
        crop_coords = {'coords': None, 'preview': False, 'cancelled': False}

        def on_select(eclick, erelease):
            """Callback for rectangle selection."""
            # Get rectangle coordinates (in data coordinates)
            x1, y1 = int(eclick.xdata), int(eclick.ydata)
            x2, y2 = int(erelease.xdata), int(erelease.ydata)

            # Ensure x1 < x2 and y1 < y2
            x_min = min(x1, x2)
            x_max = max(x1, x2)
            y_min = min(y1, y2)
            y_max = max(y1, y2)

            # Calculate width and height
            width = x_max - x_min
            height = y_max - y_min

            # Store coordinates
            crop_coords['coords'] = (x_min, y_min, width, height)

            # Update title with coordinates
            ax.set_title(
                f"Selected region: x={x_min}, y={y_min}, w={width}, h={height}\n"
                f"Press ENTER to preview, ESC to skip",
                fontsize=10
            )
            fig.canvas.draw()

        def on_key(event):
            """Handle keyboard events."""
            if event.key == 'enter':
                # Show preview
                crop_coords['preview'] = True
                plt.close(fig)
            elif event.key == 'escape':
                # Cancel the selection
                crop_coords['cancelled'] = True
                plt.close(fig)

        # Create RectangleSelector
        selector = RectangleSelector(
            ax,
            on_select,
            useblit=True,
            button=[1],  # Left mouse button
            minspanx=5,
            minspany=5,
            spancoords='pixels',
            interactive=True
        )

        # Connect keyboard event handler
        fig.canvas.mpl_connect('key_press_event', on_key)

        # Show the plot
        plt.tight_layout()
        plt.show()

        # Check if user cancelled
        if crop_coords['cancelled']:
            print("✗ Crop cancelled - skipping this figure")
            return None

        # Check if preview requested
        if not crop_coords['preview'] or crop_coords['coords'] is None:
            print("✗ No crop region selected")
            return None

        # Show preview of cropped image
        x, y, w_crop, h_crop = crop_coords['coords']

        # Create cropped image
        left = x
        upper = y
        right = x + w_crop
        lower = y + h_crop
        cropped_img = img.crop((left, upper, right, lower))

        # Show preview
        print(f"\n{'='*70}")
        print(f"PREVIEW: Crop region x={x}, y={y}, width={w_crop}, height={h_crop}")
        print(f"Cropped size: {cropped_img.width}×{cropped_img.height} pixels")
        print(f"{'='*70}\n")

        fig_preview, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

        # Show original with rectangle
        ax1.imshow(img)
        rect = patches.Rectangle((x, y), w_crop, h_crop, linewidth=2,
                                 edgecolor='red', facecolor='none')
        ax1.add_patch(rect)
        ax1.set_title("Original (red box = crop region)", fontsize=12)

        # Show cropped result
        ax2.imshow(cropped_img)
        ax2.set_title(f"Cropped Result ({cropped_img.width}×{cropped_img.height})", fontsize=12)

        plt.suptitle("Close window to confirm or retry", fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.show()

        # Ask for confirmation
        print("\nOptions:")
        print("  y - Accept this crop")
        print("  r - Retry (select again)")
        print("  n - Skip this figure")

        response = input("\nYour choice (y/r/n): ").lower().strip()

        if response == 'y':
            print(f"✓ Crop accepted: x={x}, y={y}, width={w_crop}, height={h_crop}")
            return (x, y, w_crop, h_crop)
        elif response == 'r':
            print("↻ Retrying crop selection...")
            continue  # Loop back to selection
        else:
            print("✗ Crop cancelled - skipping this figure")
            return None


def apply_crop(image_path: Path, crop_coords: Tuple[int, int, int, int], output_path: Optional[Path] = None) -> bool:
    """Apply crop coordinates to an image.

    Args:
        image_path: Path to source image
        crop_coords: Tuple of (x, y, width, height)
        output_path: Path to save cropped image (default: overwrite source)

    Returns:
        True if successful, False otherwise
    """
    if output_path is None:
        output_path = image_path

    try:
        # Load image with PIL
        img = Image.open(image_path)

        # Extract crop coordinates
        x, y, w, h = crop_coords

        # PIL crop uses (left, upper, right, lower)
        left = x
        upper = y
        right = x + w
        lower = y + h

        # Crop image
        cropped = img.crop((left, upper, right, lower))

        # Save
        cropped.save(output_path)

        logger.info(f"Cropped {image_path.name} -> {output_path.name}")
        return True

    except Exception as e:
        logger.error(f"Failed to crop {image_path}: {e}")
        print(f"✗ Error cropping {image_path.name}: {e}")
        return False


# ============================================================
# BATCH PROCESSING
# ============================================================

def batch_crop_from_coordinates(vintage: str, overwrite: bool = True) -> int:
    """Apply saved crop coordinates to all figures.

    Args:
        vintage: NECB vintage year
        overwrite: Whether to overwrite original images

    Returns:
        Number of figures successfully cropped
    """
    # Load crop coordinates
    coords = load_crop_coordinates(vintage)

    if not coords:
        print("✗ No saved crop coordinates found!")
        return 0

    # Get all figure files
    figures_dir = config.FIGURE_OUTPUT_DIR / vintage
    if not figures_dir.exists():
        print(f"✗ Figures directory not found: {figures_dir}")
        return 0

    figure_files = sorted(figures_dir.glob("Figure_*.png"))

    if not figure_files:
        print(f"✗ No figure files found in {figures_dir}")
        return 0

    print(f"\nBatch cropping {len(coords)} figures from saved coordinates...")
    print(f"{'='*70}\n")

    success_count = 0

    for fig_path in figure_files:
        label = extract_label_from_filename(fig_path.name)

        # Check if we have crop coordinates for this figure
        if label not in coords:
            print(f"⊘ Skipping {fig_path.name} (no crop coordinates)")
            continue

        # Get crop coordinates
        crop_data = coords[label]
        crop_coords = (
            crop_data['x'],
            crop_data['y'],
            crop_data['width'],
            crop_data['height']
        )

        # Apply crop
        output_path = fig_path if overwrite else fig_path.with_stem(f"{fig_path.stem}_cropped")

        if apply_crop(fig_path, crop_coords, output_path):
            print(f"✓ Cropped {fig_path.name}")
            success_count += 1
        else:
            print(f"✗ Failed to crop {fig_path.name}")

    print(f"\n{'='*70}")
    print(f"Batch crop complete: {success_count}/{len(coords)} figures cropped successfully")
    print(f"{'='*70}\n")

    return success_count


# ============================================================
# INTERACTIVE CROPPING SESSION
# ============================================================

def interactive_crop_session(vintage: str, resume: bool = False) -> int:
    """Run interactive cropping session for all figures.

    Args:
        vintage: NECB vintage year
        resume: Whether to skip figures that already have crop coordinates

    Returns:
        Number of figures cropped
    """
    # Get all figure files
    figures_dir = config.FIGURE_OUTPUT_DIR / vintage
    if not figures_dir.exists():
        print(f"✗ Figures directory not found: {figures_dir}")
        return 0

    figure_files = sorted(figures_dir.glob("Figure_*.png"))

    if not figure_files:
        print(f"✗ No figure files found in {figures_dir}")
        return 0

    # Load existing crop coordinates
    coords = load_crop_coordinates(vintage) if resume else {}

    print(f"\n{'='*70}")
    print(f"Interactive cropping session - NECB {vintage}")
    print(f"Total figures: {len(figure_files)}")
    if resume:
        already_cropped = sum(1 for f in figure_files if extract_label_from_filename(f.name) in coords)
        print(f"Already cropped: {already_cropped}")
        print(f"Remaining: {len(figure_files) - already_cropped}")
    print(f"{'='*70}\n")

    crop_count = 0
    new_coords = coords.copy()

    for idx, fig_path in enumerate(figure_files, 1):
        label = extract_label_from_filename(fig_path.name)

        # Skip if resuming and already have coordinates
        if resume and label in coords:
            print(f"[{idx}/{len(figure_files)}] ⊘ Skipping {fig_path.name} (already cropped)")
            continue

        print(f"\n[{idx}/{len(figure_files)}] Processing: {fig_path.name}")

        # Interactive crop selection
        crop_coords = interactive_crop(fig_path)

        if crop_coords is None:
            # User cancelled - ask if they want to quit or skip
            response = input("\nSkip this figure and continue? (y/n/q for quit): ").lower().strip()
            if response == 'q':
                print("\n✗ Cropping session cancelled by user")
                break
            elif response == 'n':
                # Try again
                crop_coords = interactive_crop(fig_path)
                if crop_coords is None:
                    continue
            else:
                # Skip
                continue

        # Apply crop
        if apply_crop(fig_path, crop_coords):
            print(f"✓ Successfully cropped {fig_path.name}")

            # Save coordinates
            x, y, w, h = crop_coords
            new_coords[label] = {
                'x': x,
                'y': y,
                'width': w,
                'height': h
            }

            crop_count += 1

            # Auto-save coordinates after each successful crop
            save_crop_coordinates(vintage, new_coords)
        else:
            print(f"✗ Failed to apply crop to {fig_path.name}")

    print(f"\n{'='*70}")
    print(f"Cropping session complete!")
    print(f"Figures cropped: {crop_count}")
    print(f"{'='*70}\n")

    return crop_count


# ============================================================
# CLI INTERFACE
# ============================================================

@click.command()
@click.argument("vintage", type=click.Choice(["2011", "2015", "2017", "2020"]))
@click.option(
    "--batch",
    is_flag=True,
    help="Batch mode: re-apply saved crop coordinates to all figures",
    show_default=True
)
@click.option(
    "--resume",
    is_flag=True,
    help="Resume mode: skip figures that already have crop coordinates",
    show_default=True
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
    show_default=True
)
def main(vintage: str, batch: bool, resume: bool, verbose: bool):
    """Interactive figure cropping tool for NECB figures with preview.

    VINTAGE: NECB vintage year (2011, 2015, 2017, 2020)

    Interactive mode workflow:
        1. Select crop region with click and drag
        2. Press ENTER to preview the crop
        3. View side-by-side comparison (original + cropped)
        4. Confirm (y), retry (r), or skip (n)

    Examples:
        # Interactive cropping session with preview
        python -m bluesky.mcp.scrapers.necb.parsers.figures.crop_figures 2020

        # Resume cropping (skip already cropped figures)
        python -m bluesky.mcp.scrapers.necb.parsers.figures.crop_figures 2020 --resume

        # Batch re-apply saved crop coordinates
        python -m bluesky.mcp.scrapers.necb.parsers.figures.crop_figures 2020 --batch
    """
    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger.info(f"Starting figure cropping for NECB {vintage}")
    logger.info(f"Figures directory: {config.FIGURE_OUTPUT_DIR / vintage}")

    try:
        if batch:
            # Batch mode - apply saved coordinates
            count = batch_crop_from_coordinates(vintage, overwrite=True)

            if count > 0:
                click.echo(f"\n✅ Successfully cropped {count} figures!")
                return 0
            else:
                click.echo("\n❌ No figures were cropped", err=True)
                return 1
        else:
            # Interactive mode
            count = interactive_crop_session(vintage, resume=resume)

            if count > 0:
                click.echo(f"\n✅ Successfully cropped {count} figures!")
                return 0
            else:
                click.echo("\n⚠️  No figures were cropped")
                return 0

    except KeyboardInterrupt:
        logger.info("Cropping interrupted by user")
        click.echo("\n\n⚠️  Cropping session interrupted by user")
        return 130
    except Exception as e:
        logger.exception("Fatal error during cropping")
        click.echo(f"\n❌ Fatal error: {e}", err=True)
        return 1


if __name__ == "__main__":
    main()
