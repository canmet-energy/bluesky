"""
NECB Query Understanding with Entity Extraction

Converts natural language queries to structured NECB queries using entity extraction.

Example conversions:
    "What's the max window area for a 3-story office in Calgary?"
    → location: Calgary (Zone 7A, ~5000 HDD)
    → building_type: office
    → concept: window area → FDWR (fenestration-door-wall ratio)
    → expanded_query: "FDWR fenestration door wall ratio office Calgary Zone 7A"

Entity types:
- location: City/province → Climate zone + HDD
- building_type: office, retail, school, etc. → NECB building classifications
- concept: window area → FDWR, thermal resistance → RSI/U-value, etc.
- vintage: 2011, 2015, 2017, 2020

Concept mapping:
- window area, glass area, glazing → FDWR, fenestration
- thermal resistance, insulation, R-value → RSI, U-value, thermal transmittance
- lighting, illumination → lighting power density, LPD
- HVAC, heating, cooling → system types, equipment efficiency
"""

import logging
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# Canadian Climate Zone Mapping
# Source: NECB 2020, Appendix C
CLIMATE_ZONES = {
    # Alberta
    "calgary": {"zone": "7A", "hdd": 5000, "province": "AB"},
    "edmonton": {"zone": "7B", "hdd": 5120, "province": "AB"},
    "red deer": {"zone": "7B", "hdd": 5500, "province": "AB"},
    "lethbridge": {"zone": "6", "hdd": 4700, "province": "AB"},
    "grande prairie": {"zone": "8", "hdd": 5900, "province": "AB"},
    # British Columbia
    "vancouver": {"zone": "4", "hdd": 3000, "province": "BC"},
    "victoria": {"zone": "4", "hdd": 2700, "province": "BC"},
    "kelowna": {"zone": "5", "hdd": 3500, "province": "BC"},
    "prince george": {"zone": "7B", "hdd": 5400, "province": "BC"},
    "fort st. john": {"zone": "8", "hdd": 6200, "province": "BC"},
    # Ontario
    "toronto": {"zone": "5", "hdd": 3900, "province": "ON"},
    "ottawa": {"zone": "6", "hdd": 4500, "province": "ON"},
    "windsor": {"zone": "5", "hdd": 3400, "province": "ON"},
    "thunder bay": {"zone": "7A", "hdd": 5500, "province": "ON"},
    "sudbury": {"zone": "6", "hdd": 4900, "province": "ON"},
    # Quebec
    "montreal": {"zone": "6", "hdd": 4400, "province": "QC"},
    "quebec city": {"zone": "6", "hdd": 4900, "province": "QC"},
    "sherbrooke": {"zone": "6", "hdd": 4700, "province": "QC"},
    "trois-rivieres": {"zone": "6", "hdd": 4800, "province": "QC"},
    # Atlantic
    "halifax": {"zone": "6", "hdd": 4200, "province": "NS"},
    "st. john's": {"zone": "6", "hdd": 4800, "province": "NL"},
    "fredericton": {"zone": "6", "hdd": 4500, "province": "NB"},
    "charlottetown": {"zone": "6", "hdd": 4400, "province": "PE"},
    # Prairies
    "winnipeg": {"zone": "7A", "hdd": 5700, "province": "MB"},
    "regina": {"zone": "7A", "hdd": 5600, "province": "SK"},
    "saskatoon": {"zone": "7B", "hdd": 6000, "province": "SK"},
    # Territories
    "whitehorse": {"zone": "8", "hdd": 6580, "province": "YT"},
    "yellowknife": {"zone": "8", "hdd": 8300, "province": "NT"},
    "iqaluit": {"zone": "8", "hdd": 11000, "province": "NU"},
}


# NECB Concept Mapping
CONCEPT_SYNONYMS = {
    # Fenestration / Windows
    "window": ["fenestration", "glazing", "glass", "FDWR", "window-to-wall ratio"],
    "window area": ["fenestration area", "glazing area", "FDWR", "fenestration-door-wall ratio"],
    "glass": ["glazing", "fenestration", "transparent elements"],
    # Thermal properties
    "insulation": ["thermal resistance", "RSI", "R-value", "thermal transmittance", "U-value"],
    "r-value": ["RSI", "thermal resistance", "insulation value"],
    "u-value": ["thermal transmittance", "heat transfer coefficient"],
    "thermal": ["heat transfer", "insulation", "envelope performance"],
    # Building envelope
    "wall": ["above-grade wall", "exterior wall", "building envelope"],
    "roof": ["ceiling", "attic", "building envelope"],
    "floor": ["slab", "below-grade", "building envelope"],
    # Lighting
    "lighting": ["lighting power density", "LPD", "illumination", "luminaire"],
    "light": ["lighting power", "LPD", "luminaire"],
    # HVAC
    "hvac": ["heating", "cooling", "ventilation", "mechanical systems"],
    "heating": ["furnace", "boiler", "heat pump", "thermal equipment"],
    "cooling": ["chiller", "air conditioning", "cooling equipment"],
    "ventilation": ["fresh air", "outdoor air", "air changes"],
}


