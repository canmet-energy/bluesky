"""
Equation extractor for NECB PDFs using LLM vision or OCR fallback.

NECB PDFs contain mathematical equations rendered as vector graphics (paths),
which PyMuPDF's get_text() cannot extract. This module:
1. Detects gaps in text flow that likely contain equations
2. Uses LLM vision (Claude) for accurate equation extraction, or OCR as fallback
3. Returns equation text to be inserted into the extracted content

Extraction Methods (in order of preference):
1. LLM Vision (Claude) - Most accurate, requires ANTHROPIC_API_KEY
2. OCR (tesseract) - Fallback, less accurate for mathematical notation
"""

import io
import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

import fitz
from PIL import Image

logger = logging.getLogger(__name__)

# Check for LLM vision availability (preferred)
LLM_VISION_AVAILABLE = bool(os.getenv("ANTHROPIC_API_KEY"))

# Try to import pytesseract as fallback
try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

if not LLM_VISION_AVAILABLE and not PYTESSERACT_AVAILABLE:
    logger.warning("Neither LLM vision nor pytesseract available - equation extraction disabled")


# LLM Vision prompt for equation extraction (base template)
# Note: Double braces {{ }} are used to escape literal braces for .format()
EQUATION_EXTRACTION_PROMPT_BASE = """Extract the mathematical equation shown in this image.

CRITICAL: Pay close attention to EXPONENTS and SUPERSCRIPTS. Building code equations often
contain polynomial terms like x^{{2}}, x^{{3}}, or ratios raised to powers. Small superscript
numbers are easy to miss but are mathematically essential.

{context_section}

Rules:
1. Output ONLY the equation itself in LaTeX notation, nothing else
2. Use LaTeX math notation:
   - Subscripts: use underscore with braces (e.g., t_{{adjusted}}, V_{{partload}})
   - SUPERSCRIPTS/EXPONENTS: use caret with braces (e.g., x^{{2}}, (V/V_{{rated}})^{{2}})
   - Look carefully for small superscript numbers like ², ³ - they indicate powers
   - Polynomial terms often appear as: A + Bx + Cx^{{2}} or similar patterns
   - Multiplication: use \\times for cross, or implicit multiplication
   - Division: use \\frac{{numerator}}{{denominator}}
   - Greek letters: use LaTeX commands (e.g., \\tau, \\gamma, \\alpha)
   - Summation: \\sum_{{i=1}}^{{n}}
   - Special symbols: \\leq, \\geq, \\neq, \\approx
3. If there are multiple equations or conditions, use cases environment:
   \\begin{{cases}} condition1 & \\text{{if }} x < D \\\\ condition2 & \\text{{if }} x \\geq D \\end{{cases}}
4. For polynomial expressions, verify the power of each term:
   - Linear term (power 1): Bx or B \\times x
   - Quadratic term (power 2): Cx^{{2}} or C \\times x^{{2}}
   - Cubic term (power 3): Dx^{{3}} or D \\times x^{{3}}
5. If no equation is visible, respond with "NO_EQUATION"

Example outputs:
- t_{{adjusted}} = t_{{base}} \\times \\frac{{d_{{operation}}}}{{250}}
- P = P_{{rated}} \\times \\left[A + B \\times \\left(\\frac{{V}}{{V_{{rated}}}}\\right) + C \\times \\left(\\frac{{V}}{{V_{{rated}}}}\\right)^{{2}}\\right]
- U_s = \\frac{{t_e - t_o}}{{t_2 - 0.5 t_i - 0.5 t_o}} \\times U_i
- f_{{obst,i}} = \\begin{{cases}} \\cos(1.5 \\times \\gamma_{{obst,i}}) & \\text{{if }} \\gamma_{{obst,i}} < 60° \\\\ 0 & \\text{{if }} \\gamma_{{obst,i}} \\geq 60° \\end{{cases}}
"""

# Legacy prompt for backwards compatibility (no context)
EQUATION_EXTRACTION_PROMPT = EQUATION_EXTRACTION_PROMPT_BASE.format(context_section="")


