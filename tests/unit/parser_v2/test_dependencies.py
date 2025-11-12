"""Test that all parser v2 dependencies are working"""

import pytest


def test_pymupdf4llm_import():
    """Test PyMuPDF4LLM can be imported"""
    import pymupdf4llm

    assert pymupdf4llm is not None


def test_marker_import():
    """Test Marker can be imported"""
    from marker.converters.pdf import PdfConverter

    assert PdfConverter is not None


def test_ollama_import():
    """Test Ollama Python client can be imported"""
    import ollama

    assert ollama is not None


def test_pydantic_import():
    """Test Pydantic can be imported"""
    from pydantic import BaseModel

    assert BaseModel is not None


def test_torch_available():
    """Test PyTorch is available (for GPU acceleration)"""
    import torch

    assert torch is not None
    # Check if CUDA is available (optional)
    cuda_available = torch.cuda.is_available()
    print(f"CUDA available: {cuda_available}")


@pytest.mark.integration
def test_ollama_connection():
    """Test Ollama server connection"""
    import ollama

    try:
        # List available models
        models = ollama.list()
        assert models is not None
        print(f"Available models: {[m['name'] for m in models.get('models', [])]}")
    except Exception as e:
        pytest.skip(f"Ollama server not running: {e}")