# NECB Building Type Mapping
BUILDING_TYPES = {
    "office": ["office building", "commercial office", "workspace"],
    "retail": ["store", "shop", "commercial retail", "mercantile"],
    "school": ["educational", "classroom", "university", "college"],
    "warehouse": ["storage", "distribution", "industrial"],
    "hotel": ["motel", "lodging", "accommodation", "hospitality"],
    "restaurant": ["food service", "dining", "cafeteria"],
    "hospital": ["healthcare", "medical", "clinic"],
    "apartment": ["residential", "multi-unit residential", "MURB"],
    "assembly": ["auditorium", "theatre", "arena", "convention center"],
}


@dataclass
class ExtractedEntities:
    """Structured entities extracted from natural language query."""

    # Original query
    original_query: str

    # Extracted entities
    location: Optional[str] = None  # "Calgary"
    climate_zone: Optional[str] = None  # "7A"
    hdd: Optional[int] = None  # 5000
    building_type: Optional[str] = None  # "office"
    concepts: List[str] = field(default_factory=list)  # ["FDWR", "fenestration"]
    vintage: Optional[str] = None  # "2020"

    # Query expansion
    expanded_terms: List[str] = field(default_factory=list)
    necb_keywords: List[str] = field(default_factory=list)

    # Confidence
    confidence: float = 1.0  # 0-1 confidence in extraction


