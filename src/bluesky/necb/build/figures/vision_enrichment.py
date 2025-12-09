"""
Vision-based figure description enrichment using Claude Vision API.

Generates detailed technical descriptions of figures using multimodal LLMs.
"""

import base64
import logging
import time
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass

from anthropic import Anthropic

from .cache import FigureCacheManager, create_figure_cache_entry
from .figure_models import Figure

logger = logging.getLogger(__name__)


@dataclass
class VisionEnrichmentConfig:
    """Configuration for vision enrichment."""

    model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 1024
    temperature: float = 0.0
    rate_limit_delay: float = 0.5  # seconds between API calls


@dataclass
class EnrichmentResult:
    """Result of vision enrichment for a single figure."""

    figure_label: str
    original_caption: Optional[str]
    ai_description: Optional[str]
    success: bool
    error: Optional[str] = None
    tokens_used: Optional[int] = None
    duration: Optional[float] = None


class VisionEnricher:
    """Enrich figures with AI-generated descriptions using Claude Vision."""

    def __init__(
        self,
        config: Optional[VisionEnrichmentConfig] = None,
        api_key: Optional[str] = None,
        db_path: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        section_cache_dir: Optional[Path] = None,
        use_cache: bool = True,
    ):
        """
        Initialize vision enricher.

        Args:
            config: Vision enrichment configuration
            api_key: Anthropic API key (if None, uses ANTHROPIC_API_KEY env var)
            db_path: Path to database (for fetching figure images)
            cache_dir: Directory for caching Vision API outputs
            section_cache_dir: Directory containing section cache files (JSON) for article context
            use_cache: Whether to use cached outputs when available (default: True)
        """
        self.config = config or VisionEnrichmentConfig()
        self.db_path = db_path
        self.section_cache_dir = section_cache_dir
        self.use_cache = use_cache

        # Initialize cache manager
        self.cache = None
        if cache_dir:
            self.cache = FigureCacheManager(cache_dir, verbose=True)

        try:
            self.client = Anthropic(api_key=api_key) if api_key else Anthropic()
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            raise

    def enrich_figure(
        self,
        figure: Figure,
        image_path: Optional[Path] = None,
        image_data_bytes: Optional[bytes] = None,
        vintage: Optional[str] = None
    ) -> EnrichmentResult:
        """
        Generate detailed description for a single figure.

        Args:
            figure: Figure object with metadata
            image_path: Path to the figure image file (optional if image_data_bytes provided)
            image_data_bytes: Raw PNG bytes from database (optional if image_path provided)
            vintage: NECB vintage (for section context lookup)

        Returns:
            EnrichmentResult with AI-generated description
        """
        start_time = time.time()

        # Check cache first (if enabled)
        if self.cache and self.use_cache and vintage:
            cached = self.cache.load(vintage, figure.label)
            if cached and cached.success:
                logger.info(f"✅ Cache hit for {vintage}/{figure.label}")
                return EnrichmentResult(
                    figure_label=figure.label,
                    original_caption=cached.caption,
                    ai_description=cached.ai_description,
                    success=True,
                    tokens_used=cached.tokens_used,
                    duration=cached.duration_s,
                )

        try:
            # Get image data from database BLOB or filesystem
            if image_data_bytes:
                # Use image data from database
                image_data = base64.standard_b64encode(image_data_bytes).decode("utf-8")
            elif image_path and image_path.exists():
                # Fall back to reading from filesystem
                with open(image_path, "rb") as f:
                    image_data = base64.standard_b64encode(f.read()).decode("utf-8")
            else:
                return EnrichmentResult(
                    figure_label=figure.label,
                    original_caption=figure.caption,
                    ai_description=None,
                    success=False,
                    error=f"No image data provided (path={image_path})",
                )

            # Determine media type (always PNG for database-stored images)
            media_type = "image/png"

            # Build prompt (with section context if available)
            prompt = self._build_prompt(figure, vintage=vintage)

            # Call Claude Vision API
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            },
                        ],
                    }
                ],
            )

            # Extract description
            ai_description = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

            duration = time.time() - start_time

            logger.info(
                f"✅ Enriched {figure.label}: {tokens_used} tokens, {duration:.2f}s"
            )

            # Save to cache (if enabled)
            if self.cache and vintage and ai_description:
                cache_entry = create_figure_cache_entry(
                    vintage=vintage,
                    figure_label=figure.label,
                    ai_description=ai_description,
                    caption=figure.caption or "",
                    page_number=figure.page,
                    llm_model=self.config.model,
                    tokens_used=tokens_used,
                    duration_s=duration,
                    success=True,
                )
                self.cache.save(cache_entry)

            return EnrichmentResult(
                figure_label=figure.label,
                original_caption=figure.caption,
                ai_description=ai_description,
                success=True,
                tokens_used=tokens_used,
                duration=duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Failed to enrich {figure.label}: {e}")

            return EnrichmentResult(
                figure_label=figure.label,
                original_caption=figure.caption,
                ai_description=None,
                success=False,
                error=str(e),
                duration=duration,
            )

    def enrich_figures(
        self,
        figures: List[Figure],
        figure_output_dir: Path,
        vintage: str,
    ) -> List[EnrichmentResult]:
        """
        Enrich multiple figures with AI descriptions.

        Reads image data from database BLOBs instead of filesystem.

        Args:
            figures: List of Figure objects
            figure_output_dir: Base directory containing figure images (unused, kept for compatibility)
            vintage: NECB vintage (for subdirectory path)

        Returns:
            List of EnrichmentResult objects
        """
        import sqlite3

        results = []

        logger.info(f"Enriching {len(figures)} figures for NECB {vintage}")

        # Connect to database to fetch image data
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for i, figure in enumerate(figures, 1):
            logger.info(f"[{i}/{len(figures)}] Processing {figure.label}")

            # Fetch image data from database
            cursor.execute(
                "SELECT image_data FROM necb_figures WHERE vintage = ? AND label = ? LIMIT 1",
                (vintage, figure.label)
            )
            row = cursor.fetchone()

            if row and row[0]:
                # Use image data from database BLOB
                image_data_bytes = row[0]
                result = self.enrich_figure(
                    figure,
                    image_data_bytes=image_data_bytes,
                    vintage=vintage
                )
            else:
                # No image data found in database
                result = EnrichmentResult(
                    figure_label=figure.label,
                    original_caption=figure.caption,
                    ai_description=None,
                    success=False,
                    error=f"No image data in database for {vintage} - {figure.label}",
                )

            results.append(result)

            # Rate limiting
            if i < len(figures):
                time.sleep(self.config.rate_limit_delay)

        conn.close()

        # Summary
        success_count = sum(1 for r in results if r.success)
        total_tokens = sum(r.tokens_used for r in results if r.tokens_used)
        total_duration = sum(r.duration for r in results if r.duration)

        logger.info(
            f"\n✅ Vision enrichment complete: {success_count}/{len(figures)} successful, "
            f"{total_tokens:,} tokens, {total_duration:.1f}s"
        )

        return results

    def _find_section_context(self, figure: Figure, vintage: str) -> Optional[str]:
        """
        Find section text that references this figure from cache files.

        Reads from JSON cache files instead of database for better build-time
        independence. Cache files are in: {section_cache_dir}/sections/{vintage}/{division}/{article}.json

        Args:
            figure: Figure object
            vintage: NECB vintage

        Returns:
            Section text if found, None otherwise
        """
        if not self.section_cache_dir:
            return None

        try:
            import json
            import re

            # Extract article number from figure label
            # e.g., "Figure A-8.4.4.17.(2)" -> article_number="8.4.4.17", division="A"
            label = figure.label.replace("Figure ", "").strip()

            # Check for division prefix (A-, B-, C-, D-)
            division = None
            if label.startswith(("A-", "B-", "C-", "D-")):
                division = label[0]
                label = label[2:]

            # Extract article number (e.g., "8.4.4.17" from "8.4.4.17.(2)")
            article_match = re.match(r'(\d+\.\d+\.\d+\.\d+)', label)
            if not article_match:
                return None

            article_number = article_match.group(1)

            # Try to find cache file
            cache_path = None
            sections_dir = self.section_cache_dir / "sections" / vintage

            if division:
                # Try known division first
                cache_path = sections_dir / division / f"{article_number}.json"
                if not cache_path.exists():
                    cache_path = None

            if not cache_path:
                # Search all divisions
                for div in ["A", "B", "C", "D"]:
                    candidate = sections_dir / div / f"{article_number}.json"
                    if candidate.exists():
                        cache_path = candidate
                        break

            if not cache_path or not cache_path.exists():
                logger.debug(f"No cache file found for {article_number} in {vintage}")
                return None

            # Read cache file
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            title = data.get("title", "")
            full_text = data.get("full_text", "")

            if not full_text:
                return None

            # Truncate full_text if too long (limit to ~500 words)
            words = full_text.split()
            if len(words) > 500:
                full_text = " ".join(words[:500]) + "..."

            return f"Article {article_number}: {title}\n\n{full_text}"

        except Exception as e:
            logger.warning(f"Failed to find section context for {figure.label}: {e}")
            return None

    def _build_prompt(self, figure: Figure, vintage: Optional[str] = None) -> str:
        """
        Build prompt for vision model based on figure metadata.

        Args:
            figure: Figure object with metadata
            vintage: NECB vintage (for section context lookup)

        Returns:
            Prompt string for vision model
        """
        prompt_parts = [
            "This is a technical diagram from the National Energy Code of Canada for Buildings (NECB).",
            f"Figure number: {figure.label}",
        ]

        if figure.caption:
            prompt_parts.append(f"Original caption: \"{figure.caption}\"")

        # Add section context if available
        if vintage:
            section_context = self._find_section_context(figure, vintage)
            if section_context:
                prompt_parts.extend([
                    "",
                    "Related section text from the code:",
                    "---",
                    section_context,
                    "---",
                ])

        prompt_parts.extend([
            "",
            "Provide a detailed technical description of this diagram that includes:",
            "1. What type of diagram is it (flowchart, schematic, detail drawing, etc.)?",
            "2. What building components or systems are shown?",
            "3. All visible labels, measurements, and annotations",
            "4. The relationships and connections between elements",
            "5. Any compliance requirements or technical specifications visible",
            "",
            "Focus on technical accuracy and completeness. This description will be used for semantic search by engineers and code officials.",
        ])

        return "\n".join(prompt_parts)

    @staticmethod
    def _sanitize_filename(label: str) -> str:
        """Sanitize figure label for use as filename."""
        # Remove/replace problematic characters
        # Keep dots (.) for consistency with manually cropped filenames
        sanitized = label.replace("(", "").replace(")", "")
        sanitized = sanitized.replace("/", "_").replace("\\", "_")
        sanitized = sanitized.strip("_")
        return sanitized


def save_enrichment_to_database(
    enrichment_results: List[EnrichmentResult],
    vintage: str,
    db_path: Path,
) -> int:
    """
    Save vision enrichment results to database.

    Updates necb_figures table with AI-generated descriptions.

    Args:
        enrichment_results: List of enrichment results
        vintage: NECB vintage
        db_path: Path to database file

    Returns:
        Number of figures updated
    """
    import sqlite3

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if ai_description column exists, add if not
    cursor.execute("PRAGMA table_info(necb_figures)")
    columns = {row[1] for row in cursor.fetchall()}

    if "ai_description" not in columns:
        logger.info("Adding ai_description column to necb_figures table")
        cursor.execute("""
            ALTER TABLE necb_figures
            ADD COLUMN ai_description TEXT
        """)
        conn.commit()

    # Update figures with AI descriptions
    updated_count = 0

    for result in enrichment_results:
        if result.success and result.ai_description:
            cursor.execute(
                """
                UPDATE necb_figures
                SET ai_description = ?
                WHERE vintage = ? AND label = ?
                """,
                (result.ai_description, vintage, result.figure_label),
            )

            if cursor.rowcount > 0:
                updated_count += 1

    conn.commit()
    conn.close()

    logger.info(f"✅ Updated {updated_count} figures in database with AI descriptions")

    return updated_count


def save_descriptions_to_markdown(
    enrichment_results: List[EnrichmentResult],
    figure_output_dir: Path,
    vintage: str,
) -> int:
    """
    Save AI figure descriptions as markdown files for QA review.

    Creates .md files with:
    - Figure label and original caption
    - AI-generated description
    - Metadata (tokens used, timestamp)

    Args:
        enrichment_results: List of enrichment results
        figure_output_dir: Directory containing figure images
        vintage: NECB vintage

    Returns:
        Number of markdown files saved
    """
    import re
    from datetime import datetime

    saved_count = 0
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for result in enrichment_results:
        if not result.success or not result.ai_description:
            continue

        # Sanitize filename
        safe_label = re.sub(r'[^\w\s\-\.]', '_', result.figure_label)
        md_path = figure_output_dir / f"{safe_label}.md"

        # Build markdown content
        md_content = f"# {result.figure_label}\n\n"

        if result.original_caption:
            md_content += f"**Original Caption**: {result.original_caption}\n\n"

        md_content += "## AI Description\n\n"
        md_content += f"{result.ai_description}\n\n"

        md_content += "---\n"
        md_content += f"*Generated: {timestamp}*  \n"
        if result.tokens_used:
            md_content += f"*Tokens used: {result.tokens_used:,}*  \n"
        md_content += f"*Model: claude-sonnet-4-5-20250929*  \n"
        md_content += f"*Vintage: NECB {vintage}*\n"

        # Write markdown file
        try:
            md_path.write_text(md_content, encoding="utf-8")
            saved_count += 1
            logger.debug(f"Saved markdown: {md_path.name}")
        except Exception as e:
            logger.warning(f"Failed to save markdown for {result.figure_label}: {e}")

    logger.info(f"✅ Exported {saved_count} figure descriptions to markdown")

    return saved_count