def build_equation_prompt(context_before: str = "", context_after: str = "") -> str:
    """Build the equation extraction prompt with optional context.

    The surrounding sentence text helps the LLM understand:
    - What variables mean (e.g., "P = power", "V = flow rate")
    - The physical meaning of the equation
    - Units and expected relationships

    Args:
        context_before: Text before the equation (e.g., "Pump power, P, versus flow rate, V, shall be calculated using:")
        context_after: Text after the equation (e.g., "where P_rated = rated pump power...")

    Returns:
        Complete prompt with context section filled in
    """
    if context_before or context_after:
        context_lines = ["CONTEXT from surrounding text (use this to understand variable meanings):"]
        if context_before:
            # Truncate to reasonable length
            before_text = context_before[-200:] if len(context_before) > 200 else context_before
            context_lines.append(f"  Before equation: \"{before_text}\"")
        if context_after:
            # Truncate to reasonable length, focus on the "where" definitions
            after_text = context_after[:300] if len(context_after) > 300 else context_after
            context_lines.append(f"  After equation: \"{after_text}\"")
        context_section = "\n".join(context_lines)
    else:
        context_section = ""

    return EQUATION_EXTRACTION_PROMPT_BASE.format(context_section=context_section)


@dataclass
class EquationRegion:
    """Represents a detected equation region on a page."""
    page_num: int
    y_start: float  # Top of gap (after "equation:" or similar)
    y_end: float    # Bottom of gap (before "where" or similar)
    context_before: str  # Text before the gap
    context_after: str   # Text after the gap
    extracted_text: Optional[str] = None
    method: str = "none"  # "llm", "ocr", or "none"
    target_article: Optional[str] = None  # Target article for disambiguation (from known missing list)


@dataclass
class TextBlock:
    """A block of text with its vertical position."""
    y_pos: float
    text: str


