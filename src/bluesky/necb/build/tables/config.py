"""Configuration for hybrid NECB PDF parser"""

from dataclasses import dataclass, field


# Tables that benefit from Marker's advanced layout analysis
# These tables have complex formatting (merged cells, formulas, multi-line content)
MARKER_PREFERRED_TABLES = [
    '6.2.2.1',    # SWH Equipment - 8×18 with complex formulas and notes
    '8.4.4.13',   # Heat pump system descriptions - complex multi-line descriptions
    '8.4.4.14',   # Pump power coefficients - dense numeric table
    'A-8.4.3.2.(1)',  # Climate zone data - 31×25 monster table spanning 11 pages
]


@dataclass
class ParserConfig:
    """Hybrid parser configuration"""

    # Device settings
    use_gpu: bool = True

    # LLM settings
    llm_backend: str = "claude"  # "ollama" (local) or "claude" (API)
    llm_model: str = "qwen2.5:14b-instruct"  # Ollama: "qwen2.5:14b-instruct", "llama3.1:8b"
                                              # Claude: "claude-haiku-4-5", "claude-3-5-sonnet-20241022"
    llm_temperature: float = 0.0  # Deterministic
    llm_timeout: int = 30  # seconds
    llm_api_key: str | None = None  # API key for Claude (uses ANTHROPIC_API_KEY env var if None)

    # Validation thresholds
    pymupdf_min_confidence: float = 0.8
    marker_fallback_enabled: bool = True
    marker_for_tables: list[str] = field(default_factory=lambda: MARKER_PREFERRED_TABLES.copy())

    # Table-specific model overrides
    # Phase 8+9: Chunked extraction makes operating schedules simple enough for Haiku
    # No overrides needed - all tables use base llm_model
    table_specific_models: dict[str, str] = field(default_factory=dict)

    # Performance tuning
    max_retries: int = 2
    cache_extractions: bool = True
    parallel_pages: bool = True

    # Debug options
    verbose: bool = False
    save_intermediate_results: bool = False