class NECBQueryUnderstanding:
    """Extract entities and expand natural language NECB queries."""

    def __init__(self):
        """Initialize query understanding engine."""
        self.climate_zones = CLIMATE_ZONES
        self.concept_synonyms = CONCEPT_SYNONYMS
        self.building_types = BUILDING_TYPES

    def understand_query(self, query: str) -> ExtractedEntities:
        """
        Extract entities from natural language query.

        Args:
            query: Natural language query (e.g., "max window area for office in Calgary")

        Returns:
            ExtractedEntities with location, building type, concepts, expanded terms
        """
        query_lower = query.lower()

        entities = ExtractedEntities(original_query=query)

        # Extract location and climate zone
        location_info = self._extract_location(query_lower)
        if location_info:
            entities.location = location_info["city"]
            entities.climate_zone = location_info["zone"]
            entities.hdd = location_info["hdd"]

        # Extract building type
        building_type = self._extract_building_type(query_lower)
        if building_type:
            entities.building_type = building_type

        # Extract concepts and expand
        concepts, expanded = self._extract_concepts(query_lower)
        entities.concepts = concepts
        entities.expanded_terms = expanded

        # Extract vintage
        vintage = self._extract_vintage(query_lower)
        if vintage:
            entities.vintage = vintage

        # Generate NECB keywords for search
        entities.necb_keywords = self._generate_necb_keywords(entities)

        # Calculate confidence
        entities.confidence = self._calculate_confidence(entities)

        logger.info(
            f"Query understanding: {len(entities.concepts)} concepts, "
            f"{len(entities.expanded_terms)} expanded terms, "
            f"confidence={entities.confidence:.2f}"
        )

        return entities

    def _extract_location(self, query: str) -> Optional[Dict]:
        """Extract Canadian city and map to climate zone."""
        for city, info in self.climate_zones.items():
            # Match city name (case insensitive, handle variations)
            if city in query or city.replace(" ", "") in query.replace(" ", ""):
                return {
                    "city": city.title(),
                    "zone": info["zone"],
                    "hdd": info["hdd"],
                    "province": info["province"],
                }
        return None

    def _extract_building_type(self, query: str) -> Optional[str]:
        """Extract building type."""
        for building_type, synonyms in self.building_types.items():
            if building_type in query:
                return building_type
            for synonym in synonyms:
                if synonym in query:
                    return building_type
        return None

    def _extract_concepts(self, query: str) -> Tuple[List[str], List[str]]:
        """
        Extract NECB concepts and expand with synonyms.

        Returns:
            Tuple of (concepts, expanded_terms)
        """
        concepts = []
        expanded = []

        # Check each concept
        for base_concept, synonyms in self.concept_synonyms.items():
            # Check if base concept in query
            if base_concept in query:
                concepts.append(base_concept)
                expanded.extend(synonyms)

            # Check if any synonym in query
            for synonym in synonyms:
                if synonym.lower() in query:
                    if base_concept not in concepts:
                        concepts.append(base_concept)
                    expanded.extend([s for s in synonyms if s not in expanded])

        # Deduplicate expanded terms
        expanded = list(set(expanded))

        return concepts, expanded

    def _extract_vintage(self, query: str) -> Optional[str]:
        """Extract NECB vintage year."""
        # Match NECB 2011, 2015, 2017, 2020
        vintage_patterns = [
            r"necb\s*(2011|2015|2017|2020)",
            r"\b(2011|2015|2017|2020)\b",
        ]

        for pattern in vintage_patterns:
            match = re.search(pattern, query)
            if match:
                year = match.group(1)
                if year in ["2011", "2015", "2017", "2020"]:
                    return year

        return None

    def _generate_necb_keywords(self, entities: ExtractedEntities) -> List[str]:
        """Generate NECB-specific keywords for enhanced search."""
        keywords = []

        # Add location keywords
        if entities.climate_zone:
            keywords.append(f"Zone {entities.climate_zone}")
            keywords.append(f"Climate Zone {entities.climate_zone}")

        if entities.hdd:
            # Add HDD range keywords
            hdd_range = self._get_hdd_range(entities.hdd)
            keywords.append(hdd_range)

        # Add building type keywords
        if entities.building_type:
            keywords.append(entities.building_type)
            if entities.building_type in self.building_types:
                keywords.extend(self.building_types[entities.building_type])

        # Add concept keywords
        keywords.extend(entities.concepts)
        keywords.extend(entities.expanded_terms)

        return list(set(keywords))  # Deduplicate

    def _get_hdd_range(self, hdd: int) -> str:
        """Map HDD to NECB table range."""
        # NECB tables use HDD ranges like "< 3000", "3000 to 3999", "4000 to 4999", etc.
        if hdd < 3000:
            return "< 3000"
        elif hdd < 4000:
            return "3000 to 3999"
        elif hdd < 5000:
            return "4000 to 4999"
        elif hdd < 6000:
            return "5000 to 5999"
        elif hdd < 7000:
            return "6000 to 6999"
        else:
            return "≥ 7000"

    def _calculate_confidence(self, entities: ExtractedEntities) -> float:
        """Calculate confidence in entity extraction."""
        score = 0.0
        total_weight = 0.0

        # Location extracted (weight: 0.3)
        if entities.location:
            score += 0.3
        total_weight += 0.3

        # Building type extracted (weight: 0.2)
        if entities.building_type:
            score += 0.2
        total_weight += 0.2

        # Concepts extracted (weight: 0.4)
        if entities.concepts:
            # Score based on number of concepts (max 3)
            concept_score = min(len(entities.concepts) / 3.0, 1.0) * 0.4
            score += concept_score
        total_weight += 0.4

        # Vintage extracted (weight: 0.1)
        if entities.vintage:
            score += 0.1
        total_weight += 0.1

        # Normalize to 0-1
        confidence = score / total_weight if total_weight > 0 else 0.5

        return confidence

    def expand_query(self, query: str, entities: Optional[ExtractedEntities] = None) -> str:
        """
        Expand query with NECB terms and extracted entities.

        Args:
            query: Original query
            entities: Pre-extracted entities (optional)

        Returns:
            Expanded query string with NECB keywords
        """
        if entities is None:
            entities = self.understand_query(query)

        # Build expanded query
        parts = [query]  # Start with original

        # Add NECB keywords
        if entities.necb_keywords:
            parts.extend(entities.necb_keywords)

        # Join and deduplicate words
        expanded = " ".join(parts)

        return expanded


def main():
    """CLI for testing query understanding."""
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Test queries
    test_queries = [
        "What's the max window area for a 3-story office in Calgary?",
        "Thermal transmittance for walls in cold climate",
        "Lighting power density for school classrooms in Toronto",
        "HVAC system requirements for warehouse in Edmonton NECB 2020",
        "R-value requirements for roofs in Vancouver",
        "Maximum FDWR for office building in climate zone 7A",
    ]

    engine = NECBQueryUnderstanding()

    print("=" * 80)
    print("NECB Query Understanding Test")
    print("=" * 80)

    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: {query}")
        print("-" * 80)

        entities = engine.understand_query(query)

        print(f"Location: {entities.location} (Zone {entities.climate_zone}, {entities.hdd} HDD)")
        print(f"Building Type: {entities.building_type}")
        print(f"Concepts: {', '.join(entities.concepts) if entities.concepts else 'None'}")
        print(f"Vintage: {entities.vintage or 'Not specified (default: 2020)'}")
        print(f"Confidence: {entities.confidence:.2%}")

        print(f"\nNECB Keywords ({len(entities.necb_keywords)}):")
        for keyword in entities.necb_keywords[:10]:  # Show first 10
            print(f"  - {keyword}")

        expanded = engine.expand_query(query, entities)
        print(f"\nExpanded Query:")
        print(f"  {expanded[:200]}..." if len(expanded) > 200 else f"  {expanded}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