def detect_equation_gaps(page: fitz.Page, min_gap: float = 30.0) -> list[tuple[float, float, str, str]]:
    """Detect vertical gaps in text that likely contain equations.

    Args:
        page: PyMuPDF page object
        min_gap: Minimum vertical gap size (in points) to consider as equation

    Returns:
        List of (y_start, y_end, context_before, context_after) tuples
    """
    blocks = page.get_text('dict')['blocks']

    # Copyright watermark patterns to filter out
    # These appear as large text blocks spanning the page
    copyright_patterns = [
        'copyright',
        '© nrc',
        '© cnrc',
        'world rights reserved',
        'droits réservés',
    ]

    # Collect all text lines with their y positions
    text_lines: list[TextBlock] = []

    for block in blocks:
        if block['type'] != 0:  # Skip non-text blocks
            continue

        # Check if this block is a copyright watermark by examining its text
        block_text = ''
        for line in block.get('lines', []):
            for span in line.get('spans', []):
                block_text += span.get('text', '')

        block_lower = block_text.lower()
        is_copyright = any(pattern in block_lower for pattern in copyright_patterns)

        if is_copyright:
            # Skip copyright watermark blocks entirely
            continue

        for line in block.get('lines', []):
            line_text = ''
            y_pos = line['bbox'][1]  # Top of line

            for span in line.get('spans', []):
                line_text += span.get('text', '')

            if line_text.strip():
                text_lines.append(TextBlock(y_pos=y_pos, text=line_text.strip()))

    # Sort by vertical position
    text_lines.sort(key=lambda x: x.y_pos)

    # Find gaps that follow equation indicators
    # Primary indicators (high confidence - always indicate equation follows)
    primary_indicators = [
        'equation:',
        'equations:',
        'equation.',
        'following equation',
        'following equations',
        'as follows:',           # Common in 3.2.1.4 (FDWR equations)
        'shall be as follows',   # NECB pattern
    ]

    # Secondary indicators (medium confidence - need gap or "where" to confirm)
    secondary_indicators = [
        'calculated using',
        'determined using',
        'shall be calculated',
        'shall be determined',
        'adjusted using',        # For 8.4.2.10 (Air Leakage Rate Adjustment)
        'shall be adjusted',     # NECB pattern
        'can be determined',     # Notes section pattern (Division A)
        'can be calculated',     # Notes section pattern (Division A)
    ]

    where_indicators = [
        'where',
        'Where',
        'in which',
        'and where',
    ]

    gaps: list[tuple[float, float, str, str]] = []

    for i, line in enumerate(text_lines[:-1]):
        next_line = text_lines[i + 1]
        gap_size = next_line.y_pos - line.y_pos

        line_lower = line.text.lower()

        # Check for primary indicators (high confidence)
        has_primary_indicator = any(
            indicator in line_lower
            for indicator in primary_indicators
        )

        # Check for secondary indicators (need more context)
        has_secondary_indicator = any(
            indicator in line_lower
            for indicator in secondary_indicators
        )

        # Check if next line starts with "where" (variable definitions)
        next_is_where = any(
            next_line.text.lower().startswith(indicator.lower())
            for indicator in where_indicators
        )

        # Detection logic:
        # 1. Primary indicator + significant gap → equation (don't require "where")
        # 2. Secondary indicator + gap + "where" → equation (lower threshold when "where" present)
        # 3. Any indicator + large gap (>50pt) → equation (page boundary cases)
        should_detect = False

        # Use lower threshold for secondary indicators with "where" confirmation
        # This helps catch compact equations that have less whitespace
        effective_min_gap = min_gap
        if has_secondary_indicator and next_is_where:
            effective_min_gap = 25.0  # Lower threshold when we have strong context

        if gap_size > effective_min_gap:
            if has_primary_indicator:
                # Primary indicators like "equation:" always indicate an equation
                should_detect = True
            elif has_secondary_indicator and next_is_where:
                # Secondary indicators need "where" confirmation
                should_detect = True
            elif (has_primary_indicator or has_secondary_indicator) and gap_size > 50:
                # Large gaps with any indicator (handles page boundary cases)
                should_detect = True

        if should_detect:
            gaps.append((
                line.y_pos + 15,  # Start just below the indicator line
                next_line.y_pos - 5,  # End just above next line
                line.text,
                next_line.text
            ))
            indicator_type = "primary" if has_primary_indicator else "secondary"
            where_status = "with-where" if next_is_where else "no-where"
            logger.debug(
                f"Detected equation gap: y={line.y_pos:.0f}-{next_line.y_pos:.0f}, "
                f"gap={gap_size:.0f}pt, {indicator_type}, {where_status}, "
                f"after='{line.text[:40]}...'"
            )

    return gaps


def render_region_to_image(page: fitz.Page, y_start: float, y_end: float,
                           x_margin: float = 50, zoom: float = 3.0) -> bytes:
    """Render a specific region of the page to a PNG image.

    Args:
        page: PyMuPDF page object
        y_start: Top of region (in points)
        y_end: Bottom of region (in points)
        x_margin: Left/right margin to exclude (in points)
        zoom: Zoom factor for rendering

    Returns:
        PNG image data as bytes
    """
    rect = page.rect

    # Create clip rectangle for the equation region
    clip = fitz.Rect(
        x_margin,
        y_start,
        rect.width - x_margin,
        y_end
    )

    # Render the clipped region at high resolution
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, clip=clip)

    return pix.tobytes('png')


def extract_equation_with_llm(
    image_data: bytes,
    context_before: str = "",
    context_after: str = ""
) -> str:
    """Extract equation from image using LLM vision.

    Args:
        image_data: PNG image bytes
        context_before: Text before the equation (helps LLM understand variable meanings)
        context_after: Text after the equation (often contains "where" variable definitions)

    Returns:
        Extracted equation text
    """
    if not LLM_VISION_AVAILABLE:
        return ""

    try:
        from bluesky.necb.build.tables.llm_backends import ClaudeBackend

        # Build prompt with context if available
        prompt = build_equation_prompt(context_before, context_after)

        backend = ClaudeBackend(model="claude-haiku-4-5", verbose=False)
        result = backend.generate_with_image(
            prompt=prompt,
            image_data=image_data,
            media_type="image/png",
            temperature=0.0,
            max_tokens=256
        )

        # Check for "no equation" response
        if "NO_EQUATION" in result.upper():
            return ""

        # Clean up the result
        result = result.strip()

        # Remove any markdown formatting
        result = re.sub(r'^```.*\n?', '', result)
        result = re.sub(r'\n?```$', '', result)

        return result.strip()

    except Exception as e:
        logger.warning(f"LLM equation extraction failed: {e}")
        return ""


