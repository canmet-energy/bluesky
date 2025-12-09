"""LLM backend abstraction - supports Ollama (local) and Anthropic Claude (API)

Usage:
    # Ollama (local, free)
    backend = create_llm_backend("ollama", model="qwen2.5:14b-instruct")

    # Claude (API, paid)
    backend = create_llm_backend("claude", model="claude-sonnet-4-5-20250929")
"""

from abc import ABC, abstractmethod
from typing import Any


class LLMBackend(ABC):
    """Abstract base class for LLM backends"""

    @abstractmethod
    def generate(self, prompt: str, temperature: float = 0.0, timeout: int = 30, model: str | None = None) -> str:
        """
        Generate completion from LLM

        Args:
            prompt: Input prompt
            temperature: Sampling temperature (0.0 = deterministic)
            timeout: Request timeout in seconds
            model: Optional model override (uses default if None)

        Returns:
            Generated text

        Raises:
            Exception: If generation fails
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name being used"""
        pass


class OllamaBackend(LLMBackend):
    """Ollama backend for local LLM inference"""

    def __init__(self, model: str = "qwen2.5:14b-instruct", verbose: bool = False):
        """
        Initialize Ollama backend

        Args:
            model: Ollama model name (e.g., "qwen2.5:14b-instruct", "llama3.1:8b")
            verbose: Enable verbose logging
        """
        from ollama import Client

        self.client = Client()
        self.model = model
        self.verbose = verbose

        if self.verbose:
            print(f"Ollama backend initialized: {model}")

    def generate(self, prompt: str, temperature: float = 0.0, timeout: int = 30, model: str | None = None, max_tokens: int | None = None) -> str:
        """Generate completion using Ollama

        Note: max_tokens parameter is not used by Ollama (no token limit)
        """
        response = self.client.generate(
            model=model if model else self.model,  # Use override or default
            prompt=prompt,
            options={
                "temperature": temperature,
                "timeout": timeout,
            },
        )
        return response["response"]

    def get_model_name(self) -> str:
        return f"ollama:{self.model}"


class ClaudeBackend(LLMBackend):
    """Anthropic Claude backend for API-based inference"""

    def __init__(
        self,
        model: str = "claude-haiku-4-5",
        api_key: str | None = None,
        verbose: bool = False,
    ):
        """
        Initialize Claude backend

        Args:
            model: Claude model ID
                   - "claude-haiku-4-5" (recommended - fastest, cheapest, Oct 2025)
                   - "claude-3-5-sonnet-20241022" (more powerful, slower, Oct 2024)
                   - "claude-3-5-haiku-20241022" (legacy Claude 3.5, Oct 2024)
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if None)
            verbose: Enable verbose logging
        """
        import anthropic
        import os

        self.model = model
        self.verbose = verbose

        # Get API key from parameter or environment
        if api_key is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key is None:
                raise ValueError(
                    "ANTHROPIC_API_KEY environment variable not set. "
                    "Get your API key from: https://console.anthropic.com/"
                )

        self.client = anthropic.Anthropic(api_key=api_key)

        if self.verbose:
            print(f"Claude backend initialized: {model}")

    def generate(self, prompt: str, temperature: float = 0.0, timeout: int = 30, model: str | None = None, max_tokens: int | None = None) -> str:
        """
        Generate completion using Claude

        Note: timeout parameter is ignored (Claude SDK uses default timeout)
        """
        # Use override or default model
        active_model = model if model else self.model

        # Use custom max_tokens or default
        tokens = max_tokens if max_tokens else 4096

        # Claude uses messages API, convert prompt to message
        response = self.client.messages.create(
            model=active_model,
            max_tokens=tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text from response
        if not response.content or len(response.content) == 0:
            raise ValueError("Claude returned empty response")

        return response.content[0].text

    def generate_with_image(
        self,
        prompt: str,
        image_data: bytes,
        media_type: str = "image/png",
        temperature: float = 0.0,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """
        Generate completion using Claude with an image input (vision).

        Args:
            prompt: Text prompt describing what to extract from the image
            image_data: Raw image bytes (PNG, JPEG, GIF, or WebP)
            media_type: MIME type of the image (default: "image/png")
            temperature: Sampling temperature (0.0 = deterministic)
            model: Optional model override
            max_tokens: Maximum tokens in response

        Returns:
            Generated text response
        """
        import base64

        # Use override or default model
        active_model = model if model else self.model

        # Use custom max_tokens or default
        tokens = max_tokens if max_tokens else 1024

        # Encode image as base64
        image_base64 = base64.standard_b64encode(image_data).decode("utf-8")

        # Build message with image
        response = self.client.messages.create(
            model=active_model,
            max_tokens=tokens,
            temperature=temperature,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_base64,
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

        # Extract text from response
        if not response.content or len(response.content) == 0:
            raise ValueError("Claude returned empty response")

        return response.content[0].text

    def get_model_name(self) -> str:
        return f"claude:{self.model}"


def create_llm_backend(
    backend_type: str,
    model: str | None = None,
    api_key: str | None = None,
    verbose: bool = False,
) -> LLMBackend:
    """
    Factory function to create LLM backend

    Args:
        backend_type: "ollama" or "claude"
        model: Model name (uses defaults if None)
               - Ollama default: "qwen2.5:14b-instruct"
               - Claude default: "claude-sonnet-4-5-20250929"
        api_key: API key (Claude only, uses ANTHROPIC_API_KEY env var if None)
        verbose: Enable verbose logging

    Returns:
        LLMBackend instance

    Examples:
        >>> # Ollama (local, free)
        >>> backend = create_llm_backend("ollama")
        >>> backend = create_llm_backend("ollama", model="llama3.1:8b")

        >>> # Claude (API, paid)
        >>> backend = create_llm_backend("claude")
        >>> backend = create_llm_backend("claude", model="claude-haiku-3-5-20241022")

    Raises:
        ValueError: If backend_type is not recognized
    """
    if backend_type.lower() == "ollama":
        default_model = "qwen2.5:14b-instruct"
        return OllamaBackend(model=model or default_model, verbose=verbose)

    elif backend_type.lower() == "claude":
        default_model = "claude-haiku-4-5"
        return ClaudeBackend(model=model or default_model, api_key=api_key, verbose=verbose)

    else:
        raise ValueError(
            f"Unknown backend type: {backend_type}. "
            f"Supported backends: 'ollama', 'claude'"
        )
