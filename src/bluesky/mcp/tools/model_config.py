"""
Model Configuration for NECB Semantic Search

Auto-detects GPU availability and selects optimal embedding model:
- GPU available: intfloat/e5-large-v2 (best accuracy, 1024 dims)
- CPU only: sentence-transformers/all-MiniLM-L6-v2 (fast, 384 dims)
"""

import logging
from typing import Tuple
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


def get_optimal_embedding_model() -> Tuple[SentenceTransformer, dict]:
    """
    Auto-detect GPU and select best embedding model.

    Returns:
        Tuple of (model, config_info):
            - model: Loaded SentenceTransformer ready for inference
            - config_info: Dict with device, model_name, dimensions

    Examples:
        >>> model, config = get_optimal_embedding_model()
        >>> config
        {
            'device': 'cuda',
            'model_name': 'intfloat/e5-large-v2',
            'dimensions': 1024,
            'gpu_name': 'NVIDIA RTX A2000'
        }
    """
    try:
        import torch

        if torch.cuda.is_available():
            # GPU detected - use high-accuracy model
            device = "cuda"
            model_name = "intfloat/e5-large-v2"
            dimensions = 1024
            gpu_name = torch.cuda.get_device_name(0)

            logger.info(f"✓ GPU detected: {gpu_name}")
            logger.info(f"✓ Loading high-accuracy model: {model_name} ({dimensions} dims)")

            config_info = {
                "device": device,
                "model_name": model_name,
                "dimensions": dimensions,
                "gpu_name": gpu_name,
                "gpu_memory_gb": torch.cuda.get_device_properties(0).total_memory / 1e9,
            }
        else:
            # CPU only - use compact fast model
            device = "cpu"
            model_name = "sentence-transformers/all-MiniLM-L6-v2"
            dimensions = 384

            logger.info("ℹ No GPU detected - using CPU with compact model")
            logger.info(f"✓ Loading model: {model_name} ({dimensions} dims)")

            config_info = {
                "device": device,
                "model_name": model_name,
                "dimensions": dimensions,
                "gpu_name": None,
                "gpu_memory_gb": None,
            }

    except ImportError:
        # torch not installed - fall back to CPU
        logger.warning("PyTorch not installed - defaulting to CPU mode")
        device = "cpu"
        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        dimensions = 384

        config_info = {
            "device": device,
            "model_name": model_name,
            "dimensions": dimensions,
            "gpu_name": None,
            "gpu_memory_gb": None,
        }

    # Load the model
    try:
        model = SentenceTransformer(model_name, device=device)
        logger.info(f"✓ Model loaded successfully on {device}")
    except Exception as e:
        logger.error(f"Failed to load {model_name}: {e}")
        logger.info("Falling back to MiniLM model on CPU")

        # Fallback to smallest model
        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        dimensions = 384
        model = SentenceTransformer(model_name, device="cpu")

        config_info = {
            "device": "cpu",
            "model_name": model_name,
            "dimensions": dimensions,
            "gpu_name": None,
            "gpu_memory_gb": None,
            "fallback": True,
            "original_error": str(e),
        }

    return model, config_info


def check_gpu_availability() -> dict:
    """
    Check GPU availability and return detailed hardware info.

    Returns:
        Dict with GPU status, CUDA version, available memory

    Examples:
        >>> info = check_gpu_availability()
        >>> info['available']
        True
        >>> info['device_name']
        'NVIDIA RTX A2000'
    """
    try:
        import torch

        if not torch.cuda.is_available():
            return {
                "available": False,
                "reason": "CUDA not available",
                "device_count": 0,
            }

        device_props = torch.cuda.get_device_properties(0)

        return {
            "available": True,
            "device_count": torch.cuda.device_count(),
            "device_name": torch.cuda.get_device_name(0),
            "cuda_version": torch.version.cuda,
            "total_memory_gb": device_props.total_memory / 1e9,
            "compute_capability": f"{device_props.major}.{device_props.minor}",
        }

    except ImportError:
        return {
            "available": False,
            "reason": "PyTorch not installed",
            "device_count": 0,
        }
    except Exception as e:
        return {
            "available": False,
            "reason": f"Error checking GPU: {str(e)}",
            "device_count": 0,
        }


if __name__ == "__main__":
    # Test GPU detection and model loading
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("=" * 80)
    print("NECB Semantic Search - Model Configuration Test")
    print("=" * 80)

    # Check GPU
    print("\n1. Checking GPU availability...")
    print("-" * 80)
    gpu_info = check_gpu_availability()

    if gpu_info["available"]:
        print(f"✓ GPU Available: {gpu_info['device_name']}")
        print(f"  CUDA Version: {gpu_info['cuda_version']}")
        print(f"  Memory: {gpu_info['total_memory_gb']:.2f} GB")
        print(f"  Compute Capability: {gpu_info['compute_capability']}")
    else:
        print(f"✗ GPU Not Available: {gpu_info['reason']}")

    # Load model
    print("\n2. Loading optimal embedding model...")
    print("-" * 80)

    try:
        model, config = get_optimal_embedding_model()

        print(f"✓ Model: {config['model_name']}")
        print(f"  Device: {config['device']}")
        print(f"  Dimensions: {config['dimensions']}")

        if config.get('gpu_name'):
            print(f"  GPU: {config['gpu_name']}")

        # Test embedding generation
        print("\n3. Testing embedding generation...")
        print("-" * 80)

        test_texts = [
            "What is the maximum FDWR for Calgary?",
            "U-value requirements for walls",
            "Lighting power density for classrooms",
        ]

        embeddings = model.encode(test_texts, show_progress_bar=False)

        print(f"✓ Generated embeddings: {embeddings.shape}")
        print(f"  Shape: {len(test_texts)} texts × {embeddings.shape[1]} dimensions")
        print(f"  Dtype: {embeddings.dtype}")

        print("\n" + "=" * 80)
        print("MODEL CONFIGURATION TEST COMPLETE")
        print("=" * 80)
        print(f"\n✓ Ready for NECB semantic search")
        print(f"  Device: {config['device'].upper()}")
        print(f"  Model: {config['model_name']}")

        sys.exit(0)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