def extract_equation_with_ocr(image_data: bytes) -> str:
    """Extract equation from image using OCR (fallback).

    Args:
        image_data: PNG image bytes

    Returns:
        Extracted equation text
    """
    if not PYTESSERACT_AVAILABLE:
        return ""

    try:
        img = Image.open(io.BytesIO(image_data))
        text = pytesseract.image_to_string(img, config='--psm 6')

        # Clean up OCR result
        return clean_ocr_text(text)

    except Exception as e:
        logger.warning(f"OCR equation extraction failed: {e}")
        return ""


def clean_ocr_text(text: str) -> str:
    """Clean up OCR'd equation text.

    Args:
        text: Raw OCR output

    Returns:
        Cleaned equation text
    """
    lines = text.split('\n')
    cleaned_lines = []

    noise_patterns = [
        r'copyright',
        r'©',
        r'rights reserved',
        r'national energy code',
        r'division [a-d]',
        r'^\s*\d+-\d+\s*$',  # Page numbers like "4-36"
    ]

    for line in lines:
        line = line.strip()
        if not line:
            continue

        is_noise = any(
            re.search(pattern, line, re.IGNORECASE)
            for pattern in noise_patterns
        )

        if not is_noise:
            cleaned_lines.append(line)

    result = ' '.join(cleaned_lines)

    # Normalize spacing
    result = re.sub(r'\s*=\s*', ' = ', result)
    result = re.sub(r'\s+', ' ', result)

    return result.strip()


def extract_equation_from_region(
    page: fitz.Page,
    y_start: float,
    y_end: float,
    use_llm: bool = True,
    context_before: str = "",
    context_after: str = ""
) -> tuple[str, str]:
    """Extract equation from a page region.

    Args:
        page: PyMuPDF page object
        y_start: Top of region
        y_end: Bottom of region
        use_llm: Whether to try LLM first
        context_before: Text before the equation (helps LLM understand variables)
        context_after: Text after the equation (often contains "where" definitions)

    Returns:
        Tuple of (equation_text, method_used)
    """
    # Render region to image
    image_data = render_region_to_image(page, y_start, y_end)

    # Try LLM first if enabled and available
    if use_llm and LLM_VISION_AVAILABLE:
        result = extract_equation_with_llm(image_data, context_before, context_after)
        if result:
            return result, "llm"

    # Fall back to OCR
    if PYTESSERACT_AVAILABLE:
        result = extract_equation_with_ocr(image_data)
        if result:
            return result, "ocr"

    return "", "none"


def extract_equations_from_page(doc: fitz.Document, page_num: int,
                                 use_llm: bool = True) -> list[EquationRegion]:
    """Extract all equations from a single page.

    Args:
        doc: PyMuPDF document
        page_num: 0-indexed page number
        use_llm: Whether to use LLM vision (True) or OCR only (False)

    Returns:
        List of EquationRegion objects with extracted text
    """
    page = doc[page_num]
    gaps = detect_equation_gaps(page)

    equations = []
    for y_start, y_end, context_before, context_after in gaps:
        # Pass context to LLM to help it understand variable meanings
        extracted_text, method = extract_equation_from_region(
            page, y_start, y_end,
            use_llm=use_llm,
            context_before=context_before,
            context_after=context_after
        )

        if extracted_text:
            equations.append(EquationRegion(
                page_num=page_num,
                y_start=y_start,
                y_end=y_end,
                context_before=context_before,
                context_after=context_after,
                extracted_text=extracted_text,
                method=method
            ))

            logger.info(
                f"Extracted equation on page {page_num + 1} via {method}: "
                f"'{extracted_text[:60]}...'" if len(extracted_text) > 60 else f"'{extracted_text}'"
            )

    return equations


