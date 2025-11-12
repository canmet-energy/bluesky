"""Configuration for hybrid NECB PDF parser"""

from dataclasses import dataclass


@dataclass
class ParserConfig:
    """Hybrid parser configuration"""

    # Device settings
    use_gpu: bool = True

    # LLM settings
    llm_model: str = "llama3.1:8b"
    llm_temperature: float = 0.0  # Deterministic
    llm_timeout: int = 30  # seconds

    # Validation thresholds
    pymupdf_min_confidence: float = 0.8
    marker_fallback_enabled: bool = True

    # Performance tuning
    max_retries: int = 2
    cache_extractions: bool = True
    parallel_pages: bool = True

    # Debug options
    verbose: bool = False
    save_intermediate_results: bool = False