def insert_equations_into_text(text: str, equations: list[EquationRegion]) -> str:
    """Insert extracted equations into text at appropriate positions.

    Uses the context_after (the "where" line and variable definitions) to match
    equations to their correct locations. This is more reliable than context_before
    because the variable definitions are unique to each equation.

    Args:
        text: Original extracted text
        equations: List of extracted equations

    Returns:
        Text with equations inserted
    """
    if not equations:
        return text

    for eq in equations:
        if not eq.extracted_text:
            continue

        # Extract the first variable definition from context_after to use as anchor
        # This is more unique than the "following equation:" pattern
        # e.g., "where\ntadjusted = adjusted operational time"
        after_lines = eq.context_after.split('\n') if '\n' in eq.context_after else [eq.context_after]
        first_line_after = after_lines[0].strip()

        # Build a pattern that matches the equation indicator followed by newlines,
        # then specifically "where" followed by the unique variable definition pattern
        # Use the context_before to find the right location
        context_pattern = re.escape(eq.context_before[-40:]) if len(eq.context_before) > 40 else re.escape(eq.context_before)

        # Pattern: context (ending with equation indicator), newlines, then "where"
        # We'll insert the equation between the indicator and "where"
        pattern = rf'({context_pattern}[^\n]*)\n+(\s*where\b)'

        # First, check if this pattern exists and how many times
        matches = list(re.finditer(pattern, text, flags=re.IGNORECASE))

        if len(matches) == 0:
            logger.debug(f"No match for equation context: '{eq.context_before[-30:]}'")
            continue
        elif len(matches) == 1:
            # Unique match - safe to insert
            def make_replacement(equation_text):
                def replacement(match):
                    before = match.group(1)
                    after = match.group(2)
                    return f"{before}\n\n[Equation: {equation_text}]\n\n{after}"
                return replacement

            text = re.sub(pattern, make_replacement(eq.extracted_text), text, count=1, flags=re.IGNORECASE)
            logger.debug(f"Inserted equation: '{eq.extracted_text[:40]}...'")
        else:
            # Multiple matches - need to use more context to disambiguate
            # Primary disambiguation: use target_article if provided
            # Secondary disambiguation: check which "where" block contains variables
            logger.debug(f"Multiple matches ({len(matches)}) for context, attempting disambiguation")

            best_match = None
            best_score = 0

            # Primary disambiguation: If we have a target article, find the match nearest that article
            if eq.target_article:
                logger.debug(f"Using target article '{eq.target_article}' for primary disambiguation")
                for match in matches:
                    # Look backwards from match position for article number
                    lookback_start = max(0, match.start() - 2000)
                    preceding_text = text[lookback_start:match.start()]

                    # Find all article numbers in preceding text
                    article_matches = list(re.finditer(r'\b(\d+\.\d+\.\d+\.\d+)\b', preceding_text))

                    if article_matches:
                        # Get the closest article number (last one in the preceding text)
                        closest_article = article_matches[-1].group(1)
                        if closest_article == eq.target_article:
                            best_match = match
                            best_score = 100  # High score for exact article match
                            logger.debug(f"Found exact article match for '{eq.target_article}'")
                            break

            # Secondary disambiguation: variable matching (if no target article or no exact match)
            if not best_match or best_score == 0:
                # Extract variable names from the equation
                # Handle both plain text (t_adjusted) and LaTeX notation (t_{adjusted})
                eq_vars = set()
                # Plain text subscripts: t_adjusted, C_DL,sup,i
                eq_vars.update(re.findall(r'\b([a-zA-Z]+_[a-zA-Z0-9,]+)\b', eq.extracted_text))
                # LaTeX subscripts: t_{adjusted}, C_{DL,sup,i} - extract the base variable
                latex_vars = re.findall(r'([a-zA-Z]+)_\{([^}]+)\}', eq.extracted_text)
                for base, subscript in latex_vars:
                    # Add combined form (e.g., "tadjusted", "CDL")
                    eq_vars.add(f"{base}_{subscript.replace(',', '').replace(' ', '')}")
                    eq_vars.add(base + subscript.replace(',', '').replace(' ', '').replace('{', '').replace('}', ''))

                # Greek letter mappings for matching
                greek_to_latin = {
                    'α': 'alpha', 'β': 'beta', 'γ': 'gamma', 'δ': 'delta',
                    'ε': 'epsilon', 'ζ': 'zeta', 'η': 'eta', 'θ': 'theta',
                    'ι': 'iota', 'κ': 'kappa', 'λ': 'lambda', 'μ': 'mu',
                    'ν': 'nu', 'ξ': 'xi', 'π': 'pi', 'ρ': 'rho',
                    'σ': 'sigma', 'τ': 'tau', 'υ': 'upsilon', 'φ': 'phi',
                    'χ': 'chi', 'ψ': 'psi', 'ω': 'omega',
                }

                def normalize_greek(s: str) -> str:
                    """Convert Greek letters to Latin spellings for matching."""
                    result = s.lower()
                    for greek, latin in greek_to_latin.items():
                        result = result.replace(greek, latin)
                    return result

                for match in matches:
                    # Get text after this match (the "where" clause definitions)
                    match_end = match.end()
                    following_text = text[match_end:match_end + 500]  # Next 500 chars
                    following_normalized = normalize_greek(following_text)

                    # Normalize equation for comparison
                    eq_normalized = normalize_greek(eq.extracted_text)

                    # Count how many equation variables appear in the following text
                    score = sum(1 for var in eq_vars if var.lower() in following_normalized)

                    # Also check for variables without underscores (gamma_obs -> gammaobs, gamma)
                    simple_vars = set(re.findall(r'\b([a-zA-Z]{2,})\b', eq_normalized.replace('_', '')))
                    score += sum(0.5 for var in simple_vars if var.lower() in following_normalized)

                    if score > best_score:
                        best_score = score
                        best_match = match

            # Fallback: if we have target_article but no match yet, use the first match
            # that appears after the target article in the text
            if not best_match and eq.target_article:
                logger.debug(f"Using fallback: first match after target article '{eq.target_article}'")
                target_pos = text.find(eq.target_article)
                if target_pos >= 0:
                    for match in matches:
                        if match.start() > target_pos:
                            best_match = match
                            best_score = 1  # Low score but valid
                            logger.debug(f"Fallback: using first match after article at pos {target_pos}")
                            break

            if best_match and best_score > 0:
                # Insert at the best match location
                before_text = text[:best_match.start()]
                match_text = text[best_match.start():best_match.end()]
                after_text = text[best_match.end():]

                # Reconstruct with equation inserted
                before_part = match_text[:match_text.rfind('\n') + 1] if '\n' in match_text else match_text
                after_part = "where" if "where" in match_text.lower() else match_text.split()[-1]

                # Find where "where" starts in the match
                where_idx = match_text.lower().rfind('where')
                if where_idx >= 0:
                    before_part = match_text[:where_idx].rstrip()
                    after_part = match_text[where_idx:]
                    new_match = f"{before_part}\n\n[Equation: {eq.extracted_text}]\n\n{after_part}"
                    text = before_text + new_match + after_text
                    logger.debug(f"Disambiguated and inserted equation (score={best_score}): '{eq.extracted_text[:40]}...'")
            else:
                logger.warning(f"Could not disambiguate equation location, skipping: '{eq.extracted_text[:40]}...'")

    return text


def enhance_extraction_with_equations(
    doc: fitz.Document,
    text: str,
    page_range: tuple[int, int] | None = None,
    use_llm: bool = True
) -> str:
    """Enhance extracted text by detecting and extracting equations.

    Args:
        doc: PyMuPDF document
        text: Already extracted text
        page_range: Optional (start, end) page range to process
        use_llm: Whether to use LLM vision (True) or OCR only (False)

    Returns:
        Enhanced text with equations inserted
    """
    if not LLM_VISION_AVAILABLE and not PYTESSERACT_AVAILABLE:
        logger.warning("No equation extraction method available")
        return text

    method = "LLM vision" if (use_llm and LLM_VISION_AVAILABLE) else "OCR"
    logger.info(f"Extracting equations using {method}...")

    start_page = page_range[0] if page_range else 0
    end_page = page_range[1] if page_range else doc.page_count

    all_equations = []

    for page_num in range(start_page, end_page):
        try:
            equations = extract_equations_from_page(doc, page_num, use_llm=use_llm)
            all_equations.extend(equations)
        except Exception as e:
            logger.warning(f"Failed to extract equations from page {page_num + 1}: {e}")

    if all_equations:
        llm_count = sum(1 for eq in all_equations if eq.method == "llm")
        ocr_count = sum(1 for eq in all_equations if eq.method == "ocr")
        logger.info(f"Extracted {len(all_equations)} equations (LLM: {llm_count}, OCR: {ocr_count})")
        text = insert_equations_into_text(text, all_equations)

    return text


# Alias for backwards compatibility
enhance_extraction_with_ocr = enhance_extraction_with_equations


# Known missing equations in NECB 2020 that require targeted extraction
# These are equations that may not be detected by the standard gap detection
# due to different phrasing patterns or compact layouts
# Format: (page_num, article_number, description)
KNOWN_MISSING_EQUATIONS_2020 = [
    (72, "3.2.1.4", "Allowable Fenestration and Door Area (FDWR equations)"),
    (141, "5.2.3.4", "Demand Control Ventilation Systems"),
    (191, "6.2.4.1", "Temperature Controls (MRT equation in Notes)"),
    (207, "8.4.2.10", "Air Leakage Rate Adjustment"),
    (221, "8.4.4.17", "Fans - Piecewise fan power equation"),  # Page 221 (1-indexed), contains 8.4.4.17
    (234, "8.4.5.9", "Fuel-Fired Service Water Heater (2 equations)"),
]


def extract_equations_from_targeted_pages(
    doc: fitz.Document,
    vintage: str = "2020",
    use_llm: bool = True
) -> list[EquationRegion]:
    """Extract equations from known missing pages using targeted detection.

    This function uses more aggressive gap detection (lower threshold)
    for specific pages that are known to contain equations that may be
    missed by the standard detection.

    Args:
        doc: PyMuPDF document
        vintage: NECB vintage (currently only 2020 supported)
        use_llm: Whether to use LLM vision for extraction

    Returns:
        List of EquationRegion objects with extracted equations
    """
    if vintage != "2020":
        logger.info(f"Targeted equation extraction only supported for 2020, got {vintage}")
        return []

    if not LLM_VISION_AVAILABLE and not PYTESSERACT_AVAILABLE:
        logger.warning("No equation extraction method available")
        return []

    all_equations = []

    for page_num, article_num, description in KNOWN_MISSING_EQUATIONS_2020:
        if page_num > len(doc):
            logger.warning(f"Page {page_num} out of range for document")
            continue

        page = doc[page_num - 1]  # 0-indexed

        # Use lower gap threshold for targeted pages (25pt instead of 30pt)
        gaps = detect_equation_gaps(page, min_gap=25.0)

        if gaps:
            logger.info(f"Found {len(gaps)} potential equation(s) on page {page_num} ({article_num}: {description})")

            for y_start, y_end, context_before, context_after in gaps:
                extracted_text, method = extract_equation_from_region(
                    page, y_start, y_end,
                    use_llm=use_llm,
                    context_before=context_before,
                    context_after=context_after
                )

                if extracted_text:
                    all_equations.append(EquationRegion(
                        page_num=page_num - 1,  # Convert to 0-indexed
                        y_start=y_start,
                        y_end=y_end,
                        context_before=context_before,
                        context_after=context_after,
                        extracted_text=extracted_text,
                        method=method,
                        target_article=article_num  # Pass target article for disambiguation
                    ))
                    logger.info(
                        f"Extracted targeted equation on page {page_num} ({article_num}): "
                        f"'{extracted_text[:60]}...'" if len(extracted_text) > 60 else f"'{extracted_text}'"
                    )
        else:
            logger.debug(f"No equation gaps detected on targeted page {page_num} ({article_num})")

    return all_equations
